"""
Admin routes to inspect and manage the Cloudflare R2 bucket.

Backs the dashboard « Stockage » page: list every object with its expiry
countdown, play/copy its public URL, delete it, purge expired ones, spot
R2 ↔ DB inconsistencies, and (in dev only) pull the prod bucket down.
"""

from __future__ import annotations

import logging
from datetime import UTC, datetime
from typing import Any, Protocol

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile, status
from pydantic import BaseModel
from sqlalchemy.orm import Session

from core.config import settings
from core.database import get_db
from enums.demo_site_status import DemoSiteStatus
from models.demo_site import DemoSite
from models.prospect_db import ProspectDB
from models.prospect_enrichment import ProspectEnrichment
from models.user import User
from services.auth_service import require_admin
from services.manual_upload_service import manual_upload_service
from services.r2_storage_service import r2_storage

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/admin/storage", tags=["admin-storage"])

# Suffixe des vidéos de fond de montage (intermédiaire, vit et meurt avec sa démo).
_BACKGROUND_SUFFIX = "-background.mp4"
# Catégories dont l'expiration suit le TTL de la démo (le reste du bucket est permanent).
_DEMO_DELIVERABLE_KINDS = ("website_video", "website_thumbnail", "website_background")


class _DemoTtl(Protocol):
    """The demo-site columns needed to decide a deliverable's expiry (duck-typed SQLAlchemy row)."""

    status: str
    demo_link_sent_at: datetime | None
    expires_at: datetime


def _expiry_state(demo: _DemoTtl | None, now: datetime) -> tuple[bool, int | None, bool]:
    """Decide a demo deliverable's expiry, anchored on its demo's real lifecycle.

    Mirrors the actual cleanup (``demo_site_service.expire_due_sites`` → ``_purge_demo_video``): the
    file is purged when its demo expires (``demo_link_sent_at + DEMO_SITE_TTL_DAYS``), not after a fixed
    number of days on the bucket — so a video pre-generated ahead of the send, or one still within a live
    demo's window, is **not** flagged.

    Args:
        demo: The deliverable's demo row, or None when no demo references it any more.
        now: Current UTC instant.

    Returns:
        ``(is_expired, expires_in_days, ttl_pending)`` — ``expires_in_days`` is None when expired,
        permanent (sold) or pending; ``ttl_pending`` is True while the countdown has not started.
    """
    if demo is None:
        # Plus aucune démo ne référence ce fichier : reliquat que le nettoyage aurait dû retirer.
        return True, None, False
    if demo.status == DemoSiteStatus.DELIVERED.value:
        # Démo vendue : site permanent, exclu du TTL.
        return False, None, False
    if demo.demo_link_sent_at is None:
        # Lien pas encore envoyé : le compte à rebours n'a pas démarré.
        return False, None, True
    expires_at: datetime = demo.expires_at
    if expires_at.tzinfo is None:
        expires_at = expires_at.replace(tzinfo=UTC)
    if expires_at <= now:
        return True, None, False
    return False, max(0, (expires_at - now).days), False


def _demo_ttl_by_slug(db: Session, slugs: set[str]) -> dict[str, Any]:
    """Load the TTL-relevant demo columns for a set of slugs.

    Args:
        db: Active database session.
        slugs: Demo slugs to look up.

    Returns:
        A ``slug -> row`` map exposing ``status``, ``demo_link_sent_at`` and ``expires_at``.
    """
    if not slugs:
        return {}
    rows = (
        db.query(DemoSite.slug, DemoSite.status, DemoSite.demo_link_sent_at, DemoSite.expires_at)
        .filter(DemoSite.slug.in_(slugs))
        .all()
    )
    return {row.slug: row for row in rows}


def _expired_website_keys(db: Session, objects: list[dict[str, Any]], now: datetime) -> list[str]:
    """Pick the demo-deliverable keys whose demo has expired (or vanished), for health and purge.

    Args:
        db: Active database session.
        objects: Raw R2 listing entries under the website prefixes.
        now: Current UTC instant.

    Returns:
        The object keys that should no longer exist.
    """
    slugs = {slug for slug in (_slug_from_key(item["key"]) for item in objects) if slug}
    demo_by_slug = _demo_ttl_by_slug(db, slugs)
    expired: list[str] = []
    for item in objects:
        slug = _slug_from_key(item["key"])
        if slug is None:
            continue
        is_expired, _, _ = _expiry_state(demo_by_slug.get(slug), now)
        if is_expired:
            expired.append(item["key"])
    return expired


