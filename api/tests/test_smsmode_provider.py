"""Unit tests for the smsmode provider payload + response parsing (no network)."""

import httpx
import pytest

from services.sms.smsmode_provider import SmsModeProvider
from services.sms.templates import DEFAULT_FOLLOW_UP_KEY, find_sms_template
from services.sms_service import SmsService


class TestSmsModeProvider:
    @pytest.mark.asyncio
    async def test_successful_send_parses_id_and_price(self, monkeypatch: pytest.MonkeyPatch) -> None:
        captured: dict = {}

        def handler(request: httpx.Request) -> httpx.Response:
            captured["url"] = str(request.url)
            captured["headers"] = dict(request.headers)
            import json

            captured["body"] = json.loads(request.content)
            return httpx.Response(200, json={"messageId": "abc123", "price": {"amount": 0.06, "currency": "EUR"}})

        transport = httpx.MockTransport(handler)
        original = httpx.AsyncClient

        def patched_client(*args, **kwargs):
            kwargs["transport"] = transport
            return original(*args, **kwargs)

        monkeypatch.setattr(httpx, "AsyncClient", patched_client)

        provider = SmsModeProvider()
        provider._api_key = "test-key"
        result = await provider.send(to_e164="+33629345899", sender="Dibodev", text="Bonjour", ref_client="7")

        assert result.success is True
        assert result.provider_message_id == "abc123"
        assert result.price_cents == 6  # 0.06 € → cents
        assert captured["headers"]["x-api-key"] == "test-key"
        assert captured["body"] == {
            "recipient": {"to": "+33629345899"},
            "body": {"text": "Bonjour"},
            "from": "Dibodev",
            "refClient": "7",
        }

    @pytest.mark.asyncio
    async def test_api_error_returns_failure(self, monkeypatch: pytest.MonkeyPatch) -> None:
        transport = httpx.MockTransport(lambda req: httpx.Response(422, text="bad sender"))
        original = httpx.AsyncClient
        monkeypatch.setattr(
            httpx,
            "AsyncClient",
            lambda *a, **k: original(*a, **{**k, "transport": transport}),
        )
        provider = SmsModeProvider()
        provider._api_key = "test-key"
        result = await provider.send(to_e164="+33629345899", sender="Dibodev", text="x")
        assert result.success is False
        assert "422" in (result.error or "")

    @pytest.mark.asyncio
    async def test_json_error_surfaces_message_and_detail(self, monkeypatch: pytest.MonkeyPatch) -> None:
        body = {
            "title": "Bad Request",
            "message": "Request body: refClient invalid",
            "detail": "Size must be between 3 and 140 characters",
        }
        transport = httpx.MockTransport(lambda req: httpx.Response(400, json=body))
        original = httpx.AsyncClient
        monkeypatch.setattr(
            httpx,
            "AsyncClient",
            lambda *a, **k: original(*a, **{**k, "transport": transport}),
        )
        provider = SmsModeProvider()
        provider._api_key = "test-key"
        result = await provider.send(to_e164="+33629345899", sender="Dibodev", text="x", ref_client="dlh-1")
        assert result.success is False
        assert "refClient invalid" in (result.error or "")
        assert "3 and 140" in (result.error or "")

    def test_not_configured_without_key(self) -> None:
        provider = SmsModeProvider()
        provider._api_key = ""
        assert provider.is_configured is False

    @pytest.mark.asyncio
    async def test_credit_balance_parses_bare_number(self, monkeypatch: pytest.MonkeyPatch) -> None:
        captured: dict = {}

        def handler(request: httpx.Request) -> httpx.Response:
            captured["url"] = str(request.url)
            captured["headers"] = dict(request.headers)
            return httpx.Response(200, text="152.5")

        transport = httpx.MockTransport(handler)
        original = httpx.AsyncClient
        monkeypatch.setattr(httpx, "AsyncClient", lambda *a, **k: original(*a, **{**k, "transport": transport}))

        provider = SmsModeProvider()
        provider._api_key = "test-key"
        balance = await provider.get_credit_balance()

        assert balance == 152.5
        assert captured["headers"]["x-api-key"] == "test-key"
        assert "accessToken=test-key" in captured["url"]

    @pytest.mark.asyncio
    async def test_credit_balance_none_on_http_error(self, monkeypatch: pytest.MonkeyPatch) -> None:
        transport = httpx.MockTransport(lambda req: httpx.Response(401, text="unauthorized"))
        original = httpx.AsyncClient
        monkeypatch.setattr(httpx, "AsyncClient", lambda *a, **k: original(*a, **{**k, "transport": transport}))
        provider = SmsModeProvider()
        provider._api_key = "test-key"
        assert await provider.get_credit_balance() is None

    @pytest.mark.asyncio
    async def test_credit_balance_none_without_key(self) -> None:
        provider = SmsModeProvider()
        provider._api_key = ""
        assert await provider.get_credit_balance() is None

    def test_parse_credit_handles_status_prefix_and_comma(self) -> None:
        assert SmsModeProvider._parse_credit("0 | 42,75") == 42.75
        assert SmsModeProvider._parse_credit("bad") is None


class TestComposeBody:
    def test_relance_body_recalls_the_email_with_link_signature_and_stop(self) -> None:
        service = SmsService()
        template = find_sms_template(DEFAULT_FOLLOW_UP_KEY)
        assert template is not None
        body = service.compose_from_template(
            template,
            {"salutation": "Bonjour Marc", "lien_demo": "demo.dibodev.fr/garage-central", "signature": "Léo"},
        )
        assert "email" in body
        assert "demo.dibodev.fr/garage-central" in body
        assert body.endswith("STOP au 36180")
        assert body.count("36180") == 1
        assert "Léo" in body
