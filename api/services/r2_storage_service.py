"""
Cloudflare R2 object storage (S3-compatible) — backend de stockage UNIQUE.

Même comportement en local et en production : les deux parlent à R2, seuls le
bucket et l'URL publique changent (résolus depuis ``ENV``). Remplace les anciens
backends disque local / FTP.

Arborescence (voir ``R2_STORAGE_PLAN.md``) :

    videos/websites/{slug}.mp4               vidéo de prospection générée
    videos/presenter/{user_id}.mp4           clip webcam source (par user)
    images/websites/{slug}.jpg               vignette email ({vignette_video})
    images/support/{yyyy}/{mm}/{uuid}.{ext}  pièces jointes des tickets support

Les appels boto3 sont bloquants : depuis du code async, les passer par
``asyncio.to_thread`` (helpers ``*_async`` fournis pour les cas courants).
"""
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

# Préfixes d'objets — un seul endroit connaît l'arborescence.
VIDEOS_WEBSITES_PREFIX = "videos/websites"
VIDEOS_PRESENTER_PREFIX = "videos/presenter"
IMAGES_WEBSITES_PREFIX = "images/websites"
IMAGES_SUPPORT_PREFIX = "images/support"

_client: Any = None


# --------------------------------------------------------------------------- #
# Configuration / client
# --------------------------------------------------------------------------- #

def is_configured() -> bool:
    """
    True quand R2 est utilisable (package présent + credentials + bucket + URL publique).

    @returns True si toutes les briques sont configurées.
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


def require_configured() -> None:
    """
    Lève une erreur explicite si R2 n'est pas configuré.

    @throws RuntimeError - Package manquant ou variables d'environnement absentes.
    """
    if boto3 is None:
        raise RuntimeError(
            "Le package `boto3` est absent. Installez-le avec `pip install boto3` "
            "ou reconstruisez le venv."
        ) from _BOTO_IMPORT_ERROR
    if not is_configured():
        raise RuntimeError(
            "Cloudflare R2 requis : renseignez R2_ENDPOINT, R2_ACCESS_KEY_ID, "
            "R2_SECRET_ACCESS_KEY, R2_BUCKET_DEV/PROD et R2_PUBLIC_BASE_URL_DEV/PROD "
            "dans api/.env (local ET production)."
        )


def _get_client() -> Any:
    """
    Client boto3 S3 pointé sur R2 (singleton).

    @returns Client boto3 prêt à l'emploi.
    """
    global _client
    if _client is not None:
        return _client
    require_configured()
    _client = boto3.client(
        "s3",
        endpoint_url=settings.r2_endpoint,
        aws_access_key_id=settings.r2_access_key_id,
        aws_secret_access_key=settings.r2_secret_access_key,
        # R2 n'a pas de régions : "auto" est la valeur attendue.
        region_name="auto",
        config=Config(
            signature_version="s3v4",
            retries={"max_attempts": 3, "mode": "standard"},
        ),
    )
    return _client


def bucket_name() -> str:
    """
    Bucket de l'environnement courant.

    @returns Nom du bucket.
    @throws RuntimeError - Bucket non configuré.
    """
    bucket = (settings.r2_bucket or "").strip()
    if not bucket:
        raise RuntimeError("Bucket R2 manquant (R2_BUCKET_DEV / R2_BUCKET_PROD)")
    return bucket


def prod_bucket_name() -> str:
    """
    Bucket de production — utilisé uniquement par la sync prod → dev.

    @returns Nom du bucket de prod.
    @throws RuntimeError - Bucket de prod non configuré.
    """
    bucket = (settings.r2_bucket_prod or "").strip()
    if not bucket:
        raise RuntimeError("R2_BUCKET_PROD manquant")
    return bucket


# --------------------------------------------------------------------------- #
# Clés d'objets
# --------------------------------------------------------------------------- #

def website_video_key(slug: str) -> str:
    """Clé de la vidéo de prospection d'une démo (``slug``, jamais ``prospect_id``)."""
    return f"{VIDEOS_WEBSITES_PREFIX}/{slug}.mp4"


def website_thumbnail_key(slug: str) -> str:
    """Clé de la vignette email d'une démo."""
    return f"{IMAGES_WEBSITES_PREFIX}/{slug}.jpg"


def presenter_key(user_id: int) -> str:
    """Clé du clip webcam source d'un utilisateur."""
    return f"{VIDEOS_PRESENTER_PREFIX}/{user_id}.mp4"


def support_key(original_filename: Optional[str]) -> str:
    """
    Clé d'une pièce jointe de ticket support, rangée par année/mois.

    @param original_filename - Nom d'origine (pour l'extension).
    @returns Clé unique dans le bucket.
    """
    extension = Path(original_filename or "file").suffix or ".png"
    if not extension.startswith("."):
        extension = f".{extension}"
    now = datetime.now(timezone.utc)
    return f"{IMAGES_SUPPORT_PREFIX}/{now:%Y/%m}/{uuid.uuid4().hex}{extension}"


def public_url(key: str) -> str:
    """
    URL publique de lecture d'un objet.

    @param key - Clé dans le bucket.
    @returns URL HTTPS absolue.
    @throws RuntimeError - URL publique non configurée.
    """
    base = settings.r2_public_base_url
    if not base:
        raise RuntimeError("R2_PUBLIC_BASE_URL_DEV / _PROD manquant")
    return f"{base}/{key.lstrip('/')}"


