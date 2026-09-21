"""Rehost a prospect's enrichment photos onto permanent R2 storage.

Facebook photos are served from ``fbcdn.net`` on **signed URLs that expire within days**, so a demo
site generated a few days after the scrape would fetch a dead link. Two kinds of value reach a durable
R2 home here:

- a base64 ``data:`` URI the desktop scraper captured (the preferred path — bytes grabbed on the
  residential IP while the link was fresh); it is decoded and uploaded, no network needed;
- a raw ``fbcdn``/``scontent`` URL still live — downloaded server-side then uploaded. This recovers a
  photo the scraper left as a URL (older capture, over the cap), and lets a re-hosting pass fix an
  existing enrichment without re-scraping (the user's photo curation is preserved).

Other URLs (a Google photo, an already-rehosted R2 URL) are passed through untouched. Everything is
best-effort — a rehost failure returns the original value so enrichment never breaks over a hiccup.
"""

from __future__ import annotations

import asyncio
import base64
import hashlib
import logging
import re

import httpx

from core.config import settings
from services.r2_storage_service import r2_storage

logger = logging.getLogger(__name__)

# Guard against a pathological payload — the scraper already caps a single photo at 3.5 MB.
_MAX_PHOTO_BYTES = 8 * 1024 * 1024
# Bound the concurrent uploads so a large gallery never opens dozens of R2 connections at once.
_UPLOAD_CONCURRENCY = 4
# Browser-like headers so fbcdn serves our client the same signed URL it served the <img> tag.
_DOWNLOAD_HEADERS: dict[str, str] = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
    ),
    "Accept": "image/avif,image/webp,image/apng,image/*,*/*;q=0.8",
    "Referer": "https://www.facebook.com/",
}
_DOWNLOAD_TIMEOUT_SECONDS = 15.0

_DATA_URI_RE = re.compile(r"^data:(image/[a-zA-Z0-9.+-]+);base64,(.+)$", re.DOTALL)
# Explicit extension per image MIME — ``mimetypes.guess_extension`` is platform-dependent
# (it can return ``.jpe`` for JPEG), and the key extension is user-visible in the storage page.
_EXTENSION_BY_MIME: dict[str, str] = {
    "image/jpeg": ".jpg",
    "image/jpg": ".jpg",
    "image/png": ".png",
    "image/webp": ".webp",
    "image/gif": ".gif",
    "image/avif": ".avif",
}

# Hosts whose image URLs die on us: a Storyblok asset vanishes when its space is deleted (demo
# expiry), a Google photo link rots after a few weeks, a Facebook-CDN URL is signed and expires.
# These are the ones worth copying onto permanent R2 so a revived J+30 demo keeps its exact images.
_FRAGILE_IMAGE_HOSTS: tuple[str, ...] = ("storyblok.com", "googleusercontent.com", "ggpht.com", "fbcdn", "scontent")
_IMAGE_EXTENSION_RE = re.compile(r"\.(?:jpe?g|png|webp|avif|gif)$", re.IGNORECASE)


