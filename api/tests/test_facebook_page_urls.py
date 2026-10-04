"""Reading Facebook URLs and result titles: one page, one address, one name."""

import pytest

from scrappers.facebook_page_urls import FacebookPageUrl


class TestCanonicalPageUrl:
    def test_plain_handle_drops_trailing_slash(self) -> None:
        assert FacebookPageUrl.canonical("https://www.facebook.com/PizzaFlam44/") == (
            "https://www.facebook.com/PizzaFlam44"
        )

    def test_mobile_host_and_subtab_collapse_to_page(self) -> None:
        assert FacebookPageUrl.canonical("https://m.facebook.com/PizzaFlam44/photos") == (
            "https://www.facebook.com/PizzaFlam44"
        )

    def test_post_url_collapses_to_page(self) -> None:
        assert FacebookPageUrl.canonical("https://www.facebook.com/bandbfoodtruck/posts/123456") == (
            "https://www.facebook.com/bandbfoodtruck"
        )

    def test_pg_prefix_normalizes_to_handle(self) -> None:
        assert FacebookPageUrl.canonical("https://www.facebook.com/pg/PizzaFlam44/about") == (
            "https://www.facebook.com/PizzaFlam44"
        )

    def test_profile_php_kept_with_id(self) -> None:
        raw = "https://www.facebook.com/profile.php?id=100057123456789&sk=about"
        assert FacebookPageUrl.canonical(raw) == "https://www.facebook.com/profile.php?id=100057123456789"

    def test_permalink_of_a_recent_page_collapses_to_its_id(self) -> None:
        raw = "https://www.facebook.com/p/Toupet-entretien-paysager-61556600054118/?locale=fr_CA"
        assert FacebookPageUrl.canonical(raw) == "https://www.facebook.com/61556600054118"

    def test_people_address_collapses_to_the_page_id(self) -> None:
        raw = "https://www.facebook.com/people/Jardins-Martin/100075901827931/?sk=about"
        assert FacebookPageUrl.canonical(raw) == "https://www.facebook.com/100075901827931"

    def test_permalink_prefix_alone_is_not_a_page(self) -> None:
        assert FacebookPageUrl.canonical("https://www.facebook.com/p/") is None

    def test_pages_slug_id_form_kept(self) -> None:
        raw = "https://www.facebook.com/pages/Chez-Marcel/123456789"
        assert FacebookPageUrl.canonical(raw) == "https://www.facebook.com/pages/Chez-Marcel/123456789"

    @pytest.mark.parametrize(
        "feature_url",
        [
            "https://www.facebook.com/login/?next=x",
            "https://www.facebook.com/groups/123456/",
            "https://www.facebook.com/watch/?v=123",
            "https://www.facebook.com/sharer/sharer.php?u=x",
            "https://www.facebook.com/hashtag/foodtruck",
            "https://www.facebook.com/events/123456/",
            "https://www.facebook.com/",
        ],
    )
    def test_feature_urls_are_not_pages(self, feature_url: str) -> None:
        assert FacebookPageUrl.canonical(feature_url) is None

    def test_another_site_is_not_a_page(self) -> None:
        assert FacebookPageUrl.canonical("https://example.com/PizzaFlam44") is None


class TestBusinessNameOfTitle:
    def test_strips_facebook_suffix(self) -> None:
        assert FacebookPageUrl.business_name_of_title("PIZZ'A FLAM | Facebook") == "PIZZ'A FLAM"

    def test_strips_subtab_and_facebook(self) -> None:
        assert FacebookPageUrl.business_name_of_title("B&B le Food truck - Posts | Facebook") == "B&B le Food truck"

    def test_strips_notification_prefix(self) -> None:
        assert FacebookPageUrl.business_name_of_title("(3) PIZZ'A FLAM | Facebook") == "PIZZ'A FLAM"

    def test_strips_french_subtab(self) -> None:
        assert FacebookPageUrl.business_name_of_title("Tacos Maru - Avis | Facebook") == "Tacos Maru"
