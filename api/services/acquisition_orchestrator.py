"""Acquisition orchestrator — the background engine that auto-chains the tunnel."""

from __future__ import annotations

import asyncio
import logging
from datetime import UTC, datetime

from sqlalchemy import select
from sqlalchemy.orm import Session

logger = logging.getLogger(__name__)


class AcquisitionOrchestrator:
    """
    Advances every `running` AcquisitionRun one step per tick through the item state machine:
    found → (auto_enrich) → enriched → (auto_generate) → generated → (semi_auto: review) →
    (auto_campaign) → campaigning.

    It only orchestrates: each action reuses an existing unit service (`enrichment_service`,
    `demo_site_service`, `campaign_service` / `CampaignQueueService`). All state lives in the
    database, so a crash or a restart resumes exactly where it stopped.

    Three guardrails pause a run rather than failing prospect by prospect: a non-admin user with a
    zero balance, the per-run `max_credits` budget measured as a delta since the run started, and
    the `daily_email_cap` which caps a single campaign launch and skips the overflow visibly.
    """

    TICK_INTERVAL_SECONDS: int = 30
    # Caps the item-advances per tick so one huge run cannot monopolise it; the next tick resumes.
    MAX_ADVANCES_PER_TICK: int = 8
    MAX_ITEM_ATTEMPTS: int = 3

    def _utcnow(self) -> datetime:
        """Return the current UTC time as a timezone-naive datetime (DB-compatible)."""
        return datetime.now(UTC).replace(tzinfo=None)

    # Loop

    async def run_forever(self) -> None:
        """Background loop: advance running acquisition sequences, one step at a time."""
        logger.info("[Acquisition] Orchestrator started — tick=%ds", self.TICK_INTERVAL_SECONDS)
        while True:
            try:
                await self._tick()
            except Exception as exc:
                logger.error("[Acquisition] Unhandled error in tick: %s", exc, exc_info=True)
            await asyncio.sleep(self.TICK_INTERVAL_SECONDS)

    async def _tick(self) -> None:
        """Process every running sequence within a per-tick advance budget."""
        from core.database import SessionLocal
        from enums.acquisition import AcquisitionRunStatus
        from models.acquisition_run import AcquisitionRun

        db: Session = SessionLocal()
        try:
            runs: list[AcquisitionRun] = list(
                db.execute(select(AcquisitionRun).where(AcquisitionRun.status == AcquisitionRunStatus.RUNNING.value))
                .scalars()
                .all()
            )
            if not runs:
                return

            budget: int = self.MAX_ADVANCES_PER_TICK
            for run in runs:
                if budget <= 0:
                    break
                try:
                    used: int = await self._advance_run(db, run, budget)
                    budget -= used
                except Exception as exc:
                    logger.error("[Acquisition] Run %d failed this tick: %s", run.id, exc, exc_info=True)
                    db.rollback()
        finally:
            db.close()

    # Run-level orchestration

    async def _advance_run(self, db: Session, run, budget: int) -> int:
        """
        Advance one run by up to ``budget`` item-steps, then reconcile its status.

        Returns:
            The number of item-advances actually performed (to debit the tick budget).
        """
        from enums.acquisition import AcquisitionItemStep, AcquisitionRunMode, AcquisitionRunStatus
        from models.user import User
        from services.acquisition_service import acquisition_service
        from services.credit_service import CreditService

        user: User | None = db.get(User, run.user_id)
        if user is None:
            run.status = AcquisitionRunStatus.FAILED.value
            self._merge_stats(run, {"error": "utilisateur introuvable"})
            db.commit()
            return 0

        # Full-auto: seed items from the unused-prospect pool on the first pass.
        if run.mode == AcquisitionRunMode.FULL_AUTO.value and not (run.stats or {}).get("t0_seeded"):
            self._seed_full_auto(db, run)
            db.refresh(run)

        active_steps: set[str] = self._active_steps(run)
        active_items: list = [i for i in run.items if i.step in active_steps]

        # --- Credit guardrails (only matter while there's costly work left) -----
        if active_items:
            balance: int = CreditService.get_user_balance(db, run.user_id)  # -1 = admin/unlimited
            if balance == 0:
                run.status = AcquisitionRunStatus.PAUSED.value
                self._merge_stats(run, {"pause_reason": "crédits épuisés"})
                db.commit()
                logger.info("[Acquisition] Run %d paused — no credits", run.id)
                return 0
            if run.max_credits is not None:
                baseline: int | None = (run.stats or {}).get("credits_at_start")
                if baseline is not None:
                    spent: int = CreditService.get_user_credits_consumed(db, run.user_id) - baseline
                    if spent >= run.max_credits:
                        run.status = AcquisitionRunStatus.PAUSED.value
                        self._merge_stats(run, {"pause_reason": "plafond de crédits atteint"})
                        db.commit()
                        logger.info("[Acquisition] Run %d paused — credit cap reached", run.id)
                        return 0

        # --- Advance up to `budget` active items by one step each ---------------
        used: int = 0
        for item in active_items:
            if used >= budget:
                break
            await self._advance_item(db, run, item, user)
            used += 1

        # --- Reconcile run status after the generation phase --------------------
        if not any(i.step in self._active_steps(run) for i in run.items):
            generated: list = [i for i in run.items if i.step == AcquisitionItemStep.GENERATED.value]
            if run.auto_campaign and generated:
                if run.mode == "semi_auto" and run.review_approved_at is None:
                    if run.status != AcquisitionRunStatus.AWAITING_REVIEW.value:
                        run.status = AcquisitionRunStatus.AWAITING_REVIEW.value
                        logger.info("[Acquisition] Run %d awaiting review (%d site(s))", run.id, len(generated))
                else:
                    await self._launch_campaign(db, run, user, generated)
                    run.status = AcquisitionRunStatus.COMPLETED.value
            else:
                run.status = AcquisitionRunStatus.COMPLETED.value

        self._merge_stats(run, acquisition_service.build_stats(db, run))
        db.commit()
        return used

    def _seed_full_auto(self, db: Session, run) -> None:
        """
        Full-auto T0 — fill the run with items from the **unused-prospect pool**
        matching its métier(s) + ville(s), up to ``target_days × daily_cap``.

        Honest scope: we do NOT drive the scraper from here (it runs headful on the
        user's residential machine, not this host). If the pool can't reach the
        target, we proceed with what we have and record a clear shortfall note —
        "lance une recherche pour compléter" — instead of faking a scrape.
        """
        from enums.acquisition import AcquisitionItemStep
        from models.acquisition_run_item import AcquisitionRunItem
        from services.acquisition_service import acquisition_service
        from services.send_policy_service import send_policy_service

        daily_cap: int = send_policy_service.resolve(db, run.user_id).daily_cap
        target: int = min(max((run.target_days or 1) * daily_cap, 1), 500)

        used: set[int] = acquisition_service.used_prospect_ids(db, run.user_id)
        candidate_ids = acquisition_service.find_unused_prospects_for_query(
            db,
            run.user_id,
            run.organization_id,
            metiers=run.search_metiers or [],
            villes=run.search_villes or [],
            only_without_website=run.only_without_website,
            exclude_ids=used,
            limit=target,
        )

        for prospect_id in candidate_ids:
            db.add(
                AcquisitionRunItem(
                    run_id=run.id,
                    prospect_id=prospect_id,
                    step=AcquisitionItemStep.FOUND.value,
                    template_id=run.template_id,
                )
            )

        note: dict[str, object] = {"t0_seeded": True, "target_prospects": target}
        if len(candidate_ids) < target:
            note["seed_note"] = (
                f"{len(candidate_ids)}/{target} prospects disponibles — lance une recherche pour compléter la cible."
            )
        self._merge_stats(run, note)
        db.commit()
        logger.info(
            "[Acquisition] Run %d full-auto seeded %d/%d prospect(s)",
            run.id,
            len(candidate_ids),
            target,
        )

    def _score_item(self, db: Session, run, item, prospect) -> None:
        """
        Compute a 0-100 "sellability" score + flags for a generated site, so the
        review step can surface the risky ones first (and full-auto can flag them).
        Sets ``item.quality_score`` / ``item.quality_flags`` (no commit).
        """
        from services.enrichment_service import enrichment_service

        enrichment = None
        try:
            enrichment = enrichment_service.get_for_prospect(db, run.user_id, prospect.id)
        except Exception:
            enrichment = None

        score: int = 0
        flags: list[str] = []

        def _has(attr: str) -> bool:
            return bool(getattr(enrichment, attr, None)) if enrichment is not None else False

        if prospect.email:
            score += 15
        else:
            flags.append("pas d'email")
        if prospect.phone or _has("phone"):
            score += 15
        else:
            flags.append("pas de téléphone")
        if _has("description") or _has("services"):
            score += 20
        else:
            flags.append("pas de description")
        if _has("photos"):
            score += 20
        else:
            flags.append("pas de photo")
        if _has("rating") or _has("reviews_count"):
            score += 15
        else:
            flags.append("pas d'avis")
        if prospect.city or _has("hours"):
            score += 15

        item.quality_score = min(score, 100)
        item.quality_flags = flags or None

    def _active_steps(self, run) -> set[str]:
        """
        Return the item steps that still need enrich/generate work for this run's
        configuration.  ``generated`` is intentionally excluded — it waits for the
        review gate / campaign phase, not for another per-item advance.
        """
        from enums.acquisition import AcquisitionItemStep

        steps: set[str] = {
            AcquisitionItemStep.FOUND.value,
            AcquisitionItemStep.ENRICHING.value,
            AcquisitionItemStep.GENERATING.value,
        }
        if run.auto_generate:
            # An enriched item is only "active" when it still has to be generated.
            steps.add(AcquisitionItemStep.ENRICHED.value)
        return steps

    # Item-level transitions

    async def _advance_item(self, db: Session, run, item, user) -> None:
        """Advance a single item by exactly one transition."""
        from enums.acquisition import AcquisitionItemStep
        from models.prospect_db import ProspectDB

        prospect: ProspectDB | None = db.get(ProspectDB, item.prospect_id)
        if prospect is None:
            self._fail(db, item, "prospect introuvable")
            return

        # Respect the org reservation: never act on someone else's locked prospect.
        if prospect.reserved_by_user_id not in (None, run.user_id):
            self._skip(db, item, "réservé par un autre membre")
            return

        step: str = item.step

        if step == AcquisitionItemStep.FOUND.value:
            await self._do_enrich(db, run, item, user, prospect)
        elif step == AcquisitionItemStep.ENRICHED.value:
            await self._do_generate(db, run, item, user, prospect)
        else:
            # ENRICHING / GENERATING are transient markers; if we ever see one at the
            # start of a tick it means a previous tick was interrupted — retry it.
            if step == AcquisitionItemStep.ENRICHING.value:
                await self._do_enrich(db, run, item, user, prospect)
            elif step == AcquisitionItemStep.GENERATING.value:
                await self._do_generate(db, run, item, user, prospect)

    async def _do_enrich(self, db: Session, run, item, user, prospect) -> None:
        """FOUND → ENRICHED (running enrichment when ``auto_enrich``)."""
        from enums.acquisition import AcquisitionItemStep
        from services.enrichment_service import enrichment_service

        if not run.auto_enrich:
            self._set_step(db, item, AcquisitionItemStep.ENRICHED.value)
            return

        item.step = AcquisitionItemStep.ENRICHING.value
        db.commit()
        try:
            enrichment = await enrichment_service.ensure_enriched(db, run.user_id, prospect)
        except Exception as exc:
            self._retry_or_fail(db, item, f"enrichissement: {exc}")
            return

        # Poor enrichment still advances (the site will just be sparser) but is flagged.
        reason: str | None = None
        if enrichment is None or not self._enrichment_has_signal(enrichment):
            reason = "enrichissement pauvre"
        self._set_step(db, item, AcquisitionItemStep.ENRICHED.value, reason)

    async def _do_generate(self, db: Session, run, item, user, prospect) -> None:
        """ENRICHED → GENERATED (provisioning a demo site when ``auto_generate``)."""
        from enums.acquisition import AcquisitionItemStep
        from services.demo_site_service import demo_site_service
        from services.templates.registry import DEFAULT_TEMPLATE_ID

        if not run.auto_generate:
            # Enrich-only run: the item is done (no site, so nothing to campaign).
            self._set_step(db, item, AcquisitionItemStep.ENRICHED.value)
            return

        # Quality gate: a site needs a recipient email (and a name, always present).
        if not prospect.email:
            self._skip(db, item, "pas d'email — site non généré")
            return

        item.step = AcquisitionItemStep.GENERATING.value
        db.commit()
        try:
            site = await demo_site_service.create_demo_site(
                db,
                user=user,
                business_name=prospect.name,
                template_id=item.template_id or run.template_id or DEFAULT_TEMPLATE_ID,
                phone=prospect.phone,
                email=prospect.email,
                city=prospect.city,
                description=None,
                invite_client_to_cms=False,
                theme=run.theme,
                prospect_id=prospect.id,
            )
        except ValueError as exc:
            # Deterministic rejection (e.g. missing email) — don't retry.
            self._skip(db, item, f"génération impossible: {exc}")
            return
        except Exception as exc:
            self._retry_or_fail(db, item, f"génération: {exc}")
            return

        item.demo_site_id = site.id
        self._score_item(db, run, item, prospect)
        reason: str | None = None
        if item.quality_flags:
            reason = "à vérifier : " + ", ".join(item.quality_flags[:2])
        self._set_step(db, item, AcquisitionItemStep.GENERATED.value, reason)

    # Campaign batch (run-level, on approval or full-auto)

    async def _launch_campaign(self, db: Session, run, user, generated: list) -> None:
        """
        Create (or reuse) the run's campaign, add the eligible prospects, and launch
        it once — reusing the exact campaign create → add-prospects → enqueue flow the
        UI uses.  Sends only when the user has a Resend config; otherwise the campaign
        is left in draft for a manual launch.
        """
        from enums.acquisition import AcquisitionItemStep
        from models.campaign import CampaignStatus
        from models.prospect_db import ProspectDB
        from models.resend_config import ResendConfig
        from schemas.campaign import CampaignCreate
        from services.campaign_queue_service import CampaignQueueService
        from services.campaign_service import campaign_service

        if run.campaign_id is not None:
            # Idempotency: a campaign was already launched for this run.
            return

        # Eligible = generated items whose prospect is owned by this user (outreach
        # uses the user's own identity), has an email, and isn't locked by a peer.
        eligible: list = []
        for item in generated:
            prospect: ProspectDB | None = db.get(ProspectDB, item.prospect_id)
            if prospect is None:
                self._skip(db, item, "prospect introuvable")
                continue
            if prospect.user_id != run.user_id:
                self._skip(db, item, "appartient à un autre membre")
                continue
            if prospect.reserved_by_user_id not in (None, run.user_id):
                self._skip(db, item, "réservé par un autre membre")
                continue
            if not prospect.email:
                self._skip(db, item, "pas d'email")
                continue
            eligible.append(item)

        if not eligible:
            self._merge_stats(run, {"campaign_note": "aucun prospect éligible à démarcher"})
            return

        # Daily email cap: only the first N are enqueued now; the overflow is skipped
        # with a visible reason (no silent truncation).
        if run.daily_email_cap is not None and len(eligible) > run.daily_email_cap:
            for item in eligible[run.daily_email_cap :]:
                self._skip(db, item, "plafond quotidien atteint")
            eligible = eligible[: run.daily_email_cap]

        if not run.email_template_id_a:
            # No email template configured → sites are ready, but we don't invent a
            # campaign. Leave the items generated for a manual campaign.
            self._merge_stats(run, {"campaign_note": "aucun modèle d'email — démarchage manuel requis"})
            return

        prospect_ids: list[int] = [item.prospect_id for item in eligible]

        campaign = campaign_service.create_campaign(
            db,
            run.user_id,
            CampaignCreate(
                name=run.name,
                description="Créée automatiquement par une séquence d'acquisition",
                prospect_ids=[],
                template_id=run.email_template_id_a,
                ab_template_id_b=run.email_template_id_b,
                send_delay_minutes=run.send_delay_minutes,
            ),
        )
        campaign_service.add_prospects_to_campaign(db, campaign.id, run.user_id, prospect_ids)

        # Follow-up sequence (optional).
        self._create_follow_ups(db, campaign.id, run.follow_ups)

        run.campaign_id = campaign.id

        has_resend: bool = (
            db.execute(select(ResendConfig).where(ResendConfig.user_id == run.user_id)).scalar_one_or_none() is not None
        ) and self._resend_has_key(db, run.user_id)

        if not has_resend:
            # Campaign built but not sending — mark items campaigning, note the gap.
            for item in eligible:
                self._set_step(db, item, AcquisitionItemStep.CAMPAIGNING.value, "en attente — Resend non configuré")
            self._merge_stats(run, {"campaign_note": "Resend non configuré — campagne créée en brouillon"})
            logger.info("[Acquisition] Run %d built campaign %d (draft — no Resend)", run.id, campaign.id)
            return

        # Activate + enqueue (real send).
        campaign.status = CampaignStatus.ACTIVE.value
        campaign.started_at = self._utcnow()
        db.commit()

        fresh = campaign_service.get_campaign(db, campaign.id, run.user_id)
        queue_service = CampaignQueueService(db)
        result = queue_service.enqueue_campaign(
            fresh,
            template_id=run.email_template_id_a,
            ab_template_id_b=run.email_template_id_b,
        )

        skipped_ids: set[int] = {int(entry["id"]) for entry in result.skipped_no_demo}
        for item in eligible:
            if item.prospect_id in skipped_ids:
                self._set_step(db, item, AcquisitionItemStep.SKIPPED.value, "site de démo inactif")
            else:
                self._set_step(db, item, AcquisitionItemStep.CAMPAIGNING.value)

        self._merge_stats(run, {"campaign_note": f"{result.enqueued} email(s) en file"})
        logger.info(
            "[Acquisition] Run %d launched campaign %d — %d enqueued, %d skipped",
            run.id,
            campaign.id,
            result.enqueued,
            len(skipped_ids),
        )

    def _create_follow_ups(self, db: Session, campaign_id: int, follow_ups: list | None) -> None:
        """Create CampaignFollowUp rows from a run's ``follow_ups`` config, if any."""
        if not follow_ups:
            return
        from models.campaign_follow_up import CampaignFollowUp

        for position, step in enumerate(follow_ups, start=1):
            template_id = step.get("template_id")
            if not template_id:
                continue
            db.add(
                CampaignFollowUp(
                    campaign_id=campaign_id,
                    template_id=int(template_id),
                    delay_days=int(step.get("delay_days", 5)),
                    position=position,
                )
            )
        db.commit()

    # Small helpers

    def _resend_has_key(self, db: Session, user_id: int) -> bool:
        """Return True when the user's ResendConfig actually carries an API key."""
        from models.resend_config import ResendConfig

        cfg: ResendConfig | None = db.execute(
            select(ResendConfig).where(ResendConfig.user_id == user_id)
        ).scalar_one_or_none()
        return cfg is not None and bool(cfg.api_key)

    def _enrichment_has_signal(self, enrichment) -> bool:
        """
        Heuristic: did enrichment yield anything worth putting on a site?

        Kept defensive (attribute access guarded) since the enrichment shape evolves.
        """
        for attr in ("phone", "email", "description", "services", "hours", "photos", "rating"):
            value = getattr(enrichment, attr, None)
            if value:
                return True
        return False

    def _set_step(self, db: Session, item, step: str, reason: str | None = None) -> None:
        """Move an item to ``step`` (clearing transient error), commit."""
        item.step = step
        item.step_reason = reason
        if reason is None:
            item.last_error = None
        db.commit()

    def _skip(self, db: Session, item, reason: str) -> None:
        """Terminal skip with a reason (not an error)."""
        from enums.acquisition import AcquisitionItemStep

        item.step = AcquisitionItemStep.SKIPPED.value
        item.step_reason = reason
        db.commit()

    def _fail(self, db: Session, item, reason: str) -> None:
        """Terminal failure with a reason."""
        from enums.acquisition import AcquisitionItemStep

        item.step = AcquisitionItemStep.FAILED.value
        item.step_reason = reason
        item.last_error = reason
        db.commit()

    def _retry_or_fail(self, db: Session, item, error: str) -> None:
        """
        Increment the attempt counter; keep the item retryable until it exhausts
        ``self.MAX_ITEM_ATTEMPTS``, then fail it terminally.
        """
        from enums.acquisition import AcquisitionItemStep

        item.attempts += 1
        item.last_error = error
        if item.attempts >= self.MAX_ITEM_ATTEMPTS:
            item.step = AcquisitionItemStep.FAILED.value
            item.step_reason = f"échec après {item.attempts} tentatives"
        else:
            # Reset to the previous stable step so the next tick retries.
            if item.step == AcquisitionItemStep.ENRICHING.value:
                item.step = AcquisitionItemStep.FOUND.value
            elif item.step == AcquisitionItemStep.GENERATING.value:
                item.step = AcquisitionItemStep.ENRICHED.value
            item.step_reason = f"nouvelle tentative ({item.attempts})"
        db.commit()

    def _merge_stats(self, run, patch: dict) -> None:
        """Merge ``patch`` into the run's JSON stats, preserving existing keys."""
        run.stats = {**(run.stats or {}), **patch}


acquisition_orchestrator = AcquisitionOrchestrator()
