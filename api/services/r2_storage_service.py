"""Cloudflare R2 object storage (S3-compatible) — the single storage backend."""
from __future__ import annotations

import asyncio
import mimetypes
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Optional

try:
    import boto3
    from botocore.config import Config
    from botocore.exceptions import ClientError
except ImportError as _boto_import_error:  # pragma: no cover
    boto3 = None  # type: ignore[assignment]
    Config = None  # type: ignore[assignment, misc]
    ClientError = Exception  # type: ignore[assignment, misc]
    _BOTO_IMPORT_ERROR: Optional[ImportError] = _boto_import_error
else:
    _BOTO_IMPORT_ERROR = None

from core.config import settings

S3_DELETE_BATCH_SIZE = 1000
DEFAULT_CONTENT_TYPE = "application/octet-stream"


class R2StorageService:
    """
    Reads and writes every media file the product serves, on Cloudflare R2.

    Local and production behave identically — both talk to R2, only the bucket and the public URL
    differ, resolved from `ENV`. The key layout is known here and nowhere else::

        videos/websites/{slug}.mp4               generated prospection video
        videos/presenter/{user_id}.mp4           source webcam clip, one per user
        images/websites/{slug}.jpg               email thumbnail ({vignette_video})
        images/support/{yyyy}/{mm}/{uuid}.{ext}  support ticket attachments

    boto3 calls block, so async callers must go through the `*_async` methods.
    """

    VIDEOS_WEBSITES_PREFIX = "videos/websites"
    VIDEOS_PRESENTER_PREFIX = "videos/presenter"
    IMAGES_WEBSITES_PREFIX = "images/websites"
    IMAGES_SUPPORT_PREFIX = "images/support"

    def __init__(self) -> None:
        self._client: Any = None

    def is_configured(self) -> bool:
        """
        Tell whether R2 can be used at all.

        Returns:
            Whether boto3, the credentials, the bucket and the public URL are all present.
        """
        if boto3 is None:
            return False
        return bool(
            (settings.r2_endpoint or "").strip()
            and (settings.r2_access_key_id or "").strip()
            and (settings.r2_secret_access_key or "").strip()
            and (settings.r2_bucket or "").strip()
            and (settings.r2_public_base_url or "").strip()
        )

    def require_configured(self) -> None:
        """
        Fail loudly when R2 is unusable, rather than letting a call fail obscurely later.

        Raises:
            RuntimeError: boto3 is missing, or an environment variable is not set.
        """
        if boto3 is None:
            raise RuntimeError(
                "Le package `boto3` est absent. Installez-le avec `pip install boto3` "
                "ou reconstruisez le venv."
            ) from _BOTO_IMPORT_ERROR
        if not self.is_configured():
            raise RuntimeError(
                "Cloudflare R2 requis : renseignez R2_ENDPOINT, R2_ACCESS_KEY_ID, "
                "R2_SECRET_ACCESS_KEY, R2_BUCKET_DEV/PROD et R2_PUBLIC_BASE_URL_DEV/PROD "
                "dans api/.env (local ET production)."
            )

    def bucket_name(self) -> str:
        """
        Read the bucket of the current environment.

        Returns:
            The bucket name.

        Raises:
            RuntimeError: No bucket is configured.
        """
        bucket: str = (settings.r2_bucket or "").strip()
        if not bucket:
            raise RuntimeError("Bucket R2 manquant (R2_BUCKET_DEV / R2_BUCKET_PROD)")
        return bucket

    def prod_bucket_name(self) -> str:
        """
        Read the production bucket, which only the prod → dev sync targets.

        Returns:
            The production bucket name.

        Raises:
            RuntimeError: No production bucket is configured.
        """
        bucket: str = (settings.r2_bucket_prod or "").strip()
        if not bucket:
            raise RuntimeError("R2_BUCKET_PROD manquant")
        return bucket

    @classmethod
    def website_video_key(cls, slug: str) -> str:
        """
        Build the key of a demo's prospection video.

        Args:
            slug: Demo slug — never the prospect id, which is not public.

        Returns:
            The object key.
        """
        return f"{cls.VIDEOS_WEBSITES_PREFIX}/{slug}.mp4"

    @classmethod
    def website_thumbnail_key(cls, slug: str) -> str:
        """
        Build the key of a demo's email thumbnail.

        Args:
            slug: Demo slug.

        Returns:
            The object key.
        """
        return f"{cls.IMAGES_WEBSITES_PREFIX}/{slug}.jpg"

    @classmethod
    def presenter_key(cls, user_id: int) -> str:
        """
        Build the key of a user's source webcam clip.

        Args:
            user_id: Owner of the clip.

        Returns:
            The object key.
        """
        return f"{cls.VIDEOS_PRESENTER_PREFIX}/{user_id}.mp4"

    @classmethod
    def support_key(cls, original_filename: Optional[str]) -> str:
        """
        Build the key of a support ticket attachment, filed by year and month.

        Args:
            original_filename: Uploaded name, read for its extension only.

        Returns:
            A unique object key.
        """
        extension: str = Path(original_filename or "file").suffix or ".png"
        if not extension.startswith("."):
            extension = f".{extension}"
        now = datetime.now(timezone.utc)
        return f"{cls.IMAGES_SUPPORT_PREFIX}/{now:%Y/%m}/{uuid.uuid4().hex}{extension}"

    @staticmethod
    def public_url(key: str) -> str:
        """
        Build the public read URL of an object.

        Args:
            key: Object key.

        Returns:
            An absolute HTTPS URL.

        Raises:
            RuntimeError: No public base URL is configured.
        """
        base = settings.r2_public_base_url
        if not base:
            raise RuntimeError("R2_PUBLIC_BASE_URL_DEV / _PROD manquant")
        return f"{base}/{key.lstrip('/')}"

    def upload_file(self, local_path: Path | str, key: str, content_type: Optional[str] = None) -> str:
        """
        Upload a local file, overwriting the key when it already exists.

        Args:
            local_path: Source file.
            key: Target object key.
            content_type: MIME type, guessed from the key when omitted.

        Returns:
            The public URL of the uploaded object.

        Raises:
            FileNotFoundError: The source file does not exist.
        """
        path = Path(local_path)
        if not path.is_file():
            raise FileNotFoundError(f"Fichier introuvable pour l'upload R2 : {path}")
        self._client_or_fail().upload_file(
            str(path),
            self.bucket_name(),
            key,
            ExtraArgs={"ContentType": content_type or self._guess_content_type(key)},
        )
        return self.public_url(key)

    def upload_bytes(self, key: str, data: bytes, content_type: Optional[str] = None) -> str:
        """
        Upload raw bytes, overwriting the key when it already exists.

        Args:
            key: Target object key.
            data: Binary payload.
            content_type: MIME type, guessed from the key when omitted.

        Returns:
            The public URL of the uploaded object.

        Raises:
            ValueError: The payload is empty.
        """
        if not data:
            raise ValueError("Contenu vide : rien à envoyer sur R2")
        self._client_or_fail().put_object(
            Bucket=self.bucket_name(),
            Key=key,
            Body=data,
            ContentType=content_type or self._guess_content_type(key),
        )
        return self.public_url(key)

    def download_to_path(self, key: str, local_path: Path | str) -> Path:
        """
        Download an object to disk, which ffmpeg needs since it cannot read a stream URL here.

        Args:
            key: Object key.
            local_path: Destination path; missing folders are created.

        Returns:
            The written path.
        """
        path = Path(local_path)
        path.parent.mkdir(parents=True, exist_ok=True)
        self._client_or_fail().download_file(self.bucket_name(), key, str(path))
        return path

    def exists(self, key: str) -> bool:
        """
        Tell whether an object is present in the bucket.

        Args:
            key: Object key.

        Returns:
            Whether the object exists.
        """
        try:
            self._client_or_fail().head_object(Bucket=self.bucket_name(), Key=key)
            return True
        except ClientError:
            return False

    def delete(self, key: str) -> None:
        """
        Delete an object, idempotently.

        Args:
            key: Object key.
        """
        self._client_or_fail().delete_object(Bucket=self.bucket_name(), Key=key)

    def delete_many(self, keys: list[str]) -> None:
        """
        Delete several objects, batched to the S3 per-request limit.

        Args:
            keys: Object keys; empty entries are ignored.
        """
        remaining: list[str] = [key for key in keys if key]
        if not remaining:
            return
        client = self._client_or_fail()
        bucket: str = self.bucket_name()
        for start in range(0, len(remaining), S3_DELETE_BATCH_SIZE):
            chunk: list[str] = remaining[start : start + S3_DELETE_BATCH_SIZE]
            client.delete_objects(
                Bucket=bucket,
                Delete={"Objects": [{"Key": key} for key in chunk], "Quiet": True},
            )

    def list_objects(self, prefix: str = "", *, bucket: Optional[str] = None) -> list[dict[str, Any]]:
        """
        List the objects under a prefix, following pagination to the end.

        Args:
            prefix: Key prefix; empty lists the whole bucket.
            bucket: Bucket to read, defaulting to the current environment's.

        Returns:
            One `{key, size, last_modified, etag}` per object.
        """
        client = self._client_or_fail()
        target: str = bucket or self.bucket_name()
        results: list[dict[str, Any]] = []
        token: Optional[str] = None
        while True:
            kwargs: dict[str, Any] = {"Bucket": target, "Prefix": prefix}
            if token:
                kwargs["ContinuationToken"] = token
            response = client.list_objects_v2(**kwargs)
            for item in response.get("Contents", []):
                # The Cloudflare console materialises "folders" as empty objects ending in "/".
                if str(item["Key"]).endswith("/"):
                    continue
                results.append(
                    {
                        "key": item["Key"],
                        "size": int(item.get("Size", 0) or 0),
                        "last_modified": item.get("LastModified"),
                        "etag": str(item.get("ETag", "")).strip('"'),
                    }
                )
            if not response.get("IsTruncated"):
                break
            token = response.get("NextContinuationToken")
        return results

    def copy_from_bucket(self, source_bucket: str, key: str) -> None:
        """
        Copy an object from another bucket of the same account, server-side.

        Nothing transits through the API — R2 copies internally, which is what makes the
        prod → dev sync cheap.

        Args:
            source_bucket: Bucket to read from.
            key: Key, identical on both sides.
        """
        self._client_or_fail().copy_object(
            Bucket=self.bucket_name(),
            Key=key,
            CopySource={"Bucket": source_bucket, "Key": key},
        )

    async def upload_file_async(
        self, local_path: Path | str, key: str, content_type: Optional[str] = None
    ) -> str:
        """
        Upload a local file without blocking the event loop.

        Args:
            local_path: Source file.
            key: Target object key.
            content_type: MIME type, guessed from the key when omitted.

        Returns:
            The public URL of the uploaded object.
        """
        return await asyncio.to_thread(self.upload_file, local_path, key, content_type)

    async def upload_bytes_async(
        self, key: str, data: bytes, content_type: Optional[str] = None
    ) -> str:
        """
        Upload raw bytes without blocking the event loop.

        Args:
            key: Target object key.
            data: Binary payload.
            content_type: MIME type, guessed from the key when omitted.

        Returns:
            The public URL of the uploaded object.
        """
        return await asyncio.to_thread(self.upload_bytes, key, data, content_type)

    async def download_to_path_async(self, key: str, local_path: Path | str) -> Path:
        """
        Download an object to disk without blocking the event loop.

        Args:
            key: Object key.
            local_path: Destination path.

        Returns:
            The written path.
        """
        return await asyncio.to_thread(self.download_to_path, key, local_path)

    async def delete_async(self, key: str) -> None:
        """
        Delete an object without blocking the event loop.

        Args:
            key: Object key.
        """
        await asyncio.to_thread(self.delete, key)

    def _client_or_fail(self) -> Any:
        """
        Return the boto3 client, building it on first use.

        Returns:
            A ready S3 client pointed at R2.

        Raises:
            RuntimeError: R2 is not configured.
        """
        if self._client is not None:
            return self._client
        self.require_configured()
        self._client = boto3.client(
            "s3",
            endpoint_url=settings.r2_endpoint,
            aws_access_key_id=settings.r2_access_key_id,
            aws_secret_access_key=settings.r2_secret_access_key,
            # R2 has no regions: "auto" is the expected value.
            region_name="auto",
            config=Config(
                signature_version="s3v4",
                retries={"max_attempts": 3, "mode": "standard"},
            ),
        )
        return self._client

    @staticmethod
    def _guess_content_type(filename: Optional[str], fallback: str = DEFAULT_CONTENT_TYPE) -> str:
        """
        Guess a MIME type from a file name or an object key.

        Args:
            filename: Name or key to inspect.
            fallback: Value used when the type cannot be determined.

        Returns:
            The MIME type.
        """
        guessed, _ = mimetypes.guess_type(filename or "")
        return guessed or fallback


r2_storage = R2StorageService()