class ProspectPhotoStorageService:
    """Moves captured enrichment photos to R2 and cleans them up when a prospect is deleted."""

    @staticmethod
    def _decode_data_uri(value: str) -> tuple[bytes, str, str] | None:
        """Decode a base64 image ``data:`` URI into its bytes, MIME type and file extension.

        Args:
            value: A candidate photo string (any non-data-URI returns None).

        Returns:
            A ``(bytes, content_type, extension)`` tuple, or None when the value is not a decodable
            base64 image data URI or exceeds the size guard.
        """
        match = _DATA_URI_RE.match(value.strip()) if isinstance(value, str) else None
        if not match:
            return None
        content_type = match.group(1).lower()
        try:
            data = base64.b64decode(match.group(2), validate=False)
        except (ValueError, TypeError):
            return None
        if not data or len(data) > _MAX_PHOTO_BYTES:
            return None
        extension = _EXTENSION_BY_MIME.get(content_type, ".jpg")
        return data, content_type, extension

    @staticmethod
    def _is_fb_cdn(url: str) -> bool:
        """Whether a URL is a Facebook-CDN photo (the expiring kind worth downloading to R2)."""
        lowered = url.lower()
        return "fbcdn" in lowered or "scontent" in lowered

    async def _download_fb_image(self, url: str) -> tuple[bytes, str, str] | None:
        """Download a live fbcdn/scontent photo into bytes for rehosting, or None.

        Only the expiring Facebook CDN is fetched — a Google photo (already durable) is left as its own
        URL. Returns None on any failure (dead/expired link, non-image, oversized) so rehosting degrades
        to keeping the original value.

        Args:
            url: A candidate photo URL.

        Returns:
            A ``(bytes, content_type, extension)`` tuple, or None.
        """
        if not isinstance(url, str) or not self._is_fb_cdn(url):
            return None
        try:
            async with httpx.AsyncClient(
                timeout=httpx.Timeout(_DOWNLOAD_TIMEOUT_SECONDS),
                headers=_DOWNLOAD_HEADERS,
                follow_redirects=True,
            ) as client:
                response = await client.get(url)
        except httpx.HTTPError:
            return None
        if response.status_code != 200:
            return None
        data = response.content
        if not data or len(data) > _MAX_PHOTO_BYTES:
            return None
        content_type = (response.headers.get("content-type") or "").split(";")[0].strip().lower()
        if content_type and not content_type.startswith("image/"):
            return None
        content_type = content_type or "image/jpeg"
        return data, content_type, _EXTENSION_BY_MIME.get(content_type, ".jpg")

    async def rehost_one(self, prospect_id: int, photo: str) -> str:
        """Move a single photo to permanent R2 storage, else return it unchanged.

        A captured base64 data URI is decoded; a live fbcdn/scontent URL is downloaded server-side.
        Anything else (a Google photo, an already-rehosted R2 URL) is left as-is.

        Args:
            prospect_id: Owner prospect — folders the object and scopes later cleanup.
            photo: A photo value from the enrichment (data URI, http(s) URL, or already an R2 URL).

        Returns:
            The permanent R2 URL when the photo could be rehosted, otherwise the original value (also on
            any storage failure — rehosting never breaks enrichment).
        """
        if not r2_storage.is_configured():
            return photo
        decoded = self._decode_data_uri(photo)
        if decoded is None:
            decoded = await self._download_fb_image(photo)
        if decoded is None:
            return photo
        data, content_type, extension = decoded
        digest = hashlib.sha1(data).hexdigest()[:16]
        key = r2_storage.prospect_photo_key(prospect_id, digest, extension)
        try:
            return await r2_storage.upload_bytes_async(key, data, content_type)
        except Exception as exc:  # storage hiccup must never fail the enrichment
            logger.warning("Prospect photo rehost failed for prospect_id=%s (%s): %s", prospect_id, key, exc)
            return photo

    @classmethod
    def is_fragile_image_url(cls, url: object) -> bool:
        """Whether a URL points to an image on a host that expires or gets deleted.

        True for a Storyblok asset (dies with its space), a Google photo (rots after weeks), a
        Facebook-CDN URL (signed, expires) or any ``http(s)`` URL ending in an image extension.
        False for a URL already on our R2 (permanent), a ``data:`` URI, or a non-image link.

        Args:
            url: A candidate value from a site's content.

        Returns:
            Whether the URL is a remote image worth copying to permanent R2.
        """
        if not isinstance(url, str):
            return False
        stripped = url.strip()
        lowered = stripped.lower()
        if not lowered.startswith(("http://", "https://")):
            return False
        base = (settings.r2_public_base_url or "").strip()
        if base and stripped.startswith(base):
            return False
        if any(host in lowered for host in _FRAGILE_IMAGE_HOSTS):
            return True
        path = lowered.split("?", 1)[0].split("#", 1)[0]
        return bool(_IMAGE_EXTENSION_RE.search(path))

    async def _download_remote_image(self, url: str) -> tuple[bytes, str, str] | None:
        """Download any remote image (Storyblok, Google, Facebook, …) into bytes for rehosting, or None.

        Unlike :meth:`_download_fb_image` (Facebook only), this fetches any ``http(s)`` image so a demo's
        published content images can be moved to R2. Returns None on any failure (dead link, non-image,
        oversized) so rehosting degrades to keeping the original URL.

        Args:
            url: A candidate image URL.

        Returns:
            A ``(bytes, content_type, extension)`` tuple, or None.
        """
        if not isinstance(url, str) or not url.lower().startswith(("http://", "https://")):
            return None
        headers = dict(_DOWNLOAD_HEADERS)
        if not self._is_fb_cdn(url):
            # The Facebook referer only helps fbcdn; drop it elsewhere so no host refuses it.
            headers.pop("Referer", None)
        try:
            async with httpx.AsyncClient(
                timeout=httpx.Timeout(_DOWNLOAD_TIMEOUT_SECONDS),
                headers=headers,
                follow_redirects=True,
            ) as client:
                response = await client.get(url)
        except httpx.HTTPError:
            return None
        if response.status_code != 200:
            return None
        data = response.content
        if not data or len(data) > _MAX_PHOTO_BYTES:
            return None
        content_type = (response.headers.get("content-type") or "").split(";")[0].strip().lower()
        if content_type and not content_type.startswith("image/"):
            return None
        content_type = content_type or "image/jpeg"
        return data, content_type, _EXTENSION_BY_MIME.get(content_type, ".jpg")

    async def rehost_remote_image(self, prospect_id: int, url: str) -> str:
        """Copy a fragile remote image onto permanent R2, else return it unchanged.

        The bytes are downloaded and re-uploaded as-is, so the image is pixel-identical — only its URL
        changes (fragile host → permanent R2). Anything not fragile (already on R2, a ``data:`` URI, a
        non-image link) is returned untouched. Best-effort: any download/upload failure returns the
        original URL so a restore never breaks over a hiccup.

        Args:
            prospect_id: Owner prospect — folders the object and scopes later cleanup.
            url: A content image URL.

        Returns:
            The permanent R2 URL when the image could be rehosted, otherwise the original URL.
        """
        if not r2_storage.is_configured() or not self.is_fragile_image_url(url):
            return url
        decoded = await self._download_remote_image(url)
        if decoded is None:
            return url
        data, content_type, extension = decoded
        digest = hashlib.sha1(data).hexdigest()[:16]
        key = r2_storage.prospect_photo_key(prospect_id, digest, extension)
        try:
            return await r2_storage.upload_bytes_async(key, data, content_type)
        except Exception as exc:  # storage hiccup must never fail the restore
            logger.warning("Content image rehost failed for prospect_id=%s (%s): %s", prospect_id, key, exc)
            return url

    async def rehost_photos(self, prospect_id: int, photos: list[str]) -> list[str]:
        """Rehost every captured data-URI photo of a prospect to R2, preserving order.

        Args:
            prospect_id: Owner prospect.
            photos: The enrichment photo list (mixed data URIs / URLs).

        Returns:
            The same list with each rehostable data URI replaced by its permanent R2 URL.
        """
        if not photos:
            return photos
        semaphore = asyncio.Semaphore(_UPLOAD_CONCURRENCY)

        async def _bounded(photo: str) -> str:
            async with semaphore:
                return await self.rehost_one(prospect_id, photo)

        return list(await asyncio.gather(*(_bounded(photo) for photo in photos)))

    async def delete_for_prospect(self, prospect_id: int) -> int:
        """Delete every R2 photo owned by a prospect (called when the prospect is deleted).

        Args:
            prospect_id: Prospect whose photos must be purged.

        Returns:
            The number of objects deleted (0 when R2 is unconfigured or the prospect had none).
        """
        if not r2_storage.is_configured():
            return 0
        prefix = r2_storage.prospect_photos_prefix(prospect_id)
        try:
            objects = await asyncio.to_thread(r2_storage.list_objects, prefix)
            keys = [entry["key"] for entry in objects]
            if keys:
                await asyncio.to_thread(r2_storage.delete_many, keys)
            return len(keys)
        except Exception as exc:  # cleanup is best-effort — never block a prospect deletion
            logger.warning("Prospect photo cleanup failed for prospect_id=%s: %s", prospect_id, exc)
            return 0


prospect_photo_storage = ProspectPhotoStorageService()
