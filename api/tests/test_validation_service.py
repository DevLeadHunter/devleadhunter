"""Unit tests for ValidationService website checks — pure functions, no I/O."""

from services.validation_service import validation_service


def test_is_valid_website_accepts_real_sites() -> None:
    """A normal business domain is a valid website."""
    assert validation_service.is_valid_website("https://www.plomberie-martin.fr") is True
    assert validation_service.is_valid_website("http://tasty-korea.fr") is True


def test_is_valid_website_rejects_social_pages() -> None:
    """Social pages (a prospect's only web presence) are never a website."""
    assert validation_service.is_valid_website("https://instagram.com/tastykorea.fr") is False
    assert validation_service.is_valid_website("https://www.facebook.com/mybusiness") is False


def test_is_valid_website_rejects_media_assets() -> None:
    """A poster/logo URL scraped from a post (cloudinary .png, fbcdn photo) is not a website."""
    cloudinary = (
        "https://res.cloudinary.com/shotgun/image/upload/c_limit,w_1080/fl_lossy/f_auto/q_auto/"
        "production/artworks/garorock2025-JJ_1920x1080-v7_cee7qj.png"
    )
    assert validation_service.is_asset_url(cloudinary) is True
    assert validation_service.is_valid_website(cloudinary) is False
    assert validation_service.is_valid_website("https://scontent.xx.fbcdn.net/v/t39.30808-6/1_n.jpg") is False


def test_is_valid_website_rejects_booking_platforms() -> None:
    """A booking/directory platform page (Planity, Treatwell, PagesJaunes…) is never the business's own
    site — many barbers/salons only have a Planity page and must stay « no website »."""
    assert validation_service.is_valid_website("https://www.planity.com/lelegance-barber-31000") is False
    assert validation_service.is_valid_website("https://www.treatwell.fr/salon/mon-salon/") is False
    assert validation_service.is_valid_website("https://www.pagesjaunes.fr/pros/12345") is False
    assert validation_service.is_valid_website("https://fresha.com/a/mon-salon") is False


def test_is_platform_url_matches_host_not_lookalikes() -> None:
    """The platform check matches the host or a subdomain, never a lookalike domain or a path."""
    assert validation_service.is_platform_url("https://planity.com/x") is True
    assert validation_service.is_platform_url("https://booking.planity.com/x") is True
    assert validation_service.is_platform_url("https://mon-planity.com") is False  # different domain
    assert validation_service.is_platform_url("https://real-salon.fr/planity.com") is False  # path, not host
    assert validation_service.is_platform_url(None) is False


def test_is_valid_website_rejects_foreign_directories_and_platforms() -> None:
    """A Swiss, Belgian, Luxembourg or Québec listing never counts as the artisan's site: he stays « no website »."""
    for url in (
        "https://www.local.ch/fr/d/lausanne/1004/sanitaire/sanitaire-rochat-abc",
        "https://tel.search.ch/lausanne/rue-de-geneve-12/sanitaire-rochat",
        "https://www.treatwell.be/salon/barber-liege/",
        "https://www.goldenpages.be/fr/p/plomberie-dupont/",
        "https://www.editus.lu/fr/plomberie-schmit",
        "https://www.pagesjaunes.ca/bus/Quebec/Laval/Plomberie-Tremblay/1234567.html",
    ):
        assert validation_service.is_valid_website(url) is False, url


def test_is_valid_website_keeps_a_foreign_artisan_own_site() -> None:
    assert validation_service.is_valid_website("https://www.sanitaire-rochat.ch") is True
    assert validation_service.is_valid_website("https://www.mylocal.ch") is True
    assert validation_service.is_valid_website("https://plomberie-tremblay.qc.ca") is True
