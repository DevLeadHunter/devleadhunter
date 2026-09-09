"""
Editable section cards (food « Nos spécialités »): AI output validation, the curation override
surviving regenerations, and label-aware photo seeding (never the truck on a dish card).
"""

import asyncio
from types import SimpleNamespace

import pytest

import services.demo_site_service as demo_module
import services.service_card_suggestion_service as suggestion_module
from services.demo_site_service import DemoSiteService
from services.service_card_suggestion_service import (
    ServiceCardsConfig,
    ServiceCardSuggestionService,
    eligible_photo_indexes,
    menu_dishes,
    review_excerpts,
)
from services.templates import registry
from services.templates.site_content import apply_section_overrides, clean_service_cards, fill_missing_card_images

POOL = ["https://cdn/truck.jpg", "https://cdn/burger.jpg", "https://cdn/menu.jpg", "https://cdn/wrap.jpg"]
LABELS = {
    "https://cdn/truck.jpg": {"kind": "truck", "description": "Le camion", "dishes": [], "appeal": 4},
    "https://cdn/burger.jpg": {"kind": "dish", "description": "Burger double", "dishes": ["Burger"], "appeal": 5},
    "https://cdn/menu.jpg": {
        "kind": "menu_board",
        "description": "Ardoise",
        "dishes": ["Tacos 8€", "Wrap 7€"],
        "appeal": 2,
    },
    "https://cdn/wrap.jpg": {"kind": "dish", "description": "Wrap poulet", "dishes": ["Wrap"], "appeal": 3},
}
CONFIG = ServiceCardsConfig(enabled=True, heading="Nos spécialités", subject="plats", min_cards=4, max_cards=6)


def _palette() -> dict[str, str]:
    return {"primary": "#000", "secondary": "#111", "accent": "#222"}


# ── Suggestion validation ─────────────────────────────────────────────────────


def test_eligible_indexes_are_dishes_best_first() -> None:
    assert eligible_photo_indexes(POOL, LABELS) == [2, 4]


def test_menu_dishes_read_from_menu_boards_only() -> None:
    assert menu_dishes(LABELS) == ["Tacos 8€", "Wrap 7€"]


def test_review_excerpts_keep_longest_texts() -> None:
    reviews = [
        {"text": "Super burger, énorme et bon"},
        {"text": "ok"},
        {"text": "Le wrap poulet est une tuerie absolue"},
    ]
    excerpts = review_excerpts({"reviews": reviews})
    assert excerpts[0].startswith("Le wrap")
    assert "ok" not in excerpts


def test_clean_cards_maps_photo_index_and_rejects_unfit_or_out_of_range() -> None:
    raw = [
        {"photo": 2, "title": "Le Burger", "description": "Double steak", "reason": "Star des avis"},
        {"photo": 1, "title": "Le Camion", "description": "…"},  # truck → photo dropped, text kept
        {"photo": 42, "title": "Hors pool", "description": "…"},
        {"photo": 2, "title": "Doublon photo", "description": "…"},  # burger already used
        {"title": "le burger"},  # duplicate title (case-insensitive)
        "garbage",
    ]
    cards = ServiceCardSuggestionService.clean_cards(raw, POOL, LABELS, CONFIG)
    assert [card["title"] for card in cards] == ["Le Burger", "Le Camion", "Hors pool", "Doublon photo"]
    assert cards[0]["image"] == "https://cdn/burger.jpg"
    assert cards[0]["photo_index"] == 2
    # The spare dish photo (wrap) goes to the first card left without one; the rest stay empty.
    assert cards[1]["image"] == "https://cdn/wrap.jpg"
    assert cards[2]["image"] == ""
    assert cards[3]["image"] == ""


def test_clean_cards_caps_count_and_lengths() -> None:
    raw = [{"title": f"Plat {i}", "description": "x" * 500, "reason": "y" * 500} for i in range(10)]
    cards = ServiceCardSuggestionService.clean_cards(raw, POOL, LABELS, CONFIG)
    assert len(cards) == 6
    assert len(cards[0]["description"]) == 160
    assert len(cards[0]["reason"]) == 200


