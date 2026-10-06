"""The mail check of an email's domain: a slow answer proves nothing, name servers that all fail do."""

import asyncio

import dns.resolver
import pytest

from services.prospect_search.contact_finder import EmailDomainCheck

_BROKEN_DOMAIN = "energyprojects.ch"


def _answer_with(monkeypatch: pytest.MonkeyPatch, outcomes: dict[tuple[bool, str], Exception | None]) -> None:
    """Make every DNS lookup answer from *outcomes*, keyed by (asked through public resolvers, domain)."""

    def resolve(self: dns.resolver.Resolver, qname: str, rdtype: str = "A", *_: object, **__: object) -> object:
        is_public = "8.8.8.8" in list(self.nameservers)
        outcome = outcomes.get((is_public, str(qname)))
        if outcome is not None:
            raise outcome
        return object()

    monkeypatch.setattr(dns.resolver.Resolver, "resolve", resolve)


def _receives_mail(email: str) -> bool:
    return asyncio.run(EmailDomainCheck().receives_mail(email))


def test_a_domain_whose_name_servers_all_fail_receives_no_mail(monkeypatch: pytest.MonkeyPatch) -> None:
    _answer_with(
        monkeypatch,
        {(False, _BROKEN_DOMAIN): dns.resolver.LifetimeTimeout(), (True, _BROKEN_DOMAIN): dns.resolver.NoNameservers()},
    )

    assert _receives_mail(f"info@{_BROKEN_DOMAIN}") is False


def test_a_domain_that_is_only_slow_keeps_its_email(monkeypatch: pytest.MonkeyPatch) -> None:
    _answer_with(
        monkeypatch,
        {
            (False, _BROKEN_DOMAIN): dns.resolver.LifetimeTimeout(),
            (True, _BROKEN_DOMAIN): dns.resolver.LifetimeTimeout(),
        },
    )

    assert _receives_mail(f"info@{_BROKEN_DOMAIN}") is True


def test_public_resolvers_that_fail_for_every_domain_prove_nothing(monkeypatch: pytest.MonkeyPatch) -> None:
    _answer_with(
        monkeypatch,
        {
            (False, _BROKEN_DOMAIN): dns.resolver.LifetimeTimeout(),
            (True, _BROKEN_DOMAIN): dns.resolver.NoNameservers(),
            (True, "gmail.com"): dns.resolver.NoNameservers(),
        },
    )

    assert _receives_mail(f"info@{_BROKEN_DOMAIN}") is True
