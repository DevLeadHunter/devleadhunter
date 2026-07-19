"""DMARC inheritance rules for sending subdomains.

The trap this guards against: a parent in ``p=quarantine;sp=none`` looks healthy
when only ``p`` is read, while the subdomain actually used to send outreach is
enforced by nothing.
"""
from typing import Any

import pytest

import services.email_dns_service as dns_service


@pytest.fixture(autouse=True)
def clear_cache() -> None:
    """Drop the module-level cache so each case resolves fresh records."""
    dns_service.email_dns_service._cache.clear()


def _with_records(monkeypatch: pytest.MonkeyPatch, records: dict[str, list[str]]) -> None:
    """Serve *records* instead of real DNS lookups.

    @param monkeypatch - Pytest patcher.
    @param records - TXT values keyed by DNS name.
    """
    monkeypatch.setattr(dns_service, "_txt_records", lambda name: records.get(name, []))


def test_subdomain_inherits_parent_policy_from_sp(monkeypatch: pytest.MonkeyPatch) -> None:
    """An enforced ``sp`` on the parent protects the sending subdomain."""
    _with_records(
        monkeypatch,
        {"_dmarc.example.fr": ["v=DMARC1;p=quarantine;sp=quarantine;rua=mailto:a@example.fr"]},
    )
    result: dict[str, Any] = dns_service.email_dns_service._check_dmarc("mail.example.fr")

    assert result["status"] == "ok"
    assert result["policy"] == "quarantine"
    assert result["inherited_from"] == "example.fr"


def test_subdomain_is_flagged_when_parent_declares_sp_none(monkeypatch: pytest.MonkeyPatch) -> None:
    """``p=quarantine;sp=none`` leaves the sending subdomain unprotected."""
    _with_records(monkeypatch, {"_dmarc.example.fr": ["v=DMARC1;p=quarantine;sp=none"]})
    result: dict[str, Any] = dns_service.email_dns_service._check_dmarc("mail.example.fr")

    assert result["status"] == "warn"
    assert result["policy"] == "none"
    assert "sp=" in result["detail"]


def test_subdomain_falls_back_to_p_when_sp_is_absent(monkeypatch: pytest.MonkeyPatch) -> None:
    """Without ``sp``, subdomains follow ``p`` (RFC 7489)."""
    _with_records(monkeypatch, {"_dmarc.example.fr": ["v=DMARC1;p=reject;rua=mailto:a@example.fr"]})
    result: dict[str, Any] = dns_service.email_dns_service._check_dmarc("mail.example.fr")

    assert result["status"] == "ok"
    assert result["policy"] == "reject"


def test_own_record_wins_over_the_parent(monkeypatch: pytest.MonkeyPatch) -> None:
    """A record published on the subdomain itself is not inherited."""
    _with_records(
        monkeypatch,
        {
            "_dmarc.mail.example.fr": ["v=DMARC1;p=reject;rua=mailto:a@example.fr"],
            "_dmarc.example.fr": ["v=DMARC1;p=none"],
        },
    )
    result: dict[str, Any] = dns_service.email_dns_service._check_dmarc("mail.example.fr")

    assert result["policy"] == "reject"
    assert result["inherited_from"] is None


def test_bare_p_selector_counts_as_a_dkim_key(monkeypatch: pytest.MonkeyPatch) -> None:
    """Resend publishes ``p=…`` without ``v=DKIM1`` — it must still be found."""
    _with_records(monkeypatch, {"resend._domainkey.mail.example.fr": ["p=MIGfMA0GCSqGSIb3DQ"]})
    result: dict[str, Any] = dns_service.email_dns_service._check_dkim("mail.example.fr")

    assert result["status"] == "ok"
    assert result["selectors"] == ["resend"]


def test_organizational_domain_without_record_is_danger(monkeypatch: pytest.MonkeyPatch) -> None:
    """No DMARC anywhere stays a hard failure."""
    _with_records(monkeypatch, {})
    result: dict[str, Any] = dns_service.email_dns_service._check_dmarc("example.fr")

    assert result["status"] == "danger"
    assert result["record"] is None
