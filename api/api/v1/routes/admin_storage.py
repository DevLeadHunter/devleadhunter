"""
Admin routes to inspect and manage the Cloudflare R2 bucket.

Backs the dashboard « Stockage » page: list every object with its expiry
countdown, play/copy its public URL, delete it, purge expired ones, spot
R2 ↔ DB inconsistencies, and (in dev only) pull the prod bucket down.
"""
from __future__ import annotations

import logging
from datetime import datetime, timedelta, timezone
from typing import Any, Optional

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy.orm import Session

from core.config import settings
from core.database import get_db
from models.demo_site import DemoSite
from models.prospect_db import ProspectDB
from models.user import User
from services.r2_storage_service import r2_storage
from services.auth_service import require_admin

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/admin/storage", tags=["admin-storage"])

# Durée de vie des livrables liés à une démo (aligné sur le TTL des démos).
OBJECT_TTL_DAYS = 14


class StorageObject(BaseModel):
    """One object of the bucket, enriched with business context."""

    key: str
    kind: str  # website_video | website_thumbnail | presenter | support | other
    size: int
    last_modified: Optional[datetime] = None
    url: str
    slug: Optional[str] = None
    prospect_name: Optional[str] = None
    expires_in_days: Optional[int] = None
    is_expired: bool = False


class StorageListResponse(BaseModel):
    """Bucket listing + totals."""

    bucket: str
    public_base_url: str
    items: list[StorageObject]
    total: int
    total_size: int


class StorageHealthResponse(BaseModel):
    """R2 ↔ database consistency report."""

    orphan_objects: list[str]
    missing_objects: list[str]
    expired_objects: list[str]


class StorageActionResponse(BaseModel):
    """Result of a mutating action."""

    deleted: int = 0
    copied: int = 0
    unchanged: int = 0
    message: str = ""


def _classify(key: str) -> str:
    """Map an object key to a human category."""
    if key.startswith(r2_storage.VIDEOS_WEBSITES_PREFIX):
        return "website_video"
    if key.startswith(r2_storage.IMAGES_WEBSITES_PREFIX):
        return "website_thumbnail"
    if key.startswith(r2_storage.VIDEOS_PRESENTER_PREFIX):
        return "presenter"
    if key.startswith(r2_storage.IMAGES_SUPPORT_PREFIX):
        return "support"
    return "other"


def _slug_from_key(key: str) -> Optional[str]:
    """Extract the demo slug carried by a website video/thumbnail key."""
    if _classify(key) not in ("website_video", "website_thumbnail"):
        return None
    return key.rsplit("/", 1)[-1].rsplit(".", 1)[0] or None


def _ensure_configured() -> None:
    """Fail with a readable 503 when R2 is not configured."""
    if not r2_storage.is_configured():
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Stockage R2 non configuré (voir R2_* dans api/.env).",
        )


@router.get("", response_model=StorageListResponse)
async def list_storage_objects(
    prefix: str = "",
    _admin: User = Depends(require_admin),
    db: Session = Depends(get_db),
) -> StorageListResponse:
    """
    List the bucket objects, newest first, with expiry and prospect context.

    Args:
        prefix: Optional key prefix filter (e.g. ``videos/websites/``).

    Returns:
        The bucket listing.
    """
    _ensure_configured()
    raw = await _list_async(prefix)

    slugs = {s for s in (_slug_from_key(item["key"]) for item in raw) if s}
    names_by_slug: dict[str, str] = {}
    if slugs:
        rows = (
            db.query(DemoSite.slug, ProspectDB.name)
            .outerjoin(ProspectDB, ProspectDB.id == DemoSite.prospect_id)
            .filter(DemoSite.slug.in_(slugs))
            .all()
        )
        names_by_slug = {slug: name for slug, name in rows if name}

    now = datetime.now(timezone.utc)
    items: list[StorageObject] = []
    for entry in raw:
        key = entry["key"]
        kind = _classify(key)
        slug = _slug_from_key(key)
        expires_in: Optional[int] = None
        is_expired = False
        # Seuls les livrables liés à une démo expirent ; le clip presenter et
        # les pièces jointes support sont permanents.
        if kind in ("website_video", "website_thumbnail") and entry["last_modified"]:
            deadline = entry["last_modified"] + timedelta(days=OBJECT_TTL_DAYS)
            expires_in = max(0, (deadline - now).days)
            is_expired = deadline <= now
        items.append(
            StorageObject(
                key=key,
                kind=kind,
                size=entry["size"],
                last_modified=entry["last_modified"],
                url=r2_storage.public_url(key),
                slug=slug,
                prospect_name=names_by_slug.get(slug or ""),
                expires_in_days=expires_in,
                is_expired=is_expired,
            )
        )

    items.sort(key=lambda o: o.last_modified or datetime.min.replace(tzinfo=timezone.utc), reverse=True)
    return StorageListResponse(
        bucket=r2_storage.bucket_name(),
        public_base_url=settings.r2_public_base_url or "",
        items=items,
        total=len(items),
        total_size=sum(o.size for o in items),
    )