def test_suggest_end_to_end_with_mocked_llm(monkeypatch: pytest.MonkeyPatch) -> None:
    async def fake_complete_json(messages: list[dict], **kwargs: object) -> dict:
        prompt = messages[1]["content"]
        assert "Photos ÉLIGIBLES pour une carte" in prompt
        assert "#2, #4" in prompt
        assert "Tacos 8€" in prompt
        return {
            "cards": [
                {"photo": 2, "title": "Le Burger", "description": "Double steak, cheddar.", "reason": "Photo 5/5"},
                {"photo": 4, "title": "Wrap poulet", "description": "Poulet pané, crudités.", "reason": "Menu"},
                {"photo": None, "title": "Tacos", "description": "Lu sur l'ardoise.", "reason": "Ardoise"},
                {"photo": None, "title": "Formule du midi", "description": "Plat + boisson.", "reason": "Avis"},
            ]
        }

    monkeypatch.setattr(suggestion_module.llm_service, "complete_json", fake_complete_json)
    monkeypatch.setattr(type(suggestion_module.llm_service), "is_configured", property(lambda self: True))
    service = ServiceCardSuggestionService()
    result = asyncio.run(
        service.suggest(
            business_name="Sapori",
            city="Rennes",
            category="Food truck",
            enrichment={"reviews": [{"text": "Le burger est énorme, on adore"}], "services": []},
            pool=POOL,
            labels=LABELS,
            config=CONFIG,
        )
    )
    assert [card["title"] for card in result.cards] == ["Le Burger", "Wrap poulet", "Tacos", "Formule du midi"]
    assert result.cards[0]["image"] == "https://cdn/burger.jpg"
    assert result.cards[2]["image"] == ""
    assert result.analysis["dish_photos"] == 2
    assert result.analysis["menu_boards"] == 1
    assert result.analysis["menu_dishes"] == 2
    assert result.analysis["reviews_used"] == 1


