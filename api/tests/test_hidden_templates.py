"""
Templates retired from the picker stay registered: the sites already generated with them must keep
rendering and regenerating, and the catalogue flags them so the dashboard stops offering them.
"""

from services.templates import registry
from services.templates.registry import AVAILABLE_TEMPLATES, HIDDEN_TEMPLATE_IDS


def test_hidden_templates_are_flagged_in_the_catalogue() -> None:
    flagged = {str(meta["id"]) for meta in AVAILABLE_TEMPLATES if meta["is_hidden"]}
    assert flagged == set(HIDDEN_TEMPLATE_IDS) == {"plumber-atelier", "plumber-cuivre"}


def test_plumber_signature_stays_offered() -> None:
    visible = {str(meta["id"]) for meta in AVAILABLE_TEMPLATES if not meta["is_hidden"]}
    assert "plumber-signature" in visible


def test_hidden_templates_keep_their_module() -> None:
    for template_id in HIDDEN_TEMPLATE_IDS:
        assert template_id == registry.get_module(template_id).TEMPLATE_ID
