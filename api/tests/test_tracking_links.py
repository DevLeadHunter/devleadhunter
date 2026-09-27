"""Unit tests for the demo/video link attribution helper."""

from services.tracking_links import (
    CHANNEL_EMAIL,
    CHANNEL_SMS,
    append_query_param,
    email_tracked_link,
    sms_tracked_link,
)


class TestAppendQueryParam:
    def test_first_param_uses_question_mark(self) -> None:
        assert (
            append_query_param("https://demo.dibodev.fr/x", "src", CHANNEL_SMS) == "https://demo.dibodev.fr/x?src=sms"
        )

    def test_second_param_uses_ampersand(self) -> None:
        # An SMS-tagged demo link, then an email link with the A/B variant chained on.
        url = append_query_param("https://demo.dibodev.fr/x", "src", CHANNEL_EMAIL)
        assert append_query_param(url, "v", "A") == "https://demo.dibodev.fr/x?src=email&v=A"


class TestEmailTrackedLink:
    def test_the_email_channel_comes_first(self) -> None:
        assert email_tracked_link("https://demo.dibodev.fr/ia/garage") == "https://demo.dibodev.fr/ia/garage?src=email"

    def test_the_variant_follows_the_channel(self) -> None:
        assert (
            email_tracked_link("https://demo.dibodev.fr/va/garage", "B")
            == "https://demo.dibodev.fr/va/garage?src=email&v=B"
        )


class TestSmsTrackedLink:
    def test_demo_page_gets_the_short_prefix(self) -> None:
        assert sms_tracked_link("https://demo.dibodev.fr/chez-mimon") == "https://demo.dibodev.fr/s/chez-mimon"

    def test_video_page_keeps_its_own_path(self) -> None:
        assert sms_tracked_link("https://demo.dibodev.fr/v/chez-mimon") == "https://demo.dibodev.fr/s/v/chez-mimon"

    def test_receptionist_pages_keep_their_own_path(self) -> None:
        assert sms_tracked_link("https://demo.dibodev.fr/ia/garage") == "https://demo.dibodev.fr/s/ia/garage"
        assert sms_tracked_link("https://demo.dibodev.fr/va/garage") == "https://demo.dibodev.fr/s/va/garage"

    def test_no_visible_tracking_parameter(self) -> None:
        assert "?" not in sms_tracked_link("https://demo.dibodev.fr/chez-mimon")
