"""Profile photo management (one photo per user, stored on R2).

Today the photo is drawn as the presenter bubble on prospection-video
thumbnails; it is a profile-level asset so future surfaces (signatures,
in-app avatar…) can reuse it without moving it.
"""

from __future__ import annotations

import logging
import shutil
import tempfile
from pathlib import Path

from fastapi import HTTPException, UploadFile, status
from sqlalchemy.orm import Session

from models.user import User
from services.r2_storage_service import r2_storage

logger = logging.getLogger(__name__)

# Formats image acceptés et poids max de l'upload.
_ALLOWED_PHOTO_CONTENT_TYPES: set[str] = {"image/jpeg", "image/png", "image/webp"}
_MAX_PHOTO_BYTES: int = 15 * 1024 * 1024
# Stockée en carré normalisé : les consommateurs n'ont plus qu'à masquer en cercle.
_PHOTO_STORED_SIDE_PX: int = 800


class ProfilePhotoService:
    """Upload, deletion and normalisation of the per-user profile photo."""

    async def store_photo(self, db: Session, user: User, file: UploadFile) -> str:
        """
        Persist the profile photo (replaces any previous one).

        The photo is normalised at upload — EXIF-rotated, center-cropped square,
        resized — so consumers (the thumbnail bubble) only mask it into a circle.

        Args:
            db: Active database session.
            user: Owner of the photo.
            file: Uploaded image (JPEG / PNG / WebP).

        Returns:
            The R2 key stored on the user row.

        Raises:
            HTTPException: 400/413 on invalid format, size or unreadable image.
        """
        from io import BytesIO

        from PIL import Image, ImageOps, UnidentifiedImageError

        content_type = (file.content_type or "").lower().split(";")[0].strip()
        if content_type not in _ALLOWED_PHOTO_CONTENT_TYPES:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Format d'image non supporté. Formats acceptés : JPEG, PNG, WebP.",
            )
        data = await file.read()
        if not data:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Fichier image vide.")
        if len(data) > _MAX_PHOTO_BYTES:
            raise HTTPException(
                status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
                detail=f"La photo dépasse {_MAX_PHOTO_BYTES // (1024 * 1024)} MB.",
            )

        try:
            photo = ImageOps.exif_transpose(Image.open(BytesIO(data))).convert("RGB")
        except (UnidentifiedImageError, OSError) as exc:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Impossible de lire cette image (fichier corrompu ?).",
            ) from exc

        side = min(photo.size)
        left = (photo.width - side) // 2
        top = (photo.height - side) // 2
        photo = photo.crop((left, top, left + side, top + side))
        if side > _PHOTO_STORED_SIDE_PX:
            photo = photo.resize((_PHOTO_STORED_SIDE_PX, _PHOTO_STORED_SIDE_PX), Image.LANCZOS)

        work_dir = Path(tempfile.mkdtemp(prefix=f"profile-photo-{user.id}-"))
        try:
            local_path = work_dir / "profile-photo.jpg"
            photo.save(local_path, format="JPEG", quality=88)
            key = r2_storage.profile_photo_key(user.id)
            try:
                await r2_storage.upload_file_async(local_path, key, "image/jpeg")
            except Exception as exc:
                logger.exception("[ProfilePhoto] R2 upload failed for user=%s", user.id)
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail="Impossible d'enregistrer la photo sur le stockage. Réessayez.",
                ) from exc
        finally:
            shutil.rmtree(work_dir, ignore_errors=True)

        user.profile_photo_path = key
        db.commit()
        return key

    def delete_photo(self, db: Session, user: User) -> bool:
        """
        Delete the profile photo (object + user column). Returns True if one existed.

        Args:
            db: Active database session.
            user: Owner of the photo.

        Returns:
            Whether a photo was actually removed.
        """
        stored = str(user.profile_photo_path or "")
        if not stored:
            return False
        try:
            r2_storage.delete(stored)
        except Exception:
            logger.warning("[ProfilePhoto] cleanup failed for user=%s", user.id, exc_info=True)
        user.profile_photo_path = None
        db.commit()
        return True


profile_photo_service = ProfilePhotoService()
