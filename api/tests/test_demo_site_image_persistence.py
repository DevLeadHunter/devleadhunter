"""A J+30 relance revives a dormant demo whose Storyblok space was deleted at expiry, so its frozen
``content_json`` still points at ``a.storyblok.com`` assets (and older sites at rotting Google links).
``persist_content_images_to_r2`` copies those fragile images onto permanent R2 **in place** — the site
stays byte-identical (same texts, same order, same hero), only the image URLs move to a durable home.
"""

from types import SimpleNamespace

import httpx
import pytest

from services import demo_site_service as dss_mod
from services import prospect_photo_storage_service as pps_mod
from services.demo_site_service import demo_site_service
from services.prospect_photo_storage_service import prospect_photo_storage


def test_is_fragile_image_url_targets_dying_hosts() -> None:
    """Storyblok/Google/Facebook images and any image-extension URL are fragile; R2, stable CDNs,
    data URIs and non-images are not."""
    is_fragile = prospect_photo_storage.is_fragile_image_url

    assert is_fragile("https://a.storyblok.com/f/294694547122029/abc/hero.jpg") is True
    assert is_fragile("https://lh3.googleusercontent.com/gps-cs-s/AAAA") is True  # fragile host, no extension
    assert is_fragile("https://scontent-cdg4-2.xx.fbcdn.net/v/x.jpg?oh=1") is True
    assert is_fragile("https://www.pagesjaunes.fr/media/preset/e0/5d.jpg") is True  # image extension

    assert is_fragile("https://images.unsplash.com/photo-1?ixlib=rb") is False  # stable CDN, no extension
    assert is_fragile("https://maps.google.com/maps/@47.1,0.6,17z") is False  # not an image
    assert is_fragile("data:image/jpeg;base64,AAAABBBB") is False
    assert is_fragile("") is False
    assert is_fragile(None) is False

    base = (pps_mod.settings.r2_public_base_url or "").strip()
    if base:
        assert is_fragile(f"{base}/images/prospects/29/abc.jpg") is False  # already permanent


@pytest.mark.asyncio
async def test_persist_rewrites_only_fragile_images_and_keeps_the_rest(monkeypatch) -> None:
    """Fragile URLs are swapped for R2; texts, theme, order and stable URLs are left untouched."""
    monkeypatch.setattr(dss_mod.r2_storage, "is_configured", lambda: True)

    async def fake_rehost(prospect_id: int, url: str) -> str:
        return f"https://pub-x.r2.dev/images/prospects/{prospect_id}/{len(url)}.jpg"

    monkeypatch.setattr(dss_mod.prospect_photo_storage, "rehost_remote_image", fake_rehost)

    content = {
        "businessName": "Food truck mexicain Tacos Maru",
        "heroImage": "https://a.storyblok.com/f/294694547122029/hero.jpg",
        "aboutImage": "https://a.storyblok.com/f/294694547122029/about.jpg",
        "gallery": [
            "https://a.storyblok.com/f/294694547122029/g1.jpg",
            "https://images.unsplash.com/photo-42?x=1",
        ],
        "images": {"foodCollage": "https://lh3.googleusercontent.com/gps-cs-s/BBBB"},
        "phone": "06 29 34 58 99",
        "theme": {"primary": "#111111", "accent": "#f59e0b"},
    }
    site = SimpleNamespace(prospect_id=29, slug="food-truck-mexicain-tacos-maru", content_json=content)

    moved = await demo_site_service.persist_content_images_to_r2(site)

    assert moved == 4  # hero + about + gallery[0] + foodCollage (unsplash left alone)
    assert site.content_json["heroImage"].startswith("https://pub-x.r2.dev/")
    assert site.content_json["aboutImage"].startswith("https://pub-x.r2.dev/")
    assert site.content_json["gallery"][0].startswith("https://pub-x.r2.dev/")
    assert site.content_json["images"]["foodCollage"].startswith("https://pub-x.r2.dev/")
    # Everything that is not a fragile image is byte-identical.
    assert site.content_json["gallery"][1] == "https://images.unsplash.com/photo-42?x=1"
    assert site.content_json["businessName"] == "Food truck mexicain Tacos Maru"
    assert site.content_json["phone"] == "06 29 34 58 99"
    assert site.content_json["theme"] == {"primary": "#111111", "accent": "#f59e0b"}