class StorageObject(BaseModel):
    """One object of the bucket, enriched with business context."""

    key: str
    kind: str  # website_video | website_thumbnail | website_background | presenter | support | prospect_photo | manual | other
    size: int
    last_modified: datetime | None = None
    url: str
    slug: str | None = None
    prospect_name: str | None = None
    expires_in_days: int | None = None
    is_expired: bool = False
    ttl_pending: bool = False


class StorageListResponse(BaseModel):
    """Bucket listing + totals."""

    bucket: str
    public_base_url: str
    items: list[StorageObject]
    total: int
    total_size: int
    ttl_days: int


class StorageUploadResponse(BaseModel):
    """Result of a manual upload / URL import — the caller pastes ``url`` where it is needed."""

    key: str
    url: str
    kind: str
    size: int
    message: str = ""


class ImportUrlRequest(BaseModel):
    """Payload for POST /admin/storage/import-url — the remote file to rehost onto R2."""

    url: str


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


class DeleteObjectsRequest(BaseModel):
    """Payload for POST /admin/storage/delete-objects — the object keys to remove in one call."""

    keys: list[str]


def _classify(key: str) -> str:
    """Map an object key to a human category."""
    if key.startswith(r2_storage.VIDEOS_WEBSITES_PREFIX):
        return "website_background" if key.endswith(_BACKGROUND_SUFFIX) else "website_video"
    if key.startswith(r2_storage.IMAGES_WEBSITES_PREFIX):
        return "website_thumbnail"
    if key.startswith(r2_storage.VIDEOS_PRESENTER_PREFIX):
        return "presenter"
    if key.startswith(r2_storage.IMAGES_SUPPORT_PREFIX):
        return "support"
    if key.startswith(r2_storage.IMAGES_PROSPECTS_PREFIX):
        return "prospect_photo"
    if key.startswith(r2_storage.MANUAL_UPLOADS_PREFIX):
        return "manual"
    return "other"


def _slug_from_key(key: str) -> str | None:
    """Extract the demo slug carried by a website video / thumbnail / montage-background key.

    The ``{slug}-background.mp4`` montage artifact resolves to its base slug so its expiry anchors on
    the same demo as the final video (they are purged together).
    """
    if _classify(key) not in _DEMO_DELIVERABLE_KINDS:
        return None
    base: str = key.rsplit("/", 1)[-1].rsplit(".", 1)[0]
    if base.endswith("-background"):
        base = base[: -len("-background")]
    return base or None


def _prospect_id_from_key(key: str) -> int | None:
    """Extract the prospect id carried by a rehosted photo key (``images/prospects/{id}/{hash}.jpg``)."""
    if not key.startswith(r2_storage.IMAGES_PROSPECTS_PREFIX):
        return None
    parts = key.split("/")
    return int(parts[2]) if len(parts) >= 4 and parts[2].isdigit() else None


