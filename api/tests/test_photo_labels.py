"""
Photo labels: normalisation of the vision output (kind synonyms, prompt version), ranking of
card-worthy photos, batch parsing, the time budget of a labelling run, and the two label families
(food trades, every other trade read as a craft).
"""

import asyncio

import pytest

import services.photo_labeling_service as labeling_module
from services.photo_labeling_service import PhotoLabelingService, photo_family_for_category
from services.photo_labels import (
    CRAFT_KIND_PREMISES,
    CRAFT_KIND_WORK,
    CRAFT_PHOTO_LABEL_VERSION,
    PHOTO_FAMILY_CRAFT,
    PHOTO_FAMILY_FOOD,
    PHOTO_KIND_LOGO_OR_FLYER,
    PHOTO_LABEL_VERSION,
    canonical_kind,
    craft_labels_for_urls,
    is_card_worthy,
    is_current_label,
    is_unfit_for_card,
    labels_for_urls,
    normalize_label,
    rank_card_photos,
    rank_craft_photos,
)


def test_normalize_label_coerces_shape_and_caps_values() -> None:
    label = normalize_label(
        {"kind": "Dish", "description": "  Burger  ", "dishes": ["Tacos", "Tacos", 42], "appeal": "9"}
    )
    assert label == {
        "kind": "dish",
        "description": "Burger",
        "dishes": ["Tacos", "42"],
        "appeal": 5,
        "version": PHOTO_LABEL_VERSION,
    }


def test_normalize_label_rejects_empty_kind_and_non_dict() -> None:
    assert normalize_label({"kind": ""}) is None
    assert normalize_label("dish") is None
    assert normalize_label(None) is None


def test_canonical_kind_maps_synonyms_and_keeps_unknown_wordings_as_other() -> None:
    # The model sometimes answers in French or with a close wording: never drop the photo for that.
    assert canonical_kind("plat") == "dish"
    assert canonical_kind("Menu board") == "menu_board"
    assert canonical_kind("menu-board") == "menu_board"
    assert canonical_kind("food truck exterior") == "truck"
    assert canonical_kind("spaceship") == "other"
    assert canonical_kind("") is None


def test_labels_for_urls_skips_labels_of_an_older_prompt_version() -> None:
    stored = {
        "a": {"kind": "dish", "appeal": 4, "version": PHOTO_LABEL_VERSION},
        "b": {"kind": "dish", "appeal": 4, "version": PHOTO_LABEL_VERSION - 1},
        "c": {"kind": "truck"},  # pre-versioning entry: treated as current (default version)
    }
    assert set(labels_for_urls(stored, ["a", "b", "c"])) == {"a", "c"}
    assert is_current_label(stored["a"])
    assert not is_current_label(stored["b"])
    assert labels_for_urls(None, ["a"]) == {}


def test_card_worthiness_predicates() -> None:
    assert is_card_worthy({"kind": "dish"})
    assert is_card_worthy({"kind": "drink"})
    assert not is_card_worthy({"kind": "truck"})
    assert not is_card_worthy(None)
    assert is_unfit_for_card({"kind": "truck"})
    assert is_unfit_for_card({"kind": "menu_board"})
    assert not is_unfit_for_card(None)  # unlabelled = unknown, still a last-resort fallback


def test_rank_card_photos_dishes_by_appeal_then_unknown_never_unfit() -> None:
    labels = {
        "truck": {"kind": "truck", "appeal": 5},
        "menu": {"kind": "menu_board", "appeal": 5},
        "burger": {"kind": "dish", "appeal": 3},
        "wrap": {"kind": "dish", "appeal": 5},
        "soda": {"kind": "drink", "appeal": 4},
    }
    ranked = rank_card_photos(["truck", "burger", "unknown", "menu", "wrap", "soda", "burger"], labels)
    assert ranked == ["wrap", "soda", "burger", "unknown"]


def test_rank_card_photos_honours_exclusions() -> None:
    labels = {"a": {"kind": "dish", "appeal": 5}, "b": {"kind": "dish", "appeal": 4}}
    assert rank_card_photos(["a", "b"], labels, exclude={"a"}) == ["b"]


def test_parse_batch_answer_maps_by_index_and_drops_out_of_range() -> None:
    batch = ["u1", "u2", "u3"]
    answer = {
        "photos": [
            {"index": 2, "kind": "dish", "description": "Burger", "dishes": ["Burger"], "appeal": 4},
            {"index": 1, "kind": "camion", "description": "Camion", "appeal": 2},
            {"index": 9, "kind": "dish"},
            {"kind": ""},
        ]
    }
    labels = PhotoLabelingService.parse_batch_answer(answer, batch)
    assert labels["u2"]["kind"] == "dish"
    assert labels["u2"]["version"] == PHOTO_LABEL_VERSION
    assert labels["u1"]["kind"] == "truck"
    assert "u3" not in labels


def test_parse_batch_answer_falls_back_to_position_without_index() -> None:
    labels = PhotoLabelingService.parse_batch_answer({"photos": [{"kind": "dish"}, {"kind": "event"}]}, ["a", "b"])
    assert [labels["a"]["kind"], labels["b"]["kind"]] == ["dish", "event"]
    assert PhotoLabelingService.parse_batch_answer(None, ["a"]) == {}
    assert PhotoLabelingService.parse_batch_answer({"photos": "x"}, ["a"]) == {}