@router.get("/health", response_model=StorageHealthResponse)
async def storage_health(
    _admin: User = Depends(require_admin),
    db: Session = Depends(get_db),
) -> StorageHealthResponse:
    """
    Report R2 ↔ DB inconsistencies — the proof that the 14-day cleanup works.

    Returns:
        Orphan objects, missing objects and expired leftovers.
    """
    _ensure_configured()
    from enums.demo_video_status import DemoVideoStatus

    objects = await _list_async(r2_storage.VIDEOS_WEBSITES_PREFIX)
    keys = {item["key"] for item in objects}

    ready_slugs = {
        slug
        for (slug,) in db.query(DemoSite.slug)
        .filter(DemoSite.video_status == DemoVideoStatus.READY.value)
        .all()
        if slug
    }
    expected = {r2_storage.website_video_key(slug) for slug in ready_slugs}

    now = datetime.now(timezone.utc)
    expired = [
        item["key"]
        for item in objects
        if item["last_modified"] and item["last_modified"] + timedelta(days=OBJECT_TTL_DAYS) <= now
    ]

    return StorageHealthResponse(
        orphan_objects=sorted(keys - expected),
        missing_objects=sorted(expected - keys),
        expired_objects=sorted(expired),
    )


@router.delete("/object", response_model=StorageActionResponse)
async def delete_storage_object(
    key: str,
    _admin: User = Depends(require_admin),
) -> StorageActionResponse:
    """
    Delete one object from the bucket.

    Args:
        key: Full object key (query param so slashes need no escaping).

    Returns:
        How many objects were removed.
    """
    _ensure_configured()
    if not key.strip():
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Clé manquante.")
    await r2_storage.delete_async(key)
    return StorageActionResponse(deleted=1, message=f"{key} supprimé.")


@router.post("/purge-expired", response_model=StorageActionResponse)
async def purge_expired_objects(
    _admin: User = Depends(require_admin),
) -> StorageActionResponse:
    """
    Delete every demo deliverable older than the TTL (video + thumbnail).

    Returns:
        How many objects were removed.
    """
    _ensure_configured()
    now = datetime.now(timezone.utc)
    stale: list[str] = []
    for prefix in (
        r2_storage.VIDEOS_WEBSITES_PREFIX,
        r2_storage.IMAGES_WEBSITES_PREFIX,
    ):
        for item in await _list_async(prefix):
            if item["last_modified"] and item["last_modified"] + timedelta(days=OBJECT_TTL_DAYS) <= now:
                stale.append(item["key"])

    if stale:
        import asyncio

        await asyncio.to_thread(r2_storage.delete_many, stale)
    return StorageActionResponse(deleted=len(stale), message=f"{len(stale)} objet(s) expiré(s) supprimé(s).")


@router.post("/sync-from-prod", response_model=StorageActionResponse)
async def sync_from_prod(
    _admin: User = Depends(require_admin),
) -> StorageActionResponse:
    """
    Mirror the production bucket into the dev one — **development only**.

    Incremental by design: copies only what is missing (server-side CopyObject,
    nothing transits through the API), deletes what disappeared upstream, and
    leaves identical objects untouched.

    Returns:
        Copied / deleted / unchanged counts.

    Raises:
        HTTPException: 403 when called on a production instance.
    """
    _ensure_configured()
    if settings.is_production:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="La synchronisation n'est disponible qu'en développement.",
        )

    import asyncio

    source_bucket = r2_storage.prod_bucket_name()
    target_bucket = r2_storage.bucket_name()
    if source_bucket == target_bucket:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Les buckets dev et prod sont identiques : synchronisation annulée.",
        )

    source = {i["key"]: i for i in await asyncio.to_thread(r2_storage.list_objects, "", bucket=source_bucket)}
    target = {i["key"]: i for i in await asyncio.to_thread(r2_storage.list_objects, "")}

    to_copy = [
        key
        for key, item in source.items()
        if key not in target or target[key]["etag"] != item["etag"]
    ]
    to_delete = [key for key in target if key not in source]

    for key in to_copy:
        await asyncio.to_thread(r2_storage.copy_from_bucket, source_bucket, key)
    if to_delete:
        await asyncio.to_thread(r2_storage.delete_many, to_delete)

    unchanged = len(source) - len(to_copy)
    logger.info("[Storage] sync prod->dev: %d copied, %d deleted", len(to_copy), len(to_delete))
    return StorageActionResponse(
        copied=len(to_copy),
        deleted=len(to_delete),
        unchanged=unchanged,
        message=f"{len(to_copy)} copié(s), {len(to_delete)} supprimé(s), {unchanged} inchangé(s).",
    )


async def _list_async(prefix: str) -> list[dict[str, Any]]:
    """Run the blocking listing in a worker thread."""
    import asyncio

    return await asyncio.to_thread(r2_storage.list_objects, prefix)
