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
) -> dict[str, Any]:
    """Re-sync (upsert) the blok schemas of one existing Storyblok space."""
    await storyblok_service.resync_components(space_id)
    return {"space_id": space_id, "resynced": True}


@router.post("/resync-all")
async def resync_all(
    current_user: User = Depends(require_admin),
    db: Session = Depends(get_db),
) -> dict[str, Any]:
    """Re-sync every provisioned Storyblok space (all demo sites carrying a space id)."""
    space_ids: list[int] = [
        int(row[0])
        for row in db.query(DemoSite.storyblok_space_id)
        .filter(DemoSite.storyblok_space_id.isnot(None))
        .distinct()
        .all()
        if row[0]
    ]
    for space_id in space_ids:
        await storyblok_service.resync_components(space_id)
    return {"resynced_spaces": len(space_ids), "space_ids": space_ids}
