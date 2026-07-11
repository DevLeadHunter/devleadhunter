"""Unit tests for the scraping-resilience helpers (JSON-LD, phone, email, chains).

Pure-Python, no network, no DB — runnable with ``python -m pytest tests/test_resilient_extract.py``
from the ``api`` directory, or directly with ``python tests/test_resilient_extract.py``.
"""
from __future__ import annotations

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from scrappers.resilient_extract import (  # noqa: E402
    extract_ld_json_from_html,
    find_phone,
    first_nonempty,
    parse_ld_json_blocks,
    safe_email,
)

# A realistic Pages Jaunes / Google-style LocalBusiness JSON-LD block.
_PLUMBER_LD = """
{
  "@context": "https://schema.org",
  "@type": "Plumber",
  "name": "Plomberie Dupont",
  "telephone": "01 23 45 67 89",
  "url": "https://plomberie-dupont.fr",
  "email": "contact@plomberie-dupont.fr",
  "address": {
    "@type": "PostalAddress",
    "streetAddress": "12 rue des Lilas",
    "postalCode": "75011",
    "addressLocality": "Paris"
  },
  "aggregateRating": {"@type": "AggregateRating", "ratingValue": "4,8", "reviewCount": "132"}
}
"""


def test_parse_ld_json_typed_business() -> None:
    biz = parse_ld_json_blocks([_PLUMBER_LD])
    assert biz is not None
    assert biz["name"] == "Plomberie Dupont"
    assert biz["phone"] == "01 23 45 67 89"
    assert biz["website"] == "https://plomberie-dupont.fr"
    assert biz["email"] == "contact@plomberie-dupont.fr"
    assert biz["street"] == "12 rue des Lilas"
    assert biz["postal_code"] == "75011"
    assert biz["city"] == "Paris"
    assert biz["category"] == "Plumber"
    assert biz["rating"] == 4.8
    assert biz["reviews_count"] == 132


def test_parse_ld_json_graph_container() -> None:
    payload = '{"@context":"https://schema.org","@graph":[{"@type":"WebSite","name":"x"},%s]}' % _PLUMBER_LD.strip()
    biz = parse_ld_json_blocks([payload])
    assert biz is not None and biz["name"] == "Plomberie Dupont"


def test_parse_ld_json_array_and_dict_inputs() -> None:
    import json

    as_dict = json.loads(_PLUMBER_LD)
    assert parse_ld_json_blocks([as_dict])["phone"] == "01 23 45 67 89"
    assert parse_ld_json_blocks(as_dict)["phone"] == "01 23 45 67 89"  # single, not a list
    assert parse_ld_json_blocks([[as_dict]])["phone"] == "01 23 45 67 89"  # nested list


def test_parse_ld_json_untyped_but_business_shaped() -> None:
    # No @type, but has telephone + address → still recognised.
    block = '{"name":"Garage X","telephone":"0479004218","address":"5 av. de Lyon"}'
    biz = parse_ld_json_blocks([block])
    assert biz is not None and biz["phone"] == "0479004218"


def test_parse_ld_json_none_cases() -> None:
    assert parse_ld_json_blocks([]) is None
    assert parse_ld_json_blocks(["not json at all {"]) is None
    assert parse_ld_json_blocks(['{"@type":"WebSite","name":"just a site"}']) is None
    assert parse_ld_json_blocks(None) is None


def test_extract_ld_json_from_html() -> None:
    html = (
        "<html><head>"
        '<script type="application/ld+json">' + _PLUMBER_LD + "</script>"
        '<script type="text/javascript">var x = 1;</script>'
        "<script type='application/ld+json' data-x=\"y\">{\"@type\":\"Store\",\"name\":\"S\"}</script>"
        "</head></html>"
    )
    blocks = extract_ld_json_from_html(html)
    assert len(blocks) == 2  # both ld+json blocks, not the js one
    biz = parse_ld_json_blocks(blocks)
    assert biz is not None and biz["name"] == "Plomberie Dupont"  # first typed business wins


def test_extract_ld_json_from_html_empty() -> None:
    assert extract_ld_json_from_html("<html><body>no ld here</body></html>") == []
    assert extract_ld_json_from_html(None) == []


def test_safe_email() -> None:
    assert safe_email("Contact@Example.COM") == "contact@example.com"
    assert safe_email("mailto:hi@site.fr") == "hi@site.fr"
    assert safe_email("<a@b.co>") == "a@b.co"
    assert safe_email("not-an-email") is None
    assert safe_email("a@b") is None  # no TLD
    assert safe_email("") is None
    assert safe_email(None) is None


def test_find_phone() -> None:
    assert find_phone("Tél : 01 23 45 67 89").replace(" ", "") == "0123456789"
    assert find_phone("Appelez le 04.79.00.42.18").replace(".", "").replace(" ", "") == "0479004218"
    assert find_phone("+33 1 23 45 67 89") is not None
    assert find_phone("réf 12345") is None  # too short to be a phone
    assert find_phone(None) is None
    assert find_phone("aucun numéro ici") is None


def test_first_nonempty() -> None:
    assert first_nonempty(None, "", "  ", "hit", "later") == "hit"
    assert first_nonempty(None, "", "   ") is None
    assert first_nonempty("  trimmed  ") == "trimmed"


if __name__ == "__main__":
    # Allow running without pytest: execute every test_* function.
    functions = [v for k, v in sorted(globals().items()) if k.startswith("test_") and callable(v)]
    for fn in functions:
        fn()
        print(f"[OK] {fn.__name__}")
    print(f"\nAll {len(functions)} tests passed.")
