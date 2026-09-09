"""
Photo labels: normalisation of the vision output, ranking of card-worthy photos, batch parsing and
the enrichment-time trigger (food trades only).
"""

from services.photo_labeling_service import PhotoLabelingService, should_label_for_category
from services.photo_labels import (
    is_card_worthy,
    is_unfit_for_card,
    labels_for_urls,
    normalize_label,
    rank_card_photos,
)


def test_normalize_label_coerces_shape_and_caps_values() -> None:
    label = normalize_label(
        {"kind": "Dish", "description": "  Burger  ", "dishes": ["Tacos", "Tacos", 42], "appeal": "9"}
    )
    assert label == {"kind": "dish", "description": "Burger", "dishes": ["Tacos", "42"], "appeal": 5}


def test_normalize_label_rejects_unknown_kind_and_non_dict() -> None:
    assert normalize_label({"kind": "spaceship"}) is None
    assert normalize_label("dish") is None
    assert normalize_label(None) is None


def test_card_worthiness_predicates() -> None:
    assert is_card_worthy({"kind": "dish"})
    assert is_card_worthy({"kind": "drink"})
    assert not is_card_worthy({"kind": "truck"})
    assert not is_card_worthy(None)
    assert is_unfit_for_card({"kind": "truck"})
    assert is_unfit_for_card({"kind": "menu_board"})
    assert not is_unfit_for_card(None)  # unlabelled = unknown, still a last-resort fallback


def test_labels_for_urls_restricts_and_normalises() -> None:
    stored = {"a": {"kind": "dish", "appeal": 4}, "b": {"kind": "nope"}, "c": {"kind": "truck"}}
    assert set(labels_for_urls(stored, ["a", "b", "z"])) == {"a"}
    assert labels_for_urls(None, ["a"]) == {}


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
            {"index": 1, "kind": "truck", "description": "Camion", "appeal": 2},
            {"index": 9, "kind": "dish"},
            {"kind": "bogus"},
        ]
    }
    labels = PhotoLabelingService.parse_batch_answer(answer, batch)
    assert labels["u2"]["kind"] == "dish"
    assert labels["u1"]["kind"] == "truck"
    assert "u3" not in labels


def test_parse_batch_answer_falls_back_to_position_without_index() -> None:
    labels = PhotoLabelingService.parse_batch_answer({"photos": [{"kind": "dish"}, {"kind": "event"}]}, ["a", "b"])
    assert labels == {
        "a": {"kind": "dish", "description": "", "dishes": [], "appeal": 0},
        "b": {"kind": "event", "description": "", "dishes": [], "appeal": 0},
    }
    assert PhotoLabelingService.parse_batch_answer(None, ["a"]) == {}
    assert PhotoLabelingService.parse_batch_answer({"photos": "x"}, ["a"]) == {}


def test_should_label_for_category_targets_food_trades() -> None:
    assert should_label_for_category("Food truck")
    assert should_label_for_category("Restaurant de tacos")
    assert should_label_for_category("Traiteur")
    assert not should_label_for_category("Plombier")
    assert not should_label_for_category(None)
