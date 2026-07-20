"""
Storage service for support attachments — Cloudflare R2, single backend.

Same behaviour in local and production (no more ``local`` / ``ftp`` split):
objects land in the bucket under ``images/support/{yyyy}/{mm}/{uuid}.{ext}``
and are read through the public R2 URL.
"""
from __future__ import annotations

import logging
import os
from dataclasses import dataclass
from typing import Optional

from fastapi import HTTPException, UploadFile, status

from core.config import settings
from services import r2_storage_service

logger = logging.getLogger(__name__)

# Conservé pour la colonne `support_attachments.storage_backend` (historique).
STORAGE_BACKEND = "r2"


@dataclass(slots=True, frozen=True)
class StoredAttachment:
    """
    Metadata returned after storing an attachment.
    """

    object_key: str
    backend: str  # toujours "r2" désormais
    original_filename: str
    content_type: str


class SupportStorageService:
    """
    Service responsible for persisting support attachments on R2.
    """

    def __init__(self) -> None:
        self._allowed_mime = {
            mime.strip().lower()
            for mime in settings.support_attachment_allowed_mime.split(",")
            if mime.strip()
        }
        self._max_bytes = settings.support_max_attachment_mb * 1024 * 1024

    async def store(self, file: Optional[UploadFile]) -> Optional[StoredAttachment]:
        """
        Persist an uploaded file on R2 and return its metadata.

        @param file - Incoming upload (None is a no-op).
        @returns Stored attachment metadata, or None when no file was given.
        @throws HTTPException 400/413/500 on invalid format, size or storage failure.
        """
        if file is None:
            return None

        content_type = (file.content_type or "").lower()
        if content_type not in self._allowed_mime:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Unsupported image format. Allowed: JPG, PNG, WEBP."
            )

        data = await file.read()
        if not data:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Uploaded file is empty."
            )

        if len(data) > self._max_bytes:
            raise HTTPException(
                status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
                detail=f"File exceeds maximum size of {settings.support_max_attachment_mb} MB."
            )

        extension = self._extension_from_content_type(content_type, file.filename)
        object_key = r2_storage_service.support_key(f"attachment{extension}")

        try:
            await r2_storage_service.upload_bytes_async(object_key, data, content_type)
        except Exception as exc:  # noqa: BLE001 — surfaced as a readable API error
            logger.exception("[Support] R2 upload failed for key=%s", object_key)
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to upload file to storage."
            ) from exc

        return StoredAttachment(
            object_key=object_key,
            backend=STORAGE_BACKEND,
            original_filename=file.filename or f"attachment{extension}",
            content_type=content_type,
        )

    async def store_many(self, files: list[UploadFile]) -> list[StoredAttachment]:
        """
        Persist multiple uploaded files and return their metadata.

        @param files - Incoming uploads.
        @returns Metadata of every stored attachment.
        """
        if not files:
            return []

        stored: list[StoredAttachment] = []
        for upload in files:
            stored_file = await self.store(upload)
            if stored_file:
                stored.append(stored_file)
        return stored

    def _extension_from_content_type(self, content_type: str, filename: Optional[str]) -> str:
        """
        Infer file extension.

        @param content_type - MIME type of the upload.
        @param filename - Original filename, used as a fallback.
        @returns Extension including the leading dot.
        @throws HTTPException 400 when it cannot be determined.
        """
        mapping = {
            "image/jpeg": ".jpg",
            "image/png": ".png",
            "image/webp": ".webp",
        }
        if content_type in mapping:
            return mapping[content_type]

        if filename:
            _, ext = os.path.splitext(filename)
            if ext:
                return ext.lower()

        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Unable to determine file extension."
        )


support_storage_service = SupportStorageService()
