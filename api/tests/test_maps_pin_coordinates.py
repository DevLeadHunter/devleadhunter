"""
The « nous trouver » map of a demo site sits on the business's own pin, read from its Google Maps URL.
"""

from __future__ import annotations

from services.demo_site_service import DemoSiteService

_PLACE_URL = (
    "https://www.google.com/maps/place/TP+Motorsport+s%C3%A1rl/@46.242548,7.3352826,17z/"
    "data=!3m1!4b1!4m6!3m5!1s0x478eddfd8f21dd91:0x7b3a9f35b76f1e63!8m2!3d46.2425443!4d7.3378575"
)


def test_the_place_pin_wins_over_the_centre_of_the_map_view() -> None:
    assert DemoSiteService._coords_from_maps_url(_PLACE_URL) == (46.2425443, 7.3378575)


def test_a_url_without_a_pin_falls_back_to_the_centre_of_the_map_view() -> None:
    assert DemoSiteService._coords_from_maps_url("https://www.google.com/maps/@47.39,0.68,17z") == (47.39, 0.68)


def test_a_url_without_coordinates_gives_no_position() -> None:
    assert DemoSiteService._coords_from_maps_url("https://maps.app.goo.gl/5KyQbRcibeQFgVhi7") is None