def test_label_photos_runs_batches_sequentially_saves_each_and_stops_at_the_budget(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    urls = [f"https://cdn/{i}.jpg" for i in range(3)]  # one photo per call
    calls: list[list[str]] = []
    clock = {"now": 0.0}

    async def fake_request(self: PhotoLabelingService, batch: list[str], family: str, trade: str) -> dict:
        calls.append(list(batch))
        clock["now"] += 30.0  # each batch "takes" 30 s
        return {
            url: {"kind": "dish", "description": "", "dishes": [], "appeal": 3, "version": PHOTO_LABEL_VERSION}
            for url in batch
        }

    monkeypatch.setattr(type(labeling_module.llm_service), "is_configured", property(lambda self: True))
    monkeypatch.setattr(PhotoLabelingService, "_request_labels", fake_request)
    monkeypatch.setattr(labeling_module.time, "monotonic", lambda: clock["now"])
    saved: list[int] = []

    labels = asyncio.run(
        PhotoLabelingService().label_photos(
            urls, time_budget_seconds=45.0, on_batch_labelled=lambda batch: saved.append(len(batch))
        )
    )
    # Photo 1 at t=0, photo 2 at t=30 (within budget); photo 3 would start at t=60, so it waits for the next call.
    assert calls == [[urls[0]], [urls[1]]]
    assert saved == [1, 1]
    assert len(labels) == 2


def test_label_batch_falls_back_to_one_call_per_photo_when_the_batch_fails(monkeypatch: pytest.MonkeyPatch) -> None:
    answers: list[list[str]] = []

    async def fake_request(self: PhotoLabelingService, batch: list[str], family: str, trade: str) -> dict:
        answers.append(list(batch))
        if len(batch) > 1 or batch == ["bad"]:
            return {}
        return {
            batch[0]: {"kind": "dish", "description": "", "dishes": [], "appeal": 3, "version": PHOTO_LABEL_VERSION}
        }

    monkeypatch.setattr(PhotoLabelingService, "_request_labels", fake_request)
    labels = asyncio.run(PhotoLabelingService()._label_batch(["ok1", "bad", "ok2"], "food", ""))
    assert answers == [["ok1", "bad", "ok2"], ["ok1"], ["bad"], ["ok2"]]
    assert set(labels) == {"ok1", "ok2"}


def test_photo_family_for_category_reads_food_trades_and_crafts() -> None:
    assert photo_family_for_category("Food truck") == PHOTO_FAMILY_FOOD
    assert photo_family_for_category("Restaurant de tacos") == PHOTO_FAMILY_FOOD
    assert photo_family_for_category("Traiteur") == PHOTO_FAMILY_FOOD
    assert photo_family_for_category("Plombier") == PHOTO_FAMILY_CRAFT
    assert photo_family_for_category(None) == PHOTO_FAMILY_CRAFT


def test_a_craft_answer_is_read_as_craft_labels_even_as_a_bare_list() -> None:
    answer = [
        {"index": 1, "kind": "chantier", "description": "Haie taillée", "services": ["taille de haies"], "appeal": 4},
        {"index": 2, "kind": "flyer", "description": "Carte de vœux", "texte": True, "appeal": 5},
    ]

    labels = PhotoLabelingService.parse_batch_answer(answer, ["u1", "u2"], family=PHOTO_FAMILY_CRAFT)

    assert labels["u1"] == {
        "family": PHOTO_FAMILY_CRAFT,
        "kind": CRAFT_KIND_WORK,
        "description": "Haie taillée",
        "services": ["taille de haies"],
        "text": False,
        "appeal": 4,
        "version": CRAFT_PHOTO_LABEL_VERSION,
    }
    assert labels["u2"]["kind"] == PHOTO_KIND_LOGO_OR_FLYER
    assert labels["u2"]["text"] is True


def test_craft_and_food_labels_never_read_each_other() -> None:
    stored = {
        "craft": {"family": PHOTO_FAMILY_CRAFT, "kind": "work", "appeal": 4, "version": CRAFT_PHOTO_LABEL_VERSION},
        "food": {"kind": "dish", "appeal": 4, "version": PHOTO_LABEL_VERSION},
    }

    assert set(craft_labels_for_urls(stored, ["craft", "food"])) == {"craft"}
    assert set(labels_for_urls(stored, ["craft", "food"])) == {"food"}


def test_craft_photos_rank_showable_ones_by_preferred_kind_then_appeal_and_drop_flyers() -> None:
    labels = {
        "flyer": {"kind": PHOTO_KIND_LOGO_OR_FLYER, "appeal": 5},
        "work": {"kind": CRAFT_KIND_WORK, "appeal": 3},
        "premises": {"kind": CRAFT_KIND_PREMISES, "appeal": 2},
        "work_best": {"kind": CRAFT_KIND_WORK, "appeal": 5},
        "customer": {"kind": "customer", "appeal": 5},
        "flowers": {"kind": "other", "appeal": 5},
        "blurry": {"kind": "other", "appeal": 2},
    }
    urls = ["flyer", "work", "premises", "work_best", "customer", "flowers", "blurry", "unlabelled"]

    assert rank_craft_photos(urls, labels, preferred_kinds=(CRAFT_KIND_PREMISES, CRAFT_KIND_WORK)) == [
        "premises",
        "work_best",
        "work",
        "flowers",
        "unlabelled",
    ]
    assert rank_craft_photos(urls, labels, exclude={"work_best"}) == ["flowers", "work", "premises", "unlabelled"]
