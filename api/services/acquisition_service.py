"""
Acquisition service — CRUD, lifecycle ops and stats for acquisition sequences.

This is the *business* layer over the ``acquisition_runs`` / ``acquisition_run_items``
tables (create a run from selected prospects, pause/resume/cancel, approve the
review gate, reject a single site, compute live stats).  The step-by-step
execution is done by :mod:`services.acquisition_orchestrator`.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from datetime import UTC, datetime

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from enums.acquisition import (
    AcquisitionItemStep,
    AcquisitionRunMode,
    AcquisitionRunStatus,
)
from enums.order_status import WON_STATUSES
from models.acquisition_run import AcquisitionRun
from models.acquisition_run_item import AcquisitionRunItem
from models.email_log import EmailLog
from models.order import Order
from models.prospect_db import ProspectDB
from services.credit_service import CreditService

logger = logging.getLogger(__name__)


def _utcnow() -> datetime:
    """Return the current UTC time as a timezone-naive datetime (DB-compatible)."""
    return datetime.now(UTC).replace(tzinfo=None)


@dataclass
class SequenceFollowUp:
    """One follow-up step configured on a sequence."""

    template_id: int
    delay_days: int = 5


@dataclass
class CreateSequenceInput:
    """
    Validated payload to create an automatisation.

    Two shapes:
      * **selection** (semi-auto) — ``prospect_ids`` given, items created now;
      * **query** (full-auto) — ``search_metiers`` + ``search_villes`` +
        ``target_days`` given, items seeded by the orchestrator's T0 from the
        unused-prospect pool.
    """

    name: str
    prospect_ids: list[int] = field(default_factory=list)
    mode: str = AcquisitionRunMode.SEMI_AUTO.value
    auto_enrich: bool = True
    auto_generate: bool = True
    template_id: str | None = None
    theme: dict | None = None
    auto_campaign: bool = True
    email_template_id_a: int | None = None
    email_template_id_b: int | None = None
    send_delay_minutes: int = 20
    follow_ups: list[SequenceFollowUp] = field(default_factory=list)
    # Full-auto query target.
    search_metiers: list[str] = field(default_factory=list)
    search_villes: list[str] = field(default_factory=list)
    target_days: int | None = None
    only_without_website: bool = True


class AcquisitionService:
    """Business operations for acquisition sequences."""

    def create_from_prospects(
        self,
        db: Session,
        user_id: int,
        organization_id: int | None,
        payload: CreateSequenceInput,
    ) -> AcquisitionRun:
        """
        Create an automatisation (selection- or query-based).

        Selection: only prospects visible to the user AND **not already tied to
        another automatisation** become items (one prospect = one automatisation).
        Query (full-auto): the run is created empty; the orchestrator's T0 seeds
        items from the unused-prospect pool matching métier + ville.

        The run starts ``running`` immediately when it has items or a full-auto
        query target, so the orchestrator picks it up on the next tick.

        Args:
            db: Database session.
            user_id: Owner of the run.
            organization_id: The user's organization (visibility scope), or None.
            payload: Validated configuration.

        Returns:
            The persisted :class:`AcquisitionRun` (with its items).
        """
        visible_ids: set[int] = self._visible_prospect_ids(db, user_id, organization_id, payload.prospect_ids)
        used_ids: set[int] = self.used_prospect_ids(db, user_id)

        has_query: bool = bool(payload.search_metiers and payload.search_villes and payload.target_days)

        run = AcquisitionRun(
            user_id=user_id,
            organization_id=organization_id,
            name=payload.name.strip() or "Automatisation sans nom",
            status=AcquisitionRunStatus.DRAFT.value,
            mode=payload.mode,
            auto_enrich=payload.auto_enrich,
            auto_generate=payload.auto_generate,
            template_id=payload.template_id,
            theme=payload.theme,
            auto_campaign=payload.auto_campaign,
            email_template_id_a=payload.email_template_id_a,
            email_template_id_b=payload.email_template_id_b,
            send_delay_minutes=max(payload.send_delay_minutes, 1),
            follow_ups=[{"template_id": fu.template_id, "delay_days": fu.delay_days} for fu in payload.follow_ups]
            or None,
            search_metiers=payload.search_metiers or None,
            search_villes=payload.search_villes or None,
            target_days=payload.target_days,
            only_without_website=payload.only_without_website,
            stats={"credits_at_start": CreditService.get_user_credits_consumed(db, user_id)},
        )
        db.add(run)
        db.flush()  # assign run.id

        # Selection: preserve order, drop invisible or already-used prospects.
        ordered: list[int] = [pid for pid in payload.prospect_ids if pid in visible_ids and pid not in used_ids]
        for prospect_id in ordered:
            db.add(
                AcquisitionRunItem(
                    run_id=run.id,
                    prospect_id=prospect_id,
                    step=AcquisitionItemStep.FOUND.value,
                    template_id=payload.template_id,
                )
            )

        run.status = AcquisitionRunStatus.RUNNING.value if (ordered or has_query) else AcquisitionRunStatus.DRAFT.value
        db.commit()
        db.refresh(run)
        logger.info(
            "[Acquisition] Created run %d for user %d — %d item(s), query=%s, mode=%s",
            run.id,
            user_id,
            len(ordered),
            has_query,
            run.mode,
        )
        return run

    def used_prospect_ids(self, db: Session, user_id: int) -> set[int]:
        """
        Prospect ids already claimed by one of the user's automatisations.

        A prospect is "claimed" while it belongs to a non-cancelled run and its
        item hasn't been skipped/excluded or failed — so cancelling a run or
        excluding a prospect frees it again (one prospect = one automatisation).
        """
        rows = db.execute(
            select(AcquisitionRunItem.prospect_id)
            .join(AcquisitionRun, AcquisitionRunItem.run_id == AcquisitionRun.id)
            .where(
                AcquisitionRun.user_id == user_id,
                AcquisitionRun.status != AcquisitionRunStatus.CANCELLED.value,
                AcquisitionRunItem.step.notin_([AcquisitionItemStep.SKIPPED.value, AcquisitionItemStep.FAILED.value]),
            )
        ).all()
        return {row[0] for row in rows}

    def find_unused_prospects_for_query(
        self,
        db: Session,
        user_id: int,
        organization_id: int | None,
        *,
        metiers: list[str],
        villes: list[str],
        only_without_website: bool,
        exclude_ids: set[int],
        limit: int,
    ) -> list[int]:
        """
        Return up to ``limit`` unused prospect ids matching the métier + ville
        target (case-insensitive, lenient substring match), preferring those
        without a website when ``only_without_website``.
        """
        if limit <= 0 or not metiers or not villes:
            return []
        candidates = db.execute(
            select(ProspectDB.id, ProspectDB.category, ProspectDB.city, ProspectDB.website).where(
                ProspectDB.user_id == user_id
            )
        ).all()

        metiers_lc: list[str] = [m.strip().lower() for m in metiers if m.strip()]
        villes_lc: list[str] = [v.strip().lower() for v in villes if v.strip()]
        picked: list[int] = []
        for pid, category, city, website in candidates:
            if pid in exclude_ids:
                continue
            if only_without_website and website:
                continue
            cat_lc: str = (category or "").lower()
            city_lc: str = (city or "").lower()
            if not any(m in cat_lc or cat_lc in m for m in metiers_lc):
                continue
            if not any(v in city_lc or city_lc in v for v in villes_lc):
                continue
            picked.append(pid)
            if len(picked) >= limit:
                break
        return picked

    @staticmethod
    def _visible_prospect_ids(
        db: Session,
        user_id: int,
        organization_id: int | None,
        prospect_ids: list[int],
    ) -> set[int]:
        """Return the subset of ``prospect_ids`` the user is allowed to act on."""
        if not prospect_ids:
            return set()
        rows = db.execute(
            select(ProspectDB.id, ProspectDB.user_id, ProspectDB.organization_id).where(ProspectDB.id.in_(prospect_ids))
        ).all()
        visible: set[int] = set()
        for pid, owner_id, org_id in rows:
            if owner_id == user_id or (organization_id is not None and org_id == organization_id):
                visible.add(pid)
        return visible

    def list_for_user(self, db: Session, user_id: int) -> list[AcquisitionRun]:
        """Return the user's sequences, newest first."""
        return list(
            db.execute(
                select(AcquisitionRun)
                .where(AcquisitionRun.user_id == user_id)
                .order_by(AcquisitionRun.created_at.desc())
            )
            .scalars()
            .all()
        )

    def get_for_user(self, db: Session, user_id: int, run_id: int) -> AcquisitionRun | None:
        """Return one sequence owned by the user, or None."""
        run: AcquisitionRun | None = db.get(AcquisitionRun, run_id)
        if run is None or run.user_id != user_id:
            return None
        return run

    def pause(self, db: Session, run: AcquisitionRun) -> AcquisitionRun:
        """Pause a running sequence (safe: nothing destructive)."""
        if run.status == AcquisitionRunStatus.RUNNING.value:
            run.status = AcquisitionRunStatus.PAUSED.value
            db.commit()
            db.refresh(run)
        return run

    def resume(self, db: Session, run: AcquisitionRun) -> AcquisitionRun:
        """Resume a paused sequence."""
        if run.status == AcquisitionRunStatus.PAUSED.value:
            run.status = AcquisitionRunStatus.RUNNING.value
            db.commit()
            db.refresh(run)
        return run

    def cancel(self, db: Session, run: AcquisitionRun) -> AcquisitionRun:
        """
        Cancel a sequence. Non-destructive — prospects, enrichments and sites
        already created are left in place; only the automation stops.
        """
        if run.status not in (
            AcquisitionRunStatus.COMPLETED.value,
            AcquisitionRunStatus.CANCELLED.value,
        ):
            run.status = AcquisitionRunStatus.CANCELLED.value
            db.commit()
            db.refresh(run)
        return run

    def approve_review(self, db: Session, run: AcquisitionRun) -> AcquisitionRun:
        """
        Approve the review gate ("Valider et démarcher") — the machine may now
        campaign the generated sites.
        """
        if run.status == AcquisitionRunStatus.AWAITING_REVIEW.value:
            run.review_approved_at = _utcnow()
            run.status = AcquisitionRunStatus.RUNNING.value
            db.commit()
            db.refresh(run)
        return run

    def reject_item(self, db: Session, run: AcquisitionRun, item_id: int) -> AcquisitionRunItem | None:
        """
        Reject a single generated site during review — it will not be campaigned.
        Returns the updated item, or None if it doesn't belong to the run.
        """
        item: AcquisitionRunItem | None = db.get(AcquisitionRunItem, item_id)
        if item is None or item.run_id != run.id:
            return None
        item.step = AcquisitionItemStep.SKIPPED.value
        item.step_reason = "rejeté à la validation"
        db.commit()
        db.refresh(item)
        return item

    def delete(self, db: Session, run: AcquisitionRun) -> None:
        """Delete a sequence and its items (cascade). Does not touch prospects."""
        db.delete(run)
        db.commit()

    def assign_templates(
        self,
        db: Session,
        run: AcquisitionRun,
        template_id: str | None,
        item_ids: list[int] | None = None,
    ) -> None:
        """
        Set the demo-site template on items (all pre-generation ones, or the
        given subset). No effect on items already generating or campaigning.
        """
        in_flight: set[str] = {
            AcquisitionItemStep.GENERATING.value,
            AcquisitionItemStep.CAMPAIGNING.value,
        }
        for item in run.items:
            if item_ids is not None and item.id not in item_ids:
                continue
            if item.step in in_flight:
                continue
            item.template_id = template_id
        db.commit()

    def regenerate_items(
        self,
        db: Session,
        run: AcquisitionRun,
        item_ids: list[int],
        template_id: str | None = None,
    ) -> None:
        """
        Re-generate the sites of the given items (optionally with a new template)
        by resetting them to ``enriched`` so the orchestrator rebuilds them.
        """
        changed: bool = False
        wanted: set[int] = set(item_ids)
        for item in run.items:
            if item.id not in wanted:
                continue
            if template_id is not None:
                item.template_id = template_id
            item.demo_site_id = None
            item.quality_score = None
            item.quality_flags = None
            item.step = AcquisitionItemStep.ENRICHED.value
            item.step_reason = "régénération demandée"
            changed = True
        self._reactivate(db, run, changed)

    def reenrich_items(self, db: Session, run: AcquisitionRun, item_ids: list[int]) -> None:
        """Re-enrich then re-generate the given items (reset to ``found``)."""
        changed: bool = False
        wanted: set[int] = set(item_ids)
        for item in run.items:
            if item.id not in wanted:
                continue
            item.step = AcquisitionItemStep.FOUND.value
            item.step_reason = "ré-enrichissement demandé"
            changed = True
        self._reactivate(db, run, changed)

    def exclude_items(self, db: Session, run: AcquisitionRun, item_ids: list[int]) -> None:
        """Exclude items from the automatisation (frees their prospects)."""
        wanted: set[int] = set(item_ids)
        for item in run.items:
            if item.id in wanted:
                item.step = AcquisitionItemStep.SKIPPED.value
                item.step_reason = "exclu manuellement"
        db.commit()

    def _reactivate(self, db: Session, run: AcquisitionRun, changed: bool) -> None:
        """Put a completed/awaiting-review run back to running after a reset."""
        if changed and run.status in (
            AcquisitionRunStatus.COMPLETED.value,
            AcquisitionRunStatus.AWAITING_REVIEW.value,
        ):
            run.status = AcquisitionRunStatus.RUNNING.value
        db.commit()

    def preview_email(self, db: Session, run: AcquisitionRun, item_id: int, template_id: int) -> dict | None:
        """
        Render the real email for one item (subject + body) with its demo link —
        exactly what will be sent. Returns None if the item/template is missing.
        """
        from models.demo_site import DemoSite
        from models.email_template import EmailTemplate
        from models.prospect_db import ProspectDB
        from services.email_sending_service import EmailSendingService

        item: AcquisitionRunItem | None = db.get(AcquisitionRunItem, item_id)
        if item is None or item.run_id != run.id:
            return None
        prospect: ProspectDB | None = db.get(ProspectDB, item.prospect_id)
        template: EmailTemplate | None = db.get(EmailTemplate, template_id)
        if prospect is None or template is None:
            return None

        demo_url: str = ""
        if item.demo_site_id is not None:
            site: DemoSite | None = db.get(DemoSite, item.demo_site_id)
            if site is not None and site.demo_url:
                demo_url = site.demo_url

        name_parts: list[str] = (prospect.name or "").split()
        variables: dict[str, str] = {
            "prenom": name_parts[0] if name_parts else "",
            "entreprise": prospect.name or "",
            "ville": prospect.city or "",
            "email": prospect.email or "",
            "phone": prospect.phone or "",
            "metier": prospect.category or "",
            "lien_demo": demo_url,
        }
        service = EmailSendingService(db)
        return {
            "subject": service.replace_variables(template.subject, variables),
            "body_html": service.replace_variables(template.body_html, variables),
        }

    def build_stats(self, db: Session, run: AcquisitionRun) -> dict:
        """
        Compute live stats for a run: item counts per step plus a won/emails
        overlay derived from Orders and EmailLogs.

        Returns:
            ``{"total", "by_step", "won", "emails_sent", "credits_spent"}``.
        """
        by_step: dict[str, int] = {}
        prospect_ids: list[int] = []
        for item in run.items:
            by_step[item.step] = by_step.get(item.step, 0) + 1
            prospect_ids.append(item.prospect_id)

        won: int = 0
        if prospect_ids:
            won = (
                db.execute(
                    select(func.count(func.distinct(Order.prospect_id))).where(
                        Order.user_id == run.user_id,
                        Order.prospect_id.in_(prospect_ids),
                        Order.status.in_(WON_STATUSES),
                    )
                ).scalar()
                or 0
            )

        emails_sent: int = 0
        if run.campaign_id is not None:
            emails_sent = (
                db.execute(
                    select(func.count()).select_from(EmailLog).where(EmailLog.campaign_id == run.campaign_id)
                ).scalar()
                or 0
            )

        credits_spent: int = 0
        baseline: int | None = (run.stats or {}).get("credits_at_start")
        if baseline is not None:
            credits_spent = max(0, CreditService.get_user_credits_consumed(db, run.user_id) - baseline)

        return {
            "total": len(run.items),
            "by_step": by_step,
            "won": won,
            "emails_sent": emails_sent,
            "credits_spent": credits_spent,
        }


acquisition_service = AcquisitionService()
