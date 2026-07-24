"""
Organization service — team workspaces with a shared prospect list.

Business rules (validated by Léo, 2026-07-10):
- Any user can create ONE organization and invite existing users by email.
- A user belongs to at most one organization at a time.
- ONLY prospects are shared: campaigns, demo sites, emails and credits stay
  personal (each member outreaches with their own sending identity).
- Sharing follows the creator's membership: joining an org tags the member's
  prospects with the org id (the shared list is instantly useful); leaving
  clears the tag AND any reservation held by the leaving member.
- Reservation = anti double-outreach: while a member holds a prospect, other
  members see it locked and API actions on it are refused for them.
"""

from __future__ import annotations

import logging
from datetime import UTC, datetime

from sqlalchemy import select, update
from sqlalchemy.orm import Session

from models.organization import Organization, OrganizationMember
from models.prospect_db import ProspectDB
from models.user import User

logger = logging.getLogger(__name__)

OWNER_ROLE: str = "owner"
MEMBER_ROLE: str = "member"


class OrganizationError(Exception):
    """Business-rule violation (mapped to HTTP 400/403/404 by the route layer)."""

    def __init__(self, message: str, status_code: int = 400) -> None:
        super().__init__(message)
        self.status_code = status_code


class OrganizationService:
    """Manages organizations, memberships and prospect reservations."""

    # ── Lookups ────────────────────────────────────────────────────────────

    def get_membership(self, db: Session, user_id: int) -> OrganizationMember | None:
        """Return the user's membership row, or None when not in any org."""
        return db.execute(select(OrganizationMember).where(OrganizationMember.user_id == user_id)).scalar_one_or_none()

    def get_user_organization(self, db: Session, user_id: int) -> Organization | None:
        """Return the organization the user belongs to, or None."""
        membership = self.get_membership(db, user_id)
        if membership is None:
            return None
        return db.get(Organization, membership.organization_id)

    def user_org_id(self, db: Session, user_id: int) -> int | None:
        """Return the user's organization id, or None (fast scope helper)."""
        membership = self.get_membership(db, user_id)
        return membership.organization_id if membership else None

    # ── Organization lifecycle ─────────────────────────────────────────────

    def create_organization(self, db: Session, user: User, name: str) -> Organization:
        """Create an organization owned by ``user`` and share their prospects with it.

        Raises:
            OrganizationError: When the user already belongs to an organization.
        """
        if self.get_membership(db, user.id) is not None:
            raise OrganizationError("Vous appartenez déjà à une organisation.", 400)

        organization = Organization(name=name.strip(), owner_user_id=user.id)
        db.add(organization)
        db.flush()

        db.add(OrganizationMember(organization_id=organization.id, user_id=user.id, role=OWNER_ROLE))
        self._share_user_prospects(db, user.id, organization.id)
        db.commit()
        db.refresh(organization)
        logger.info("Organization %d created by user %d", organization.id, user.id)
        return organization

    def delete_organization(self, db: Session, user_id: int) -> None:
        """Delete the org (owner only). Every member's prospects become personal again.

        Raises:
            OrganizationError: When the user is not the owner of an organization.
        """
        organization = self.get_user_organization(db, user_id)
        if organization is None:
            raise OrganizationError("Vous n'appartenez à aucune organisation.", 404)
        if organization.owner_user_id != user_id:
            raise OrganizationError("Seul le propriétaire peut supprimer l'organisation.", 403)

        self._unshare_org_prospects(db, organization.id)
        db.delete(organization)  # memberships cascade
        db.commit()
        logger.info("Organization %d deleted by owner %d", organization.id, user_id)

    # ── Members ────────────────────────────────────────────────────────────

    def invite_member(self, db: Session, inviter_id: int, email: str) -> OrganizationMember:
        """Add an EXISTING user (by account email) to the inviter's organization.

        Any member can invite (small-team usage). The invitee must not already
        belong to an organization.

        Raises:
            OrganizationError: When the inviter has no org, the email matches no
                account, or the invitee is already in an organization.
        """
        organization = self.get_user_organization(db, inviter_id)
        if organization is None:
            raise OrganizationError("Créez d'abord une organisation.", 400)

        invitee = db.execute(select(User).where(User.email == email.strip().lower())).scalar_one_or_none()
        if invitee is None:
            raise OrganizationError(
                "Aucun compte DevLeadHunter avec cet email — la personne doit d'abord s'inscrire.",
                404,
            )
        if self.get_membership(db, invitee.id) is not None:
            raise OrganizationError("Cet utilisateur appartient déjà à une organisation.", 400)

        membership = OrganizationMember(organization_id=organization.id, user_id=invitee.id, role=MEMBER_ROLE)
        db.add(membership)
        self._share_user_prospects(db, invitee.id, organization.id)
        db.commit()
        db.refresh(membership)
        logger.info(
            "User %d joined organization %d (invited by %d)",
            invitee.id,
            organization.id,
            inviter_id,
        )
        return membership

    def remove_member(self, db: Session, actor_id: int, member_user_id: int) -> None:
        """Remove a member — the owner removes anyone; a member removes only themselves.

        The leaving member's prospects turn personal again and their reservations
        inside the org are released.

        Raises:
            OrganizationError: On missing org/member or insufficient rights.
        """
        organization = self.get_user_organization(db, actor_id)
        if organization is None:
            raise OrganizationError("Vous n'appartenez à aucune organisation.", 404)

        is_owner = organization.owner_user_id == actor_id
        if member_user_id != actor_id and not is_owner:
            raise OrganizationError("Seul le propriétaire peut retirer un autre membre.", 403)
        if member_user_id == organization.owner_user_id:
            raise OrganizationError("Le propriétaire ne peut pas quitter — supprimez l'organisation.", 400)

        membership = db.execute(
            select(OrganizationMember).where(
                OrganizationMember.user_id == member_user_id,
                OrganizationMember.organization_id == organization.id,
            )
        ).scalar_one_or_none()
        if membership is None:
            raise OrganizationError("Ce membre n'appartient pas à votre organisation.", 404)

        # The member's own prospects become personal again…
        db.execute(update(ProspectDB).where(ProspectDB.user_id == member_user_id).values(organization_id=None))
        # …and every reservation they held in the org is released.
        db.execute(
            update(ProspectDB)
            .where(
                ProspectDB.organization_id == organization.id,
                ProspectDB.reserved_by_user_id == member_user_id,
            )
            .values(reserved_by_user_id=None, reserved_at=None)
        )
        db.delete(membership)
        db.commit()
        logger.info("User %d left organization %d", member_user_id, organization.id)

    # ── Prospect reservation ───────────────────────────────────────────────

    def reserve_prospect(self, db: Session, user_id: int, prospect: ProspectDB) -> ProspectDB:
        """Reserve a shared prospect for ``user_id``.

        Raises:
            OrganizationError: When the prospect is outside the user's org or
                already reserved by another member.
        """
        self._assert_prospect_visible(db, user_id, prospect)
        if prospect.reserved_by_user_id not in (None, user_id):
            raise OrganizationError("Ce prospect est déjà réservé par un autre membre.", 409)

        prospect.reserved_by_user_id = user_id
        prospect.reserved_at = datetime.now(UTC)
        db.commit()
        db.refresh(prospect)
        return prospect

    def release_prospect(self, db: Session, user_id: int, prospect: ProspectDB) -> ProspectDB:
        """Release a reservation — only the holder (or the org owner) can free it.

        Raises:
            OrganizationError: When not reserved, or held by someone else and the
                actor is not the org owner.
        """
        if prospect.reserved_by_user_id is None:
            raise OrganizationError("Ce prospect n'est pas réservé.", 400)
        if prospect.reserved_by_user_id != user_id:
            organization = self.get_user_organization(db, user_id)
            if organization is None or organization.owner_user_id != user_id:
                raise OrganizationError("Seul le membre qui a réservé (ou le propriétaire) peut libérer.", 403)

        prospect.reserved_by_user_id = None
        prospect.reserved_at = None
        db.commit()
        db.refresh(prospect)
        return prospect

    def assert_prospect_actionable(self, db: Session, user_id: int, prospect: ProspectDB) -> None:
        """Guard for write/outreach actions: refuse when another member holds it.

        Raises:
            OrganizationError: When the prospect is reserved by another member.
        """
        if prospect.reserved_by_user_id not in (None, user_id):
            raise OrganizationError("Ce prospect est réservé par un autre membre de votre organisation.", 403)

    # ── Internals ──────────────────────────────────────────────────────────

    def _assert_prospect_visible(self, db: Session, user_id: int, prospect: ProspectDB) -> None:
        """Raise unless the prospect is the user's own or shared with their org."""
        if prospect.user_id == user_id:
            return
        org_id = self.user_org_id(db, user_id)
        if org_id is None or prospect.organization_id != org_id:
            raise OrganizationError("Prospect introuvable.", 404)

    @staticmethod
    def _share_user_prospects(db: Session, user_id: int, organization_id: int) -> None:
        """Tag every prospect owned by the user with the organization."""
        db.execute(update(ProspectDB).where(ProspectDB.user_id == user_id).values(organization_id=organization_id))

    @staticmethod
    def _unshare_org_prospects(db: Session, organization_id: int) -> None:
        """Reset sharing + reservations for every prospect of a dissolved org."""
        db.execute(
            update(ProspectDB)
            .where(ProspectDB.organization_id == organization_id)
            .values(organization_id=None, reserved_by_user_id=None, reserved_at=None)
        )


organization_service = OrganizationService()
