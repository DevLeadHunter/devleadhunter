"""Manual uploads to R2 from the admin storage page.

A hand-picked file (browser upload) or a remote URL (e.g. an expiring Facebook ``fbcdn`` image fetched
server-side) is validated against an image/PDF allowlist, size-capped, and stored under the permanent
``uploads/manual/`` prefix — the caller then pastes the returned R2 URL into a prospect's info.
"""

import httpx
import pytest
from fastapi import HTTPException

from services.manual_upload_service import ManualUploadService, manual_upload_service
from services.r2_storage_service import r2_storage

_PNG_BYTES = b"\x89PNG\r\n\x1a\n" + b"rest"
_JPEG_BYTES = b"\xff\xd8\xff\xe0" + b"rest"


class _FakeResponse:
    """Minimal stand-in for an ``httpx.Response``."""

    def __init__(self, status_code: int, content: bytes = b"", content_type: str = "image/jpeg") -> None:
        self.status_code = status_code
        self.content = content
        self.headers = {"content-type": content_type}


class _FakeClient:
    """Async-context httpx client serving one canned response (or raising for an unknown URL)."""

    def __init__(self, responses: dict[str, _FakeResponse]) -> None:
        self._responses = responses

    async def __aenter__(self) -> "_FakeClient":
        return self

    async def __aexit__(self, *_exc: object) -> bool:
        return False

    async def get(self, url: str) -> _FakeResponse:
        response = self._responses.get(url)
        if response is None:
            raise httpx.ConnectError("no route")
        return response


def test_sniff_detects_common_types() -> None:
    assert ManualUploadService._sniff(_JPEG_BYTES) == "image/jpeg"
    assert ManualUploadService._sniff(_PNG_BYTES) == "image/png"
    assert ManualUploadService._sniff(b"GIF89a....") == "image/gif"
    assert ManualUploadService._sniff(b"RIFF\x00\x00\x00\x00WEBPVP8 ") == "image/webp"
    assert ManualUploadService._sniff(b"%PDF-1.7 rest") == "application/pdf"
    assert ManualUploadService._sniff(b"not-an-image") is None


def test_resolve_type_prefers_header() -> None:
    # A valid header wins over a mismatching file extension.
    content_type, extension = manual_upload_service._resolve_type("image/png", "photo.jpg", _JPEG_BYTES)
    assert (content_type, extension) == ("image/png", ".png")


def test_resolve_type_falls_back_to_filename() -> None:
    # A generic/unsupported header defers to the file name's extension.
    content_type, extension = manual_upload_service._resolve_type("application/octet-stream", "photo.png", b"x")
    assert (content_type, extension) == ("image/png", ".png")


def test_resolve_type_falls_back_to_sniff() -> None:
    content_type, extension = manual_upload_service._resolve_type(None, None, _PNG_BYTES)
    assert (content_type, extension) == ("image/png", ".png")


def test_resolve_type_rejects_unsupported() -> None:
    with pytest.raises(HTTPException) as exc:
        manual_upload_service._resolve_type("text/plain", "note.txt", b"plain text")
    assert exc.value.status_code == 400


@pytest.mark.asyncio
async def test_store_bytes_rejects_empty(monkeypatch) -> None:
    monkeypatch.setattr(r2_storage, "is_configured", lambda: True)
    with pytest.raises(HTTPException) as exc:
        await manual_upload_service.store_bytes(data=b"", content_type="image/png")
    assert exc.value.status_code == 400


@pytest.mark.asyncio
async def test_store_bytes_rejects_oversized(monkeypatch) -> None:
    monkeypatch.setattr(r2_storage, "is_configured", lambda: True)
    monkeypatch.setattr("services.manual_upload_service._MAX_UPLOAD_BYTES", 4)
    with pytest.raises(HTTPException) as exc:
        await manual_upload_service.store_bytes(data=_PNG_BYTES, content_type="image/png")
    assert exc.value.status_code == 413


@pytest.mark.asyncio
async def test_store_bytes_requires_r2(monkeypatch) -> None:
    monkeypatch.setattr(r2_storage, "is_configured", lambda: False)
    with pytest.raises(HTTPException) as exc:
        await manual_upload_service.store_bytes(data=_PNG_BYTES, content_type="image/png")
    assert exc.value.status_code == 503


@pytest.mark.asyncio
async def test_store_bytes_uploads_under_manual_prefix(monkeypatch) -> None:
    uploaded: dict[str, object] = {}
    monkeypatch.setattr(r2_storage, "is_configured", lambda: True)
    monkeypatch.setattr(r2_storage, "manual_upload_key", lambda ext: f"uploads/manual/2026/09/deadbeef{ext}")

    async def fake_upload(key: str, data: bytes, content_type: str) -> str:
        uploaded.update({"key": key, "data": data, "content_type": content_type})
        return f"https://cdn.example/{key}"

    monkeypatch.setattr(r2_storage, "upload_bytes_async", fake_upload)

    stored = await manual_upload_service.store_bytes(data=_PNG_BYTES, content_type="image/png", filename="logo.png")

    assert stored.key == "uploads/manual/2026/09/deadbeef.png"
    assert stored.url == "https://cdn.example/uploads/manual/2026/09/deadbeef.png"
    assert stored.size == len(_PNG_BYTES)
    assert stored.content_type == "image/png"
    assert uploaded["data"] == _PNG_BYTES


@pytest.mark.asyncio
async def test_import_from_url_rejects_bad_scheme(monkeypatch) -> None:
    monkeypatch.setattr(r2_storage, "is_configured", lambda: True)
    with pytest.raises(HTTPException) as exc:
        await manual_upload_service.import_from_url("ftp://example.com/x.jpg")
    assert exc.value.status_code == 400


@pytest.mark.asyncio
async def test_import_from_url_maps_source_error_to_502(monkeypatch) -> None:
    dead = "https://scontent.xx.fbcdn.net/v/dead.jpg?oh=1"
    monkeypatch.setattr(r2_storage, "is_configured", lambda: True)
    monkeypatch.setattr(
        "services.manual_upload_service.httpx.AsyncClient",
        lambda *args, **kwargs: _FakeClient({dead: _FakeResponse(403)}),
    )
    with pytest.raises(HTTPException) as exc:
        await manual_upload_service.import_from_url(dead)
    assert exc.value.status_code == 502


@pytest.mark.asyncio
async def test_import_from_url_downloads_and_stores(monkeypatch) -> None:
    fbcdn = "https://scontent-cdg4-2.xx.fbcdn.net/v/t39.30808-6/484654844_n.jpg?stp=dst-jpg&oh=1&oe=2"
    monkeypatch.setattr(r2_storage, "is_configured", lambda: True)
    monkeypatch.setattr(r2_storage, "manual_upload_key", lambda ext: f"uploads/manual/2026/09/abc{ext}")
    monkeypatch.setattr(
        "services.manual_upload_service.httpx.AsyncClient",
        lambda *args, **kwargs: _FakeClient({fbcdn: _FakeResponse(200, b"real-photo-bytes", "image/jpeg")}),
    )

    async def fake_upload(key: str, data: bytes, content_type: str) -> str:
        return f"https://cdn/{key}"

    monkeypatch.setattr(r2_storage, "upload_bytes_async", fake_upload)

    stored = await manual_upload_service.import_from_url(fbcdn)

    assert stored.key == "uploads/manual/2026/09/abc.jpg"
    assert stored.url == "https://cdn/uploads/manual/2026/09/abc.jpg"
    assert stored.content_type == "image/jpeg"
    assert stored.size == len(b"real-photo-bytes")
