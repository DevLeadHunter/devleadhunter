"""A Google result hidden behind Google's own redirect is read at the address written under its title."""

import pytest

from scrappers.google_result_link import GoogleResultLink

_REDIRECT = "https://www.google.com/goto?url=CAEShAEB6zswFa15c_X0UKzJbxn7VHnYWp2tKcWgjAoOtcVo66UDknDMUTdhIlgcpi2d"


def test_a_redirected_result_is_the_front_page_of_the_site_shown_under_its_title() -> None:
    """Search n° 17: the result giving Welington Automobiles' email hid « welingtonautomobiles.fr » behind it."""
    result = {"link": _REDIRECT, "display_link": "https://welingtonautomobiles.fr › vehicules"}

    assert GoogleResultLink.address_of(result) == "https://welingtonautomobiles.fr/"


def test_a_shown_address_without_its_scheme_is_still_read() -> None:
    assert GoogleResultLink.address_of({"link": _REDIRECT, "display_link": "www.exemple-garage.fr › contact"}) == (
        "https://www.exemple-garage.fr/"
    )


def test_a_plain_link_is_kept_as_it_is() -> None:
    link = "https://www.welingtonautomobiles.fr/414/vehicules/?marque=834"

    assert (
        GoogleResultLink.address_of({"link": link, "display_link": "https://www.welingtonautomobiles.fr › vehicules"})
        == link
    )


@pytest.mark.parametrize(
    "display_link",
    [None, "", "https://www.garage-exemple-et-fils-automob…", "https://sites.google.com › view › garage-exemple"],
)
def test_a_redirect_showing_no_readable_site_stays_the_redirect(display_link: str | None) -> None:
    assert GoogleResultLink.address_of({"link": _REDIRECT, "display_link": display_link}) == _REDIRECT


def test_a_business_page_on_a_google_host_is_not_taken_for_a_redirect() -> None:
    link = "https://sites.google.com/view/garage-exemple"

    assert GoogleResultLink.address_of({"link": link, "display_link": "https://sites.google.com › view"}) == link