@pytest.mark.asyncio
async def test_persist_is_best_effort_when_a_rehost_fails(monkeypatch) -> None:
    """A rehost that returns the original URL (dead link, storage hiccup) leaves the content unchanged."""
    monkeypatch.setattr(dss_mod.r2_storage, "is_configured", lambda: True)

    async def fake_rehost(prospect_id: int, url: str) -> str:
        return url

    monkeypatch.setattr(dss_mod.prospect_photo_storage, "rehost_remote_image", fake_rehost)
    original = "https://a.storyblok.com/f/294694547122029/hero.jpg"
    site = SimpleNamespace(prospect_id=29, slug="x", content_json={"heroImage": original})

    assert await demo_site_service.persist_content_images_to_r2(site) == 0
    assert site.content_json["heroImage"] == original


@pytest.mark.asyncio
async def test_persist_noop_without_prospect_or_r2(monkeypatch) -> None:
    """No prospect (cannot key the object) or no R2 configured → nothing is touched."""
    monkeypatch.setattr(dss_mod.r2_storage, "is_configured", lambda: True)
    orphan = SimpleNamespace(
        prospect_id=None, slug="x", content_json={"heroImage": "https://a.storyblok.com/f/1/h.jpg"}
    )
    assert await demo_site_service.persist_content_images_to_r2(orphan) == 0

    monkeypatch.setattr(dss_mod.r2_storage, "is_configured", lambda: False)
    site = SimpleNamespace(prospect_id=29, slug="x", content_json={"heroImage": "https://a.storyblok.com/f/1/h.jpg"})
    assert await demo_site_service.persist_content_images_to_r2(site) == 0


class _FakeResponse:
    """Minimal stand-in for an ``httpx.Response``."""

    def __init__(self, status_code: int, content: bytes = b"", content_type: str = "image/jpeg") -> None:
        self.status_code = status_code
        self.content = content
        self.headers = {"content-type": content_type}


class _FakeClient:
    """Async-context httpx client serving canned responses (raises for an unknown URL)."""

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


@pytest.mark.asyncio
async def test_rehost_remote_image_downloads_and_uploads(monkeypatch) -> None:
    """A live fragile image is downloaded and re-uploaded to R2, returning its permanent URL."""
    monkeypatch.setattr(pps_mod.r2_storage, "is_configured", lambda: True)
    url = "https://a.storyblok.com/f/294694547122029/hero.jpg"
    monkeypatch.setattr(pps_mod.httpx, "AsyncClient", lambda *a, **k: _FakeClient({url: _FakeResponse(200, b"img")}))
    monkeypatch.setattr(
        pps_mod.r2_storage, "prospect_photo_key", lambda pid, digest, ext: f"images/prospects/{pid}/{digest}{ext}"
    )

    async def fake_upload(key: str, data: bytes, content_type: str) -> str:
        return f"https://pub-x.r2.dev/{key}"

    monkeypatch.setattr(pps_mod.r2_storage, "upload_bytes_async", fake_upload)

    result = await prospect_photo_storage.rehost_remote_image(29, url)

    assert result.startswith("https://pub-x.r2.dev/images/prospects/29/")
    assert result.endswith(".jpg")


@pytest.mark.asyncio
async def test_rehost_remote_image_keeps_original_on_dead_link(monkeypatch) -> None:
    """A dead fragile link cannot be recovered → the original URL is returned unchanged."""
    monkeypatch.setattr(pps_mod.r2_storage, "is_configured", lambda: True)
    url = "https://a.storyblok.com/f/294694547122029/dead.jpg"
    monkeypatch.setattr(pps_mod.httpx, "AsyncClient", lambda *a, **k: _FakeClient({url: _FakeResponse(404)}))

    assert await prospect_photo_storage.rehost_remote_image(29, url) == url


@pytest.mark.asyncio
async def test_rehost_remote_image_leaves_non_fragile_untouched(monkeypatch) -> None:
    """A stable Unsplash URL is never even downloaded."""
    monkeypatch.setattr(pps_mod.r2_storage, "is_configured", lambda: True)

    def _no_network(*_args: object, **_kwargs: object) -> None:
        raise AssertionError("must not download a non-fragile URL")

    monkeypatch.setattr(pps_mod.httpx, "AsyncClient", _no_network)
    url = "https://images.unsplash.com/photo-42?ixlib=rb"

    assert await prospect_photo_storage.rehost_remote_image(29, url) == url
