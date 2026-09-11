"""
Round-trip tests for the ``SiteContent`` ⇄ Storyblok bridge.

The Storyblok projection splits the flat ``SiteContent`` into per-section bloks (``section_hero``,
``section_about``…). These tests lock the split (``to_storyblok_site_content``) and the merge back
(``from_storyblok_site_content``) — especially images (asset/multiasset), the string rating and the
palette moving to the page ``theme`` field.
"""

from services.templates import site_content as sc


def _flat_site() -> dict:
    """A minimal flat SiteContent carrying every image-bearing field and a palette."""
    return {
        "businessName": "Barbier d'Antan",
        "logo": "https://img.example/logo.png",
        "heroImage": "https://img.example/hero.jpg",
        "aboutImage": "https://img.example/about.jpg",
        "gallery": [
            {"url": "https://img.example/g1.jpg", "alt": "Devanture"},
            {"url": "https://img.example/g2.jpg", "alt": ""},
        ],
        "beforeAfter": [
            {"before": "https://img.example/b.jpg", "after": "https://img.example/a.jpg", "label": "Salon"}
        ],
        "palette": {"primary": "#121212", "secondary": "#f8f5ef", "accent": "#dec7a6"},
    }


def _page(site: dict) -> dict:
    """Wrap the section body into a page story, with the palette on the page ``theme`` field."""
    palette = site.get("palette") or {}
    return {
        "component": "page",
        "theme": [{"_uid": "theme-1", "component": "theme_palette", **palette}],
        "body": sc.to_storyblok_site_content(site),
    }


def _section(body: list, suffix: str) -> dict:
    """Return the ``section_<suffix>`` blok from a body list."""
    return next(blok for blok in body if blok["component"] == f"section_{suffix}")


def test_body_is_split_into_section_bloks() -> None:
    """``to_storyblok`` returns an ordered list of ``section_*`` bloks, each owning its fields."""
    body = sc.to_storyblok_site_content(_flat_site())

    assert [blok["component"] for blok in body] == [f"section_{suffix}" for suffix, _, _ in sc.SECTION_DEFINITIONS]
    hero = _section(body, "hero")
    assert hero["heroImage"]["fieldtype"] == "asset"
    assert hero["heroImage"]["filename"] == "https://img.example/hero.jpg"
    gallery = _section(body, "gallery")
    assert [asset["filename"] for asset in gallery["gallery"]] == [
        "https://img.example/g1.jpg",
        "https://img.example/g2.jpg",
    ]
    before_after = _section(body, "beforeAfter")
    assert before_after["beforeAfter"][0]["before"]["filename"] == "https://img.example/b.jpg"
    # Every asset key must be present or Storyblok disables the replace/edit dialog.
    contact = _section(body, "contact")
    assert set(contact["logo"]) == {"fieldtype", "filename", "alt", "copyright", "name", "title", "focus", "id"}


def test_used_sections_drop_unrendered_sections() -> None:
    """A template's ``USED_SECTIONS`` keeps only the sections it renders, in order — no dead sections."""
    body = sc.to_storyblok_site_content(_flat_site(), ["hero", "gallery", "contact"])

    assert [blok["component"] for blok in body] == ["section_hero", "section_gallery", "section_contact"]


def test_section_field_overrides_swap_hero_fields() -> None:
    """A per-section override exposes a field the default hides (heroTitle) and drops shared ones."""
    body = sc.to_storyblok_site_content(
        {"heroTitle": "Élagage à Angers", "subtitle": "Taille et abattage", "heroBadge": "IGNORÉ"},
        ["hero"],
        None,
        {"hero": ["heroTitle", "subtitle", "heroImage", "ctaCallLabel", "ctaQuoteLabel"]},
    )
    hero = _section(body, "hero")

    assert hero["heroTitle"] == "Élagage à Angers"
    assert "heroBadge" not in hero
    assert "heroPoints" not in hero


def test_build_content_schemas_honours_field_overrides() -> None:
    """The Storyblok section schema reflects the per-template field override (order = editor pos)."""
    schemas = sc.build_content_schemas(None, {"hero": ["heroTitle", "subtitle"]})
    hero = next(component for component in schemas if component["name"] == "section_hero")

    assert set(hero["schema"]) == {"heroTitle", "subtitle"}
    assert hero["schema"]["heroTitle"]["pos"] == 0


def test_hero_title_round_trips() -> None:
    """The new ``heroTitle`` flows back out of a published Storyblok hero section."""
    flat = sc.from_storyblok_site_content(
        {"component": "page", "body": [{"component": "section_hero", "heroTitle": "Élagueur à Angers"}]}
    )

    assert flat["heroTitle"] == "Élagueur à Angers"


def test_review_rating_is_pushed_as_string() -> None:
    """Storyblok ``number`` fields validate against strings — an int rating fails save/publish."""
    body = sc.to_storyblok_site_content(
        {"reviews": [{"author": "Jean", "rating": 5, "text": "Top"}, {"author": "Marie", "text": "Bien"}]}
    )
    reviews = _section(body, "reviews")["reviews"]

    assert reviews[0]["rating"] == "5"
    assert reviews[1]["rating"] == ""


def test_round_trip_preserves_content() -> None:
    """Splitting into sections then merging back yields the original flat values."""
    flat = sc.from_storyblok_site_content(_page(_flat_site()))

    assert flat["logo"] == "https://img.example/logo.png"
    assert flat["heroImage"] == "https://img.example/hero.jpg"
    assert flat["aboutImage"] == "https://img.example/about.jpg"
    assert [image["url"] for image in flat["gallery"]] == [
        "https://img.example/g1.jpg",
        "https://img.example/g2.jpg",
    ]
    assert flat["gallery"][0]["alt"] == "Devanture"
    assert flat["beforeAfter"][0] == {
        "before": "https://img.example/b.jpg",
        "after": "https://img.example/a.jpg",
        "label": "Salon",
    }
    # Palette is read back from the page ``theme`` field, not a section.
    assert flat["palette"] == {"primary": "#121212", "secondary": "#f8f5ef", "accent": "#dec7a6"}


def test_round_trip_rating_back_to_int() -> None:
    """A string rating survives the round-trip back to an int."""
    flat = sc.from_storyblok_site_content(_page({"reviews": [{"author": "Jean", "rating": 5, "text": "Top"}]}))

    assert flat["reviews"][0]["rating"] == 5


def test_flatten_tolerates_legacy_single_blok() -> None:
    """A pre-section story (one bare ``site_content`` blok, URL strings) still flattens."""
    legacy = {
        "component": "site_content",
        "logo": "https://img.example/legacy-logo.png",
        "heroImage": "https://img.example/legacy-hero.jpg",
    }
    flat = sc.from_storyblok_site_content(legacy)

    assert flat["logo"] == "https://img.example/legacy-logo.png"
    assert flat["heroImage"] == "https://img.example/legacy-hero.jpg"


def test_empty_content_flattens_to_empty() -> None:
    """A site with no images flattens to empty strings and an empty gallery."""
    flat = sc.from_storyblok_site_content(_page({"businessName": "Sans photo"}))

    assert flat["logo"] == ""
    assert flat["heroImage"] == ""
    assert flat["gallery"] == []