def _referenced_prospect_photo_keys(db: Session) -> set[str]:
    """Collect every ``images/prospects/`` object key still referenced by an enrichment record.

    Compared by KEY (not full URL) so it holds regardless of the dev/prod public base URL. A prospect's
    ``photos`` list and its ``logo_url`` are the only places a rehosted photo is referenced.
    """
    prefix = r2_storage.IMAGES_PROSPECTS_PREFIX
    keys: set[str] = set()
    for photos, logo_url in db.query(ProspectEnrichment.photos, ProspectEnrichment.logo_url).all():
        for value in [*(photos or []), logo_url]:
            if not isinstance(value, str):
                continue
            index = value.find(prefix)
            if index != -1:
                keys.add(value[index:])
    return keys


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
    demo_by_slug: dict[str, Any] = {}
    if slugs:
        rows = (
            db.query(
                DemoSite.slug,
                DemoSite.status,
                DemoSite.demo_link_sent_at,
                DemoSite.expires_at,
                ProspectDB.name,
            )
            .outerjoin(ProspectDB, ProspectDB.id == DemoSite.prospect_id)
            .filter(DemoSite.slug.in_(slugs))
            .all()
        )
        demo_by_slug = {row.slug: row for row in rows}
        names_by_slug = {row.slug: row.name for row in rows if row.name}

    prospect_ids = {pid for pid in (_prospect_id_from_key(item["key"]) for item in raw) if pid}
    names_by_prospect_id: dict[int, str] = {}
    if prospect_ids:
        prospect_rows = db.query(ProspectDB.id, ProspectDB.name).filter(ProspectDB.id.in_(prospect_ids)).all()
        names_by_prospect_id = {pid: name for pid, name in prospect_rows if name}

    now = datetime.now(UTC)
    items: list[StorageObject] = []
    for entry in raw:
        key = entry["key"]
        kind = _classify(key)
        slug = _slug_from_key(key)
        expires_in: int | None = None
        is_expired = False
        ttl_pending = False
        # Seuls les livrables liés à une démo expirent (ancrés sur le TTL réel de LEUR démo) ; le clip
        # presenter, les pièces jointes support, les photos de prospect et les imports manuels sont permanents.
        if kind in _DEMO_DELIVERABLE_KINDS:
            is_expired, expires_in, ttl_pending = _expiry_state(demo_by_slug.get(slug or ""), now)
        prospect_name = names_by_slug.get(slug or "")
        if kind == "prospect_photo":
            prospect_name = names_by_prospect_id.get(_prospect_id_from_key(key) or 0)
        items.append(
            StorageObject(
                key=key,
                kind=kind,
                size=entry["size"],
                last_modified=entry["last_modified"],
                url=r2_storage.public_url(key),
                slug=slug,
                prospect_name=prospect_name,
                expires_in_days=expires_in,
                is_expired=is_expired,
                ttl_pending=ttl_pending,
            )
        )

    items.sort(key=lambda o: o.last_modified or datetime.min.replace(tzinfo=UTC), reverse=True)
    return StorageListResponse(
        bucket=r2_storage.bucket_name(),
        public_base_url=settings.r2_public_base_url or "",
        items=items,
        total=len(items),
        total_size=sum(o.size for o in items),
        ttl_days=settings.demo_site_ttl_days,
    )


@router.get("/health", response_model=StorageHealthResponse)
async def storage_health(
    _admin: User = Depends(require_admin),
    db: Session = Depends(get_db),
) -> StorageHealthResponse:
    """
    Report R2 ↔ DB inconsistencies — the proof that the demo-TTL cleanup works.

    Returns:
        Orphan objects, missing objects and expired leftovers.
    """
    _ensure_configured()
    from enums.demo_video_status import DemoVideoStatus

    objects = await _list_async(r2_storage.VIDEOS_WEBSITES_PREFIX)
    # Les fonds de montage ``-background.mp4`` ne sont pas des livrables autonomes : hors comparaison
    # orphelins/manquants (sinon ils apparaîtraient toujours comme orphelins).
    keys = {item["key"] for item in objects if not item["key"].endswith(_BACKGROUND_SUFFIX)}

    ready_slugs = {
        slug
        for (slug,) in db.query(DemoSite.slug).filter(DemoSite.video_status == DemoVideoStatus.READY.value).all()
        if slug
    }
    expected = {r2_storage.website_video_key(slug) for slug in ready_slugs}

    now = datetime.now(UTC)
    expired = _expired_website_keys(db, objects, now)

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


@router.post("/delete-objects", response_model=StorageActionResponse)
async def delete_storage_objects(
    payload: DeleteObjectsRequest,
    _admin: User = Depends(require_admin),
) -> StorageActionResponse:
    """
    Delete several objects at once (the storage page's multi-selection).

    Args:
        payload: The object keys to remove; blank entries are ignored.

    Returns:
        How many objects were removed.
    """
    _ensure_configured()
    keys = [key for key in payload.keys if key.strip()]
    if not keys:
        return StorageActionResponse(deleted=0, message="Aucun fichier sélectionné.")
    import asyncio

    await asyncio.to_thread(r2_storage.delete_many, keys)
    return StorageActionResponse(deleted=len(keys), message=f"{len(keys)} fichier(s) supprimé(s).")


