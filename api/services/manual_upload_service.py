"""Hand uploads to R2, from the admin storage page.

Two entry points feed the same permanent home (``uploads/manual/{yyyy}/{mm}/{uuid}.{ext}``):

- a file uploaded straight from the browser;
- a URL fetched server-side — handy to capture an **expiring** Facebook ``fbcdn`` image before its
  signed link dies, then paste the durable R2 URL into a prospect's photos.

Everything is admin-only, validated against an image/PDF allowlist with a hard size cap, and never
auto-expires (the manual prefix is excluded from every cleanup pass).
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from pathlib import Path
from urllib.parse import urlparse

import httpx
from fastapi import HTTPException, status

from services.r2_storage_service import r2_storage

logger = logging.getLogger(__name__)

# Poids max d'un import manuel (marge large pour un visuel haute définition ou un PDF de menu).
_MAX_UPLOAD_BYTES: int = 15 * 1024 * 1024
_DOWNLOAD_TIMEOUT_SECONDS: float = 20.0
# En-têtes navigateur pour que fbcdn nous serve les mêmes octets qu'à la balise <img> d'origine.
_DOWNLOAD_HEADERS: dict[str, str] = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
    ),
    "Accept": "image/avif,image/webp,image/apng,image/*,*/*;q=0.8",
    "Referer": "https://www.facebook.com/",
}
# Extension explicite par type MIME — ``mimetypes.guess_extension`` est dépendant de la plateforme
# (il peut renvoyer ``.jpe`` pour du JPEG) et l'extension de la clé est visible sur la page stockage.
_EXTENSION_BY_MIME: dict[str, str] = {
    "image/jpeg": ".jpg",
    "image/jpg": ".jpg",
    "image/png": ".png",
    "image/webp": ".webp",
    "image/gif": ".gif",
    "image/avif": ".avif",
    "application/pdf": ".pdf",
}
_ALLOWED_LABEL: str = "JPEG, PNG, WebP, GIF, AVIF, PDF"


@dataclass(frozen=True)
class StoredUpload:
    """One object written to R2 by a manual import."""

    key: str
    url: str
    content_type: str
    size: int


class ManualUploadService:
    """Store hand-picked files (raw bytes or a remote URL) on permanent R2 storage."""

    @staticmethod
    def _ensure_configured() -> None:
        """Fail with a readable 503 when R2 is not configured.

        Raises:
            HTTPException: 503 when the R2 credentials/bucket are missing.
        """
        if not r2_storage.is_configured():
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Stockage R2 non configuré (voir R2_* dans api/.env).",
            )

    @staticmethod
    def _normalise_content_type(raw: str | None) -> str:
        """Reduce a raw ``Content-Type`` header to its bare, lower-cased MIME type.

        Args:
            raw: The header value (may carry a charset or be None).

        Returns:
            The lower-cased MIME type, or an empty string.
        """
        return (raw or "").split(";")[0].strip().lower()

    @staticmethod
    def _sniff(data: bytes) -> str | None:
        """Guess an allowed MIME type from a file's magic bytes.

        Last-resort detection when neither the header nor the file name carries a usable type.

        Args:
            data: The file's leading bytes.

        Returns:
            The detected MIME type, or None when the signature is not a supported image/PDF.
        """
        if data[:3] == b"\xff\xd8\xff":
            return "image/jpeg"
        if data[:8] == b"\x89PNG\r\n\x1a\n":
            return "image/png"
        if data[:6] in (b"GIF87a", b"GIF89a"):
            return "image/gif"
        if data[:4] == b"RIFF" and data[8:12] == b"WEBP":
            return "image/webp"
        if data[:4] == b"%PDF":
            return "application/pdf"
        # AVIF : boîte ``ftyp`` avec la marque ``avif`` dans les tout premiers octets.
        if data[4:8] == b"ftyp" and b"avif" in data[8:20]:
            return "image/avif"
        return None

    def _resolve_type(self, content_type: str | None, filename: str | None, data: bytes) -> tuple[str, str]:
        """Resolve the MIME type and file extension, from the header, then the name, then the bytes.

        Args:
            content_type: The declared ``Content-Type`` (header or upload field).
            filename: The original file name or URL path, read for its extension only.
            data: The file bytes, sniffed as a last resort.

        Returns:
            A ``(content_type, extension)`` pair, both non-empty.

        Raises:
            HTTPException: 400 when the file is not a supported image/PDF.
        """
        normalised: str = self._normalise_content_type(content_type)
        extension: str | None = _EXTENSION_BY_MIME.get(normalised)

        if extension is None and filename:
            suffix: str = Path(filename).suffix.lower()
            matched_mime: str | None = next((mime for mime, ext in _EXTENSION_BY_MIME.items() if ext == suffix), None)
            if matched_mime is not None:
                normalised, extension = matched_mime, suffix

        if extension is None:
            sniffed: str | None = self._sniff(data)
            if sniffed is not None:
                normalised, extension = sniffed, _EXTENSION_BY_MIME[sniffed]

        if extension is None:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Type de fichier non supporté. Formats acceptés : {_ALLOWED_LABEL}.",
            )
        return normalised, extension

    async def store_bytes(self, *, data: bytes, content_type: str | None, filename: str | None = None) -> StoredUpload:
        """Store raw bytes on R2 under the manual-uploads prefix.

        Args:
            data: The file payload.
            content_type: The declared MIME type (validated against the allowlist).
            filename: The original file name, used to recover the extension when the type is generic.

        Returns:
            The stored object (key, public URL, MIME type, size).

        Raises:
            HTTPException: 400/413 on an empty, oversized or unsupported file; 500 on a storage error.
        """
        self._ensure_configured()
        if not data:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Fichier vide.")
        if len(data) > _MAX_UPLOAD_BYTES:
            raise HTTPException(
                status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
                detail=f"Le fichier dépasse {_MAX_UPLOAD_BYTES // (1024 * 1024)} Mo.",
            )
        resolved_type, extension = self._resolve_type(content_type, filename, data)
        key: str = r2_storage.manual_upload_key(extension)
        try:
            url: str = await r2_storage.upload_bytes_async(key, data, resolved_type)
        except Exception as exc:
            logger.exception("[ManualUpload] R2 upload failed key=%s", key)
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Impossible d'enregistrer le fichier sur le stockage. Réessayez.",
            ) from exc
        return StoredUpload(key=key, url=url, content_type=resolved_type, size=len(data))

    async def import_from_url(self, url: str) -> StoredUpload:
        """Download a remote file server-side and store it permanently on R2.

        Purpose-built for expiring Facebook ``fbcdn`` URLs: fetched with browser-like headers so the
        CDN serves the bytes, then rehosted so the link no longer dies after a few days.

        Args:
            url: The source URL (http/https).

        Returns:
            The stored object (key, public URL, MIME type, size).

        Raises:
            HTTPException: 400 on an invalid URL; 502 when the source is unreachable or errored;
                400/413 when the downloaded file is unsupported or oversized.
        """
        self._ensure_configured()
        clean: str = (url or "").strip()
        if not (clean.lower().startswith("http://") or clean.lower().startswith("https://")):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="URL invalide : elle doit commencer par http:// ou https://.",
            )
        try:
            async with httpx.AsyncClient(
                timeout=httpx.Timeout(_DOWNLOAD_TIMEOUT_SECONDS),
                headers=_DOWNLOAD_HEADERS,
                follow_redirects=True,
            ) as client:
                response: httpx.Response = await client.get(clean)
        except httpx.HTTPError as exc:
            raise HTTPException(
                status_code=status.HTTP_502_BAD_GATEWAY,
                detail="Impossible de télécharger le fichier depuis cette URL.",
            ) from exc
        if response.status_code != 200:
            raise HTTPException(
                status_code=status.HTTP_502_BAD_GATEWAY,
                detail=f"La source a répondu {response.status_code} — lien expiré ou protégé ?",
            )
        return await self.store_bytes(
            data=response.content,
            content_type=response.headers.get("content-type"),
            filename=urlparse(clean).path,
        )


manual_upload_service = ManualUploadService()
