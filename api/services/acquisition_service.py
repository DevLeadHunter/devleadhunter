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
from datetime import datetime, timezone
from typing import List, Optional

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
    return datetime.now(timezone.utc).replace(tzinfo=None)


@dataclass
class SequenceFollowUp:
    """One follow-up step configured on a sequence."""

    template_id: int
    delay_days: int = 5


@dataclass
class CreateSequenceInput:
    """Validated payload to create a sequence from already-found prospects."""

    name: str
    prospect_ids: List[int]
    mode: str = AcquisitionRunMode.SEMI_AUTO.value
    auto_enrich: bool = True
    auto_generate: bool = True
    template_id: Optional[str] = None
    auto_campaign: bool = True
    email_template_id_a: Optional[int] = None
    email_template_id_b: Optional[int] = None
    send_delay_minutes: int = 20
    follow_ups: List[SequenceFollowUp] = field(default_factory=list)
    max_credits: Optional[int] = None
    daily_email_cap: Optional[int] = None


class AcquisitionService:
    """Business operations for acquisition sequences."""

    # -----------------------------------------------------------------------
    # Creation
    # -----------------------------------------------------------------------

    def create_from_prospects(
        self,
        db: Session,
        user_id: int,
        organization_id: Optional[int],
        payload: CreateSequenceInput,
    ) -> AcquisitionRun:
        """
        Create a sequence over a batch of prospects the user can see.

        Only prospects visible to the user (owned by them or shared by their
        organization) become items.  The run starts ``running`` immediately when
        it has at least one item, so the orchestrator picks it up on the next
        tick.

        Args:
            db: Database session.
            user_id: Owner of the run.
            organization_id: The user's organization (visibility scope), or None.
            payload: Validated sequence configuration.

        Returns:
            The persisted :class:`AcquisitionRun` (with its items).
        """
        visible_ids: set[int] = self._visible_prospect_ids(
            db, user_id, organization_id, payload.prospect_ids
        )

        run = AcquisitionRun(
            user_id=user_id,
            organization_id=organization_id,
            name=payload.name.strip() or "Séquence sans nom",
            status=AcquisitionRunStatus.DRAFT.value,
            mode=payload.mode,
            auto_enrich=payload.auto_enrich,
            auto_generate=payload.auto_generate,
            template_id=payload.template_id,
            auto_campaign=payload.auto_campaign,
            email_template_id_a=payload.email_template_id_a,
            email_template_id_b=payload.email_template_id_b,
            send_delay_minutes=max(payload.send_delay_minutes, 1),
            follow_ups=[
                {"template_id": fu.template_id, "delay_days": fu.delay_days}
                for fu in payload.follow_ups
            ]
            or None,
            max_credits=payload.max_credits,
            daily_email_cap=payload.daily_email_cap,
            stats={"credits_at_start": CreditService.get_user_credits_consumed(db, user_id)},
        )
        db.add(run)
        db.flush()  # assign run.id

        # Preserve the order the user selected them in.
        ordered: List[int] = [pid for pid in payload.prospect_ids if pid in visible_ids]
        for prospect_id in ordered:
            db.add(
                AcquisitionRunItem(
                    run_id=run.id,
                    prospect_id=prospect_id,
                    step=AcquisitionItemStep.FOUND.value,
                )
            )

        run.status = (
            AcquisitionRunStatus.RUNNING.value
            if ordered
            else AcquisitionRunStatus.DRAFT.value
        )
        db.commit()
        db.refresh(run)
        logger.info(
            "[Acquisition] Created run %d for user %d with %d item(s) (mode=%s)",
            run.id, user_id, len(ordered), run.mode,
        )
        return run

    @staticmethod
    def _visible_prospect_ids(
        db: Session,
        user_id: int,
        organization_id: Optional[int],
        prospect_ids: List[int],
    ) -> set[int]:
        """Return the subset of ``prospect_ids`` the user is allowed to act on."""
        if not prospect_ids:
            return set()
        rows = db.execute(
            select(ProspectDB.id, ProspectDB.user_id, ProspectDB.organization_id).where(
                ProspectDB.id.in_(prospect_ids)
            )
        ).all()
        visible: set[int] = set()
        for pid, owner_id, org_id in rows:
            if owner_id == user_id:
                visible.add(pid)
            elif organization_id is not None and org_id == organization_id:
                visible.add(pid)
        return visible

    # -----------------------------------------------------------------------
    # Reads
    # -----------------------------------------------------------------------

    def list_for_user(self, db: Session, user_id: int) -> List[AcquisitionRun]:
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

    def get_for_user(
        self, db: Session, user_id: int, run_id: int
    ) -> Optional[AcquisitionRun]:
        """Return one sequence owned by the user, or None."""
        run: Optional[AcquisitionRun] = db.get(AcquisitionRun, run_id)
        if run is None or run.user_id != user_id:
            return None
        return run

    # -----------------------------------------------------------------------
    # Lifecycle operations
    # -----------------------------------------------------------------------

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

    def reject_item(
        self, db: Session, run: AcquisitionRun, item_id: int
    ) -> Optional[AcquisitionRunItem]:
        """
        Reject a single generated site during review — it will not be campaigned.
        Returns the updated item, or None if it doesn't belong to the run.
        """
        item: Optional[AcquisitionRunItem] = db.get(AcquisitionRunItem, item_id)
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

    # -----------------------------------------------------------------------
    # Stats (derived — always fresh)
    # -----------------------------------------------------------------------

    def build_stats(self, db: Session, run: AcquisitionRun) -> dict:
        """
        Compute live stats for a run: item counts per step plus a won/emails
        overlay derived from Orders and EmailLogs.

        Returns:
            ``{"total", "by_step", "won", "emails_sent", "credits_spent"}``.
        """
        by_step: dict[str, int] = {}
        prospect_ids: List[int] = []
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
                    select(func.count()).select_from(EmailLog).where(
                        EmailLog.campaign_id == run.campaign_id
                    )
                ).scalar()
                or 0
            )

        credits_spent: int = 0
        baseline: Optional[int] = (run.stats or {}).get("credits_at_start")
        if baseline is not None:
            credits_spent = max(
                0, CreditService.get_user_credits_consumed(db, run.user_id) - baseline
            )

        return {
            "total": len(run.items),
            "by_step": by_step,
            "won": won,
            "emails_sent": emails_sent,
            "credits_spent": credits_spent,
        }


acquisition_service = AcquisitionService()