@router.post("/purge-expired", response_model=StorageActionResponse)
async def purge_expired_objects(
    _admin: User = Depends(require_admin),
    db: Session = Depends(get_db),
) -> StorageActionResponse:
    """
    Delete every demo deliverable whose demo has expired or vanished (video + thumbnail + background).

    Anchored on the same demo lifecycle as the listing's expiry badge, so this removes exactly what the
    page flags — never a file still tied to a live or not-yet-sent demo.

    Returns:
        How many objects were removed.
    """
    _ensure_configured()
    now = datetime.now(UTC)
    objects: list[dict[str, Any]] = []
    for prefix in (
        r2_storage.VIDEOS_WEBSITES_PREFIX,
        r2_storage.IMAGES_WEBSITES_PREFIX,
    ):
        objects.extend(await _list_async(prefix))
    stale = _expired_website_keys(db, objects, now)

    if stale:
        import asyncio

        await asyncio.to_thread(r2_storage.delete_many, stale)
    return StorageActionResponse(deleted=len(stale), message=f"{len(stale)} objet(s) expiré(s) supprimé(s).")


@router.post("/purge-orphan-prospect-photos", response_model=StorageActionResponse)
async def purge_orphan_prospect_photos(
    _admin: User = Depends(require_admin),
    db: Session = Depends(get_db),
) -> StorageActionResponse:
    """
    Delete rehosted prospect photos that no enrichment record references any more.

    Deleting a prospect removes its photos inline and a re-enrichment reuses content-hash keys, but a
    replaced photo or an interrupted delete can leave an object behind. This reconciles the bucket
    against the enrichment table: every ``images/prospects/`` object whose key is referenced by no
    enrichment (``photos`` or ``logo_url``) is removed.

    Returns:
        How many orphan objects were removed.
    """
    _ensure_configured()
    referenced = _referenced_prospect_photo_keys(db)
    objects = await _list_async(r2_storage.IMAGES_PROSPECTS_PREFIX)
    orphans = [item["key"] for item in objects if item["key"] not in referenced]
    if orphans:
        import asyncio

        await asyncio.to_thread(r2_storage.delete_many, orphans)
    return StorageActionResponse(deleted=len(orphans), message=f"{len(orphans)} photo(s) orpheline(s) supprimée(s).")


@router.post("/upload", response_model=StorageUploadResponse)
async def upload_manual_file(
    file: UploadFile = File(...),
    _admin: User = Depends(require_admin),
) -> StorageUploadResponse:
    """
    Store a hand-picked file on R2 and return its permanent public URL.

    Args:
        file: The uploaded image or PDF.

    Returns:
        The stored object — paste ``url`` into a prospect's info.
    """
    _ensure_configured()
    data = await file.read()
    stored = await manual_upload_service.store_bytes(
        data=data,
        content_type=file.content_type,
        filename=file.filename,
    )
    return StorageUploadResponse(
        key=stored.key,
        url=stored.url,
        kind=_classify(stored.key),
        size=stored.size,
        message="Fichier importé.",
    )


@router.post("/import-url", response_model=StorageUploadResponse)
async def import_manual_url(
    payload: ImportUrlRequest,
    _admin: User = Depends(require_admin),
) -> StorageUploadResponse:
    """
    Rehost a remote file (e.g. an expiring Facebook ``fbcdn`` image) onto R2, and return its URL.

    Args:
        payload: The source URL to download and store.

    Returns:
        The stored object — paste ``url`` into a prospect's info.
    """
    _ensure_configured()
    stored = await manual_upload_service.import_from_url(payload.url)
    return StorageUploadResponse(
        key=stored.key,
        url=stored.url,
        kind=_classify(stored.key),
        size=stored.size,
        message="Fichier importé depuis l'URL.",
    )


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

    to_copy = [key for key, item in source.items() if key not in target or target[key]["etag"] != item["etag"]]
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
