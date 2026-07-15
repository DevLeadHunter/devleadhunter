"""
Storage service for support attachments.
"""
from __future__ import annotations

import os
from dataclasses import dataclass
from datetime import datetime
from ftplib import FTP, FTP_TLS, error_perm
from pathlib import Path
from typing import Optional
from uuid import uuid4

from fastapi import HTTPException, UploadFile, status

from core.config import settings


@dataclass(slots=True, frozen=True)
class StoredAttachment:
    """
    Metadata returned after storing an attachment.
    """

    object_key: str
    backend: str  # "local" | "ftp"
    original_filename: str
    content_type: str


class SupportStorageService:
    """
    Service responsible for persisting support attachments.
    """

    def __init__(self) -> None:
        self._allowed_mime = {
            mime.strip().lower()
            for mime in settings.support_attachment_allowed_mime.split(",")
            if mime.strip()
        }
        self._max_bytes = settings.support_max_attachment_mb * 1024 * 1024
        self._local_base = Path(settings.support_local_upload_dir)

    async def store(self, file: Optional[UploadFile]) -> Optional[StoredAttachment]:
        """
        Persist an uploaded file and return its metadata.
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
        object_key = self._build_object_key(extension)

        if settings.is_production and self._has_ftp_credentials():
            self._upload_to_ftp(object_key, data)
            return StoredAttachment(
                object_key=object_key,
                backend="ftp",
                original_filename=file.filename or f"attachment{extension}",
                content_type=content_type,
            )

        self._save_locally(object_key, data)
        return StoredAttachment(
            object_key=object_key,
            backend="local",
            original_filename=file.filename or f"attachment{extension}",
            content_type=content_type,
        )

    async def store_many(self, files: list[UploadFile]) -> list[StoredAttachment]:
        """
        Persist multiple uploaded files and return their metadata.
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

    def _build_object_key(self, extension: str) -> str:
        """
        Generate a unique storage object key.
        """
        now = datetime.utcnow()
        return f"{now:%Y/%m}/{uuid4().hex}{extension}"

    def _has_ftp_credentials(self) -> bool:
        """
        Ensure FTP credentials are configured.
        """
        return bool(
            settings.support_ftp_host
            and settings.support_ftp_user
            and settings.support_ftp_password
        )

    def _upload_to_ftp(self, object_key: str, data: bytes) -> None:
        """
        Upload the file to the configured FTP server.
        """
        host = settings.support_ftp_host
        if not host:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="FTP configuration is missing."
            )

        ftp_class = FTP_TLS if settings.support_ftp_use_tls else FTP
        ftp = ftp_class()

        try:
            ftp.connect(host=host, port=settings.support_ftp_port, timeout=30)
            if isinstance(ftp, FTP_TLS):
                ftp.auth()
                ftp.prot_p()
            ftp.login(settings.support_ftp_user, settings.support_ftp_password)

            self._ensure_remote_directories(ftp, settings.support_ftp_base_dir)

            # Navigate to target directory
            dir_name, file_name = os.path.split(object_key)
            target_dir = self._join_remote_path(settings.support_ftp_base_dir, dir_name)
            self._ensure_remote_directories(ftp, target_dir)
            ftp.cwd(target_dir)

            ftp.storbinary(f"STOR {file_name}", self._to_bytes_io(data))
        except Exception as exc:  # pragma: no cover - networking issues
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to upload file to FTP server."
            ) from exc
        finally:
            try:
                ftp.quit()
            except Exception:
                ftp.close()

    def _ensure_remote_directories(self, ftp: FTP, path: str) -> None:
        """
        Ensure all directories in the remote path exist.
        """
        segments = [segment for segment in path.strip("/").split("/") if segment]
        if not segments:
            return

        ftp.cwd("/")
        for segment in segments:
            try:
                ftp.mkd(segment)
            except error_perm as exc:
                # Ignore "directory exists"
                if not exc.args or not str(exc.args[0]).startswith("550"):
                    raise
            ftp.cwd(segment)

    def _save_locally(self, object_key: str, data: bytes) -> None:
        """
        Persist file on the local filesystem.
        """
        target_path = self._local_base / object_key
        target_path.parent.mkdir(parents=True, exist_ok=True)
        target_path.write_bytes(data)

    def _join_remote_path(self, base: str, relative: str) -> str:
        """
        Join FTP paths safely.
        """
        base = base.rstrip("/")
        relative = relative.strip("/")
        if not relative:
            return base or "/"
        return f"{base}/{relative}" if base else f"/{relative}"

    @staticmethod
    def _to_bytes_io(data: bytes):
        """
        Provide a BytesIO instance in a way compatible with limited environments.
        """
        from io import BytesIO

        return BytesIO(data)


support_storage_service = SupportStorageService()