def test_suggest_without_llm_returns_no_cards(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(type(suggestion_module.llm_service), "is_configured", property(lambda self: False))
    result = asyncio.run(
        ServiceCardSuggestionService().suggest(
            business_name="X", city=None, category=None, enrichment=None, pool=POOL, labels=LABELS, config=CONFIG
        )
    )
    assert result.cards == []
    assert result.analysis["photos_total"] == 4


# ── Curated cards (override) ──────────────────────────────────────────────────


def test_clean_service_cards_validates_shape_and_pool() -> None:
    cards = clean_service_cards(
        [
            {"title": "  Le  Burger ", "description": "Double", "image": "https://cdn/burger.jpg"},
            {"title": "", "image": "https://cdn/wrap.jpg"},  # no title → dropped
            {"title": "Ailleurs", "image": "https://evil/x.jpg"},  # image outside the pool → cleared
            "nope",
        ],
        allowed_images=POOL,
    )
    assert cards == [
        {"title": "Le Burger", "description": "Double", "image": "https://cdn/burger.jpg"},
        {"title": "Ailleurs", "description": "", "image": ""},
    ]


def test_apply_section_overrides_replaces_services_and_fills_missing_photos() -> None:
    site = {
        "services": [{"title": "Plat signature", "description": "…", "image": "https://cdn/truck.jpg"}],
        "gallery": [{"url": url, "alt": ""} for url in POOL],
        "heroImage": "",
        "aboutImage": "",
    }
    overrides = {
        "services": [
            {"title": "Le Burger", "description": "Double", "image": "https://cdn/burger.jpg"},
            {"title": "Tacos", "description": "Lu sur l'ardoise", "image": ""},
            {"title": "Formule", "description": "", "image": ""},
        ],
        "services_source": "ai",
    }
    apply_section_overrides(site, overrides, {"photo_labels": LABELS})
    images = [card["image"] for card in site["services"]]
    # The wrap (only unused dish) fills the first empty card; the truck and the menu board never do.
    assert images == ["https://cdn/burger.jpg", "https://cdn/wrap.jpg", ""]


def test_apply_section_overrides_ignores_empty_or_invalid_overrides() -> None:
    site = {"services": [{"title": "Généré", "description": "", "image": ""}], "gallery": []}
    apply_section_overrides(site, None)
    apply_section_overrides(site, {"services": []})
    apply_section_overrides(site, {"services": [{"title": ""}]})
    assert site["services"][0]["title"] == "Généré"


def test_fill_missing_card_images_without_labels_keeps_gallery_order() -> None:
    site = {
        "services": [{"title": "A"}, {"title": "B"}, {"title": "C"}],
        "gallery": [{"url": "g1"}, {"url": "g2"}],
        "heroImage": "hero",
        "aboutImage": "about",
    }
    fill_missing_card_images(site, {})
    # Legacy behaviour: gallery by position, hero/about untouched, the third card stays empty.
    assert [card.get("image", "") for card in site["services"]] == ["g1", "g2", ""]


# ── Food generation: label-aware seeding ──────────────────────────────────────


def _food_site(enrichment: dict) -> dict:
    return registry.build_site_content(
        template_id="food",
        business_name="Sapori",
        phone="0",
        email="x@y.fr",
        city="Rennes",
        area="Rennes",
        subtitle="",
        palette=_palette(),
        enrichment=enrichment,
    )


def test_food_menu_cards_take_dish_photos_never_the_truck() -> None:
    photos = ["https://cdn/hero.jpg", "https://cdn/about.jpg", *POOL]
    labels = {**LABELS, "https://cdn/hero.jpg": {"kind": "dish", "description": "Pizza", "dishes": [], "appeal": 4}}
    site = _food_site({"photos": photos, "photo_labels": labels})
    images = [card.get("image", "") for card in site["services"]]
    assert "https://cdn/truck.jpg" not in images
    assert "https://cdn/menu.jpg" not in images
    # Best dish first (burger 5), then the hero pizza (4), then the wrap (3), then the unlabelled about photo.
    assert images == ["https://cdn/burger.jpg", "https://cdn/hero.jpg", "https://cdn/wrap.jpg", "https://cdn/about.jpg"]


def test_food_menu_cards_without_labels_keep_legacy_gallery_order() -> None:
    photos = ["https://cdn/hero.jpg", "https://cdn/about.jpg", *POOL]
    site = _food_site({"photos": photos})
    images = [card.get("image", "") for card in site["services"]]
    assert images == POOL


# ── Demo site service: override folded into every rebuild ─────────────────────


class _FakeDB:
    def __init__(self) -> None:
        self.commits = 0

    def commit(self) -> None:
        self.commits += 1

    def refresh(self, row: object) -> None:
        return None


def _site(**overrides: object) -> SimpleNamespace:
    base = {
        "id": 1,
        "user_id": 1,
        "prospect_id": 7,
        "business_name": "Sapori",
        "slug": "sapori",
        "template_id": "food",
        "phone": None,
        "email": None,
        "city": "Rennes",
        "description": None,
        "content_json": None,
        "image_order": None,
        "image_pool_snapshot": None,
        "section_overrides": None,
        "use_brand_color": True,
    }
    base.update(overrides)
    return SimpleNamespace(**base)


def test_rebuild_applies_the_curated_cards(monkeypatch: pytest.MonkeyPatch) -> None:
    enrichment = {"photos": ["https://cdn/hero.jpg", "https://cdn/about.jpg", *POOL], "photo_labels": LABELS}
    monkeypatch.setattr(DemoSiteService, "_enrichment_dict_for_site", lambda self, db, site: enrichment)
    site = _site(
        section_overrides={
            "services": [{"title": "Le Burger", "description": "Double", "image": "https://cdn/burger.jpg"}],
            "services_source": "manual",
        }
    )
    content = DemoSiteService()._build_content_for_site(_FakeDB(), site)
    assert [card["title"] for card in content["services"]] == ["Le Burger"]
    assert content["services"][0]["image"] == "https://cdn/burger.jpg"


def test_update_saves_and_clears_the_curation(monkeypatch: pytest.MonkeyPatch) -> None:
    enrichment = {"photos": ["https://cdn/hero.jpg", "https://cdn/about.jpg", *POOL], "photo_labels": LABELS}
    monkeypatch.setattr(DemoSiteService, "_enrichment_dict_for_site", lambda self, db, site: enrichment)

    async def fake_regenerate(self: DemoSiteService, db: object, demo_site: object) -> object:
        return demo_site

    monkeypatch.setattr(DemoSiteService, "regenerate_demo_site", fake_regenerate)
    service = DemoSiteService()
    site = _site()
    asyncio.run(
        service.update_demo_site(
            _FakeDB(),
            site,
            services=[
                {"title": "Le Burger", "description": "Double", "image": "https://cdn/burger.jpg"},
                {"title": "Ailleurs", "description": "", "image": "https://evil/x.jpg"},
            ],
            services_source="ai",
        )
    )
    assert site.section_overrides["services_source"] == "ai"
    assert site.section_overrides["services"][1]["image"] == ""
    asyncio.run(service.update_demo_site(_FakeDB(), site, services=[]))
    assert site.section_overrides is None


def test_update_rejects_cards_without_any_title(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(DemoSiteService, "_enrichment_dict_for_site", lambda self, db, site: {"photos": POOL})
    with pytest.raises(ValueError):
        asyncio.run(DemoSiteService().update_demo_site(_FakeDB(), _site(), services=[{"title": "  "}]))


def test_get_service_cards_reports_state_and_pool(monkeypatch: pytest.MonkeyPatch) -> None:
    enrichment = {"photos": POOL, "photo_labels": {POOL[1]: LABELS[POOL[1]]}}
    monkeypatch.setattr(DemoSiteService, "_enrichment_dict_for_site", lambda self, db, site: enrichment)
    monkeypatch.setattr(type(demo_module.service_card_suggestion_service), "is_available", property(lambda self: False))
    site = _site(
        content_json={"services": [{"title": "Généré", "description": "", "image": ""}]},
        section_overrides={
            "services": [{"title": "Le Burger", "description": "", "image": ""}],
            "services_source": "ai_auto",
        },
        image_order=[POOL[3], POOL[1]],
        image_pool_snapshot=POOL,
    )
    state = DemoSiteService().get_service_cards(_FakeDB(), site)
    assert state["override_active"] is True
    assert state["override_source"] == "ai_auto"
    assert state["ai_available"] is False
    assert state["labels_pending"] == 3
    assert state["config"]["enabled"] is True
    assert state["config"]["heading"] == "Nos spécialités"
    # Placed photos first (the curated order), then the unused ones; labels attached where known.
    assert [entry["url"] for entry in state["pool"]] == [POOL[3], POOL[1], POOL[0], POOL[2]]
    assert state["pool"][1]["card_worthy"] is True
    assert state["pool"][0]["kind"] == "unknown"


def test_service_cards_disabled_for_fixed_grid_templates() -> None:
    state_config = DemoSiteService._service_cards_config(_site(template_id="barber"))
    assert state_config.enabled is False


def test_auto_cards_kept_only_when_the_minimum_is_reached(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(type(demo_module.service_card_suggestion_service), "is_available", property(lambda self: True))
    few = [{"title": "A", "description": "", "image": ""}] * 2
    enough = [{"title": f"Plat {i}", "description": "", "image": ""} for i in range(4)]
    outcomes = iter([{"cards": few}, {"cards": enough}])

    async def fake_suggest(self: DemoSiteService, db: object, demo_site: object) -> dict:
        return next(outcomes)

    monkeypatch.setattr(DemoSiteService, "suggest_service_cards", fake_suggest)
    service = DemoSiteService()
    site = _site()
    asyncio.run(service._seed_auto_service_cards(_FakeDB(), site, {"photos": POOL}))
    assert site.section_overrides is None
    asyncio.run(service._seed_auto_service_cards(_FakeDB(), site, {"photos": POOL}))
    assert site.section_overrides["services_source"] == "ai_auto"
    assert len(site.section_overrides["services"]) == 4
