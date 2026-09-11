"""
Admin-only Storyblok tooling.

Re-sync the blok schemas (component definitions) of already-provisioned spaces so
they pick up new fields (e.g. ``social``) and updated FR labels — the "re-sync
command" the audit flagged as missing. The upsert lives in ``storyblok_service``;
these endpoints just expose it to an admin.
"""

from typing import Any

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from core.database import get_db
from models.demo_site import DemoSite
from models.user import User
from services.auth_service import require_admin
from services.storyblok_service import storyblok_service

router = APIRouter(prefix="/admin/storyblok", tags=["admin-storyblok"])


@router.post("/resync/{space_id}")
async def resync_space(
    space_id: int,
    current_user: User = Depends(require_admin),
    db: Session = Depends(get_db),
) -> dict[str, Any]:
    """Re-sync (upsert) one existing Storyblok space using ITS template's schema (overrides included)."""
    template_id: str | None = (
        db.query(DemoSite.template_id)
        .filter(DemoSite.storyblok_space_id == space_id)
        .order_by(DemoSite.id.desc())
        .limit(1)
        .scalar()
    )
    await storyblok_service.resync_components(space_id, template_id)
    return {"space_id": space_id, "resynced": True, "template_id": template_id}


@router.post("/resync-all")
async def resync_all(
    current_user: User = Depends(require_admin),
    db: Session = Depends(get_db),
) -> dict[str, Any]:
    """Re-sync every provisioned Storyblok space, each with its own template's schema."""
    template_by_space: dict[int, str | None] = {}
    for space_id, template_id in (
        db.query(DemoSite.storyblok_space_id, DemoSite.template_id)
        .filter(DemoSite.storyblok_space_id.isnot(None))
        .order_by(DemoSite.id.desc())
        .all()
    ):
        if space_id and int(space_id) not in template_by_space:
            template_by_space[int(space_id)] = template_id
    for space_id, template_id in template_by_space.items():
        await storyblok_service.resync_components(space_id, template_id)
    return {"resynced_spaces": len(template_by_space), "space_ids": list(template_by_space)}
