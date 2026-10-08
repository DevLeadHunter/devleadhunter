"""
Léo's rule for site copy (12 Sep 2026): no em dash (« — ») in what a demo site says, commas, colons and
periods instead. Checked on the templates of the wave 4 campaign, whose garage copy still had five.
"""

from typing import Any

import pytest

from services.templates import registry

_EM_DASH = "—"


def _texts_in(node: Any) -> list[str]:
    """Every string of a content tree."""
    if isinstance(node, dict):
        return [text for value in node.values() for text in _texts_in(value)]
    if isinstance(node, list):
        return [text for item in node for text in _texts_in(item)]
    return [node] if isinstance(node, str) else []


@pytest.mark.parametrize("template_id", ["landscaper-verdure", "mechanic-pitlane", "electrician-eclat"])
def test_the_generated_copy_has_no_em_dash(template_id: str) -> None:
    site = registry.build_site_content(
        template_id=template_id,
        business_name="Exemple Services",
        phone="0600000000",
        email="contact@exemple.fr",
        city="Tours",
        area="Tours",
        subtitle=registry.default_subtitle(template_id, "Tours"),
        palette=registry.default_theme(template_id),
        enrichment={},
    )

    assert [text for text in _texts_in(site) if _EM_DASH in text] == []