def _guess_content_type(filename: Optional[str], fallback: str = "application/octet-stream") -> str:
    """
    Devine le type MIME depuis un nom de fichier.

    @param filename - Nom ou clé du fichier.
    @param fallback - Valeur si indéterminable.
    @returns Type MIME.
    """
    guessed, _ = mimetypes.guess_type(filename or "")
    return guessed or fallback


# --------------------------------------------------------------------------- #
# Écriture / lecture
# --------------------------------------------------------------------------- #

def upload_file(local_path: Path | str, key: str, content_type: Optional[str] = None) -> str:
    """
    Envoie un fichier local vers R2 (écrase si la clé existe).

    @param local_path - Chemin du fichier source.
    @param key - Clé cible dans le bucket.
    @param content_type - Type MIME (deviné depuis la clé si absent).
    @returns URL publique de l'objet.
    @throws FileNotFoundError - Fichier source absent.
    """
    path = Path(local_path)
    if not path.is_file():
        raise FileNotFoundError(f"Fichier introuvable pour l'upload R2 : {path}")
    mime = content_type or _guess_content_type(key)
    _get_client().upload_file(
        str(path),
        bucket_name(),
        key,
        ExtraArgs={"ContentType": mime},
    )
    return public_url(key)


def upload_bytes(key: str, data: bytes, content_type: Optional[str] = None) -> str:
    """
    Envoie des octets vers R2 (écrase si la clé existe).

    @param key - Clé cible dans le bucket.
    @param data - Contenu binaire.
    @param content_type - Type MIME (deviné depuis la clé si absent).
    @returns URL publique de l'objet.
    @throws ValueError - Contenu vide.
    """
    if not data:
        raise ValueError("Contenu vide : rien à envoyer sur R2")
    mime = content_type or _guess_content_type(key)
    _get_client().put_object(
        Bucket=bucket_name(),
        Key=key,
        Body=data,
        ContentType=mime,
    )
    return public_url(key)


def download_to_path(key: str, local_path: Path | str) -> Path:
    """
    Télécharge un objet vers un fichier local (nécessaire pour ffmpeg).

    @param key - Clé dans le bucket.
    @param local_path - Chemin de destination (dossiers créés au besoin).
    @returns Le chemin local écrit.
    """
    path = Path(local_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    _get_client().download_file(bucket_name(), key, str(path))
    return path


def exists(key: str) -> bool:
    """
    Indique si un objet est présent dans le bucket.

    @param key - Clé dans le bucket.
    @returns True si l'objet existe.
    """
    try:
        _get_client().head_object(Bucket=bucket_name(), Key=key)
        return True
    except ClientError:
        return False


def delete(key: str) -> None:
    """
    Supprime un objet (best effort, idempotent).

    @param key - Clé dans le bucket.
    """
    _get_client().delete_object(Bucket=bucket_name(), Key=key)


def delete_many(keys: list[str]) -> None:
    """
    Supprime plusieurs objets (par lots de 1000, limite S3).

    @param keys - Clés à supprimer.
    """
    remaining = [k for k in keys if k]
    if not remaining:
        return
    client = _get_client()
    bucket = bucket_name()
    for start in range(0, len(remaining), 1000):
        chunk = remaining[start : start + 1000]
        client.delete_objects(
            Bucket=bucket,
            Delete={"Objects": [{"Key": k} for k in chunk], "Quiet": True},
        )


def list_objects(prefix: str = "", *, bucket: Optional[str] = None) -> list[dict[str, Any]]:
    """
    Liste les objets d'un préfixe (pagination gérée).

    @param prefix - Préfixe de clé (vide = tout le bucket).
    @param bucket - Bucket ciblé (défaut : celui de l'environnement).
    @returns Liste de ``{key, size, last_modified, etag}``.
    """
    client = _get_client()
    target = bucket or bucket_name()
    results: list[dict[str, Any]] = []
    token: Optional[str] = None
    while True:
        kwargs: dict[str, Any] = {"Bucket": target, "Prefix": prefix}
        if token:
            kwargs["ContinuationToken"] = token
        response = client.list_objects_v2(**kwargs)
        for item in response.get("Contents", []):
            # La console Cloudflare matérialise les « dossiers » par des objets
            # vides finissant par « / » : ce ne sont pas des fichiers.
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


def copy_from_bucket(source_bucket: str, key: str) -> None:
    """
    Copie un objet depuis un autre bucket du même compte, **côté serveur**.

    Rien ne transite par l'API : R2 copie en interne (utilisé par la sync prod → dev).

    @param source_bucket - Bucket source.
    @param key - Clé, identique à la source et à la destination.
    """
    _get_client().copy_object(
        Bucket=bucket_name(),
        Key=key,
        CopySource={"Bucket": source_bucket, "Key": key},
    )


# --------------------------------------------------------------------------- #
# Wrappers async (boto3 est bloquant)
# --------------------------------------------------------------------------- #

async def upload_file_async(local_path: Path | str, key: str, content_type: Optional[str] = None) -> str:
    """Version async de :func:`upload_file`."""
    return await asyncio.to_thread(upload_file, local_path, key, content_type)


async def upload_bytes_async(key: str, data: bytes, content_type: Optional[str] = None) -> str:
    """Version async de :func:`upload_bytes`."""
    return await asyncio.to_thread(upload_bytes, key, data, content_type)


async def download_to_path_async(key: str, local_path: Path | str) -> Path:
    """Version async de :func:`download_to_path`."""
    return await asyncio.to_thread(download_to_path, key, local_path)


async def delete_async(key: str) -> None:
    """Version async de :func:`delete`."""
    await asyncio.to_thread(delete, key)
