"""
Pick the email that actually belongs to a prospect out of a Google results page.

The email scraper used to keep the FIRST non-blacklisted address found on the
SERP, which routinely returned a town hall / directory / tourist-office address
(a garage getting ``contact@saint-germain-lembron.fr``, the town's mairie).
Sending to those addresses burns the sending domain's reputation.

Léo's decision (2026-08-25): never build an aggressive filter. A real prospect
email often has NO link to the business name or its city (someone whose main
inbox is named after a footballer), so name/domain coherence is used ONLY as a
positive ranking signal, never as a reason to reject. We prefer a couple of
visible false positives to dozens of prospects silently dropped.

Two stages:
  1. Disqualify — the only hard reject, restricted to families that are provably
     never a prospect (state domains, town halls, tourist offices, a domain that
     is exactly the city name, known directories, socials, noreply artefacts).
  2. Score the survivors on positive signals and keep the best. As long as one
     candidate survives stage 1 we return it, even with a low score; ``None``
     only when everything is disqualified or no email was found at all.
"""

from __future__ import annotations

import re
from bisect import bisect_left
from urllib.parse import urlparse

from services.decision_maker.normalize import company_tokens, fold

# Mailbox providers whose domain carries no business identity — the domain-equals-city
# reject must never fire on these (``leo.rennes@gmail.com`` is legitimate).
GENERIC_EMAIL_PROVIDERS: frozenset[str] = frozenset(
    {
        "gmail.com",
        "googlemail.com",
        "orange.fr",
        "wanadoo.fr",
        "free.fr",
        "sfr.fr",
        "neuf.fr",
        "laposte.net",
        "hotmail.com",
        "hotmail.fr",
        "outlook.com",
        "outlook.fr",
        "live.fr",
        "live.com",
        "msn.com",
        "yahoo.com",
        "yahoo.fr",
        "ymail.com",
        "icloud.com",
        "me.com",
        "aol.com",
        "gmx.fr",
        "gmx.com",
        "bbox.fr",
        "numericable.fr",
        "protonmail.com",
        "proton.me",
        "bluewin.ch",
        "bluemail.ch",
        "gmx.ch",
        "gmx.net",
        "sunrise.ch",
        "hispeed.ch",
        "skynet.be",
        "telenet.be",
        "proximus.be",
        "voo.be",
        "hotmail.be",
        "pt.lu",
        "videotron.ca",
        "sympatico.ca",
        "bell.net",
        "hotmail.ca",
        "live.ca",
        "yahoo.ca",
        "globetrotter.net",
        "cgocable.ca",
    }
)

# Domains that are never a real business contact (platforms, aggregators, directories…).
BLOCKED_DOMAINS: frozenset[str] = frozenset(
    {
        "example.com",
        "test.com",
        "domain.com",
        "yoursite.com",
        "sentry.io",
        "google.com",
        "gstatic.com",
        "googleapis.com",
        "facebook.com",
        "instagram.com",
        "twitter.com",
        "x.com",
        "linkedin.com",
        "youtube.com",
        "tiktok.com",
        "pinterest.com",
        "pinterest.fr",
        "snapchat.com",
        # Review / aggregator sites
        "eldo.com",
        "avis-verifies.com",
        "trustpilot.com",
        "tripadvisor.com",
        "tripadvisor.fr",
        "yelp.com",
        "yelp.fr",
        # Directories (a prospect never owns an address on these)
        "plombiers.com",
        "electriciens.com",
        "artisans.com",
        "pagesjaunes.fr",
        "pages-jaunes.fr",
        "annuaire.com",
        "annuaires.com",
        "kompass.com",
        "societe.com",
        "verif.com",
        "infogreffe.fr",
        "vroomly.com",
        "allogarage.fr",
        "cylex-france.fr",
        "cylex.fr",
        "justacote.com",
        "118000.fr",
        "118712.fr",
        "mappy.com",
        "hoodspot.fr",
        "starofservice.com",
        "ootravaux.fr",
        "travaux.com",
        "houzz.fr",
        "local.ch",
        "search.ch",
        "localsearch.ch",
        "moneyhouse.ch",
        "zefix.ch",
        "help.ch",
        "monetas.ch",
        "renovero.ch",
        "ofri.ch",
        "swissfirms.ch",
        "houzz.ch",
        "yelp.ch",
        "tripadvisor.ch",
        "goldenpages.be",
        "pagesdor.be",
        "goudengids.be",
        "infobel.be",
        "infobel.com",
        "companyweb.be",
        "trendstop.levif.be",
        "openthebox.be",
        "1307.be",
        "houzz.be",
        "yelp.be",
        "tripadvisor.be",
        "editus.lu",
        "yellow.lu",
        "lbr.lu",
        "pagesjaunes.ca",
        "yellowpages.ca",
        "411.ca",
        "canada411.ca",
        "canpages.ca",
        "soumissionrenovation.ca",
        "reno-assistance.ca",
        "homestars.com",
        "houzz.ca",
        "yelp.ca",
        "tripadvisor.ca",
        "bbb.org",
        "opencorporates.com",
        # Genealogy / off-topic sites surfacing in broad searches
        "geneafrance.com",
        "geneanet.org",
        "filae.com",
        # Public services
        "service-public.fr",
        "pole-emploi.fr",
        "urssaf.fr",
    }
)

# Substrings marking a public collectivity anywhere in the domain (never an artisan).
BLOCKED_DOMAIN_SUBSTRINGS: tuple[str, ...] = (
    "mairie",
    "prefecture",
    "gendarmerie",
)

# Collectivity / tourist-office shapes matched on the full domain.
BLOCKED_DOMAIN_PATTERNS: tuple[re.Pattern[str], ...] = (
    re.compile(r"\.gouv\.fr$"),
    re.compile(r"(^|\.)admin\.ch$"),
    re.compile(r"(^|\.)(ag|ai|ar|be|bl|bs|fr|ge|gl|gr|ju|lu|ne|nw|ow|sg|sh|so|sz|tg|ti|ur|vd|vs|zg|zh)\.ch$"),
    re.compile(r"(^|\.)fgov\.be$"),
    re.compile(r"(^|\.)belgium\.be$"),
    re.compile(r"(^|\.)public\.lu$"),
    re.compile(r"(^|\.)gc\.ca$"),
    re.compile(r"(^|\.)gouv\.qc\.ca$"),
    re.compile(r"(^|\.)ville\."),
    re.compile(r"(^|[.-])ville-"),
    re.compile(r"(^|[.-])cc-"),
    re.compile(r"(^|[.-])ccas([.-]|$)"),
    re.compile(r"communaute-de-communes"),
    re.compile(r"office.?de.?tourisme"),
    re.compile(r"(^|[.-])ot-"),
    re.compile(r"-tourisme\.(fr|com)$"),
    re.compile(r"(^|[.-])tourisme-"),
)

# Local parts that are never the real business contact.
BLOCKED_LOCAL_PREFIXES: tuple[str, ...] = (
    "u003",
    "u0022",
    "noreply",
    "no-reply",
    "donotreply",
    "do-not-reply",
    "service-avis",
    "avis@",
    "mairie",
)

# Role inboxes that are typically the business's own contact address.
ROLE_LOCAL_PARTS: frozenset[str] = frozenset(
    {
        "contact",
        "contactez",
        "info",
        "infos",
        "bonjour",
        "hello",
        "accueil",
        "rdv",
        "commercial",
        "direction",
        "secretariat",
        "devis",
    }
)

_EMAIL_PATTERN: re.Pattern[str] = re.compile(r"[a-z0-9._%+-]+@[a-z0-9.-]+\.[a-z]{2,}")

# Proximity credit reaches zero beyond this many chars from the nearest name mention.
_PROXIMITY_REACH_CHARS: int = 1500

_CANADIAN_SECOND_LEVEL_SUFFIXES: frozenset[str] = frozenset(
    {
        "ab.ca",
        "bc.ca",
        "gc.ca",
        "mb.ca",
        "nb.ca",
        "nf.ca",
        "nl.ca",
        "ns.ca",
        "nt.ca",
        "nu.ca",
        "on.ca",
        "pe.ca",
        "qc.ca",
        "sk.ca",
        "yk.ca",
    }
)


class EmailCandidateScorer:
    """Rank the emails found on a page and return the one most likely the prospect's."""

    def best_email(self, page_text: str, *, name: str, city: str, website: str | None = None) -> str | None:
        """Return the highest-scored non-disqualified email of *page_text*, or ``None``.

        A survivor is always returned even with a low score (Léo's floor); ``None``
        means every candidate was disqualified or the page held no email.
        """
        ranked = self.rank_candidates(page_text, name=name, city=city, website=website)
        return ranked[0][0] if ranked else None

    def rank_candidates(
        self, page_text: str, *, name: str, city: str, website: str | None = None
    ) -> list[tuple[str, float]]:
        """Disqualify then score every email of *page_text*, best first.

        Returned as ``(email, score)`` pairs — exposed for tests and diagnostics.
        Ties keep the page's reading order (first occurrence wins).
        """
        if not page_text:
            return []

        text_lower = page_text.lower()
        first_seen: dict[str, int] = {}
        positions: dict[str, list[int]] = {}
        for match in _EMAIL_PATTERN.finditer(text_lower):
            email = match.group(0)
            if email not in first_seen:
                first_seen[email] = match.start()
                positions[email] = []
            positions[email].append(match.start())

        if not first_seen:
            return []

        city_key = self._alnum(city)
        website_label = self._website_label(website)
        name_tokens = {token for token in company_tokens(name) if len(token) >= 4}
        name_positions = self._name_positions(text_lower, name_tokens)

        scored: list[tuple[str, float]] = []
        for email in first_seen:
            if self._is_disqualified(email, city_key):
                continue
            score = self._positive_score(
                email,
                positions[email],
                name_tokens=name_tokens,
                website_label=website_label,
                name_positions=name_positions,
            )
            scored.append((email, score))

        scored.sort(key=lambda pair: (-pair[1], first_seen[pair[0]]))
        return scored

    def _is_disqualified(self, email: str, city_key: str) -> bool:
        """True when *email* provably belongs to a non-prospect (the only hard reject)."""
        local, _, domain = email.partition("@")
        if not domain:
            return True
        if any(local.startswith(prefix) for prefix in BLOCKED_LOCAL_PREFIXES):
            return True
        if self._is_blocked_domain(domain):
            return True
        if any(chunk in domain for chunk in BLOCKED_DOMAIN_SUBSTRINGS):
            return True
        if any(pattern.search(domain) for pattern in BLOCKED_DOMAIN_PATTERNS):
            return True
        # Domain that IS the city name (town hall / office), never on a generic provider.
        return bool(
            domain not in GENERIC_EMAIL_PROVIDERS
            and city_key
            and self._alnum(self._registrable_label(domain)) == city_key
        )

    def _positive_score(
        self,
        email: str,
        occurrences: list[int],
        *,
        name_tokens: set[str],
        website_label: str,
        name_positions: list[int],
    ) -> float:
        """Positive-only score: ownership signals raise it, nothing lowers it."""
        local, _, domain = email.partition("@")
        label = self._registrable_label(domain)
        is_generic = domain in GENERIC_EMAIL_PROVIDERS

        score = 1.0  # base: keep every survivor in the race for the floor rule
        if website_label and label and not is_generic and website_label == label:
            score += 100.0
        if name_tokens and any(token in label for token in name_tokens):
            score += 40.0
        if name_tokens and any(token in local for token in name_tokens):
            score += 25.0
        score += self._proximity_score(occurrences, name_positions)
        if local in ROLE_LOCAL_PARTS:
            score += 5.0
        return score

    def _name_positions(self, text_lower: str, name_tokens: set[str]) -> list[int]:
        """Sorted start offsets of every business-name token occurrence in the page."""
        offsets: list[int] = []
        for token in name_tokens:
            offsets.extend(match.start() for match in re.finditer(re.escape(token), text_lower))
        offsets.sort()
        return offsets

    def _proximity_score(self, occurrences: list[int], name_positions: list[int]) -> float:
        """Up to +30 the closer the email sits to a business-name mention."""
        if not occurrences or not name_positions:
            return 0.0
        best_distance = min(self._nearest_distance(position, name_positions) for position in occurrences)
        return 30.0 * max(0.0, 1.0 - best_distance / _PROXIMITY_REACH_CHARS)

    @staticmethod
    def _nearest_distance(position: int, sorted_positions: list[int]) -> int:
        """Char distance from *position* to the nearest offset in *sorted_positions*."""
        index = bisect_left(sorted_positions, position)
        candidates: list[int] = []
        if index < len(sorted_positions):
            candidates.append(abs(sorted_positions[index] - position))
        if index > 0:
            candidates.append(abs(position - sorted_positions[index - 1]))
        return min(candidates) if candidates else _PROXIMITY_REACH_CHARS

    @staticmethod
    def _alnum(value: str) -> str:
        """Fold *value* (accent-strip + lowercase) then keep only ``[a-z0-9]``."""
        return re.sub(r"[^a-z0-9]", "", fold(value))

    @staticmethod
    def _is_blocked_domain(domain: str) -> bool:
        """Whether *domain* is a known directory / platform domain or one of its subdomains (``tel.search.ch``)."""
        labels = domain.split(".")
        return any(".".join(labels[index:]) in BLOCKED_DOMAINS for index in range(len(labels) - 1))

    @staticmethod
    def _registrable_label(domain: str) -> str:
        """Label registered before the suffix, ``.fr`` as ``.qc.ca`` (``plomberie-tremblay`` in ``plomberie-tremblay.qc.ca``)."""
        parts = [part for part in domain.lower().split(".") if part]
        has_canadian_second_level_suffix = len(parts) >= 3 and ".".join(parts[-2:]) in _CANADIAN_SECOND_LEVEL_SUFFIXES
        suffix_length = 2 if has_canadian_second_level_suffix else 1
        if len(parts) > suffix_length:
            return parts[-suffix_length - 1]
        return parts[0] if parts else ""

    @classmethod
    def _website_label(cls, website: str | None) -> str:
        """Registrable label of a website URL, stripping scheme and ``www.``."""
        if not website:
            return ""
        candidate = website.strip()
        if "//" not in candidate:
            candidate = "//" + candidate
        host = (urlparse(candidate).hostname or "").lower()
        host = host.removeprefix("www.")
        return cls._registrable_label(host)


email_candidate_scorer = EmailCandidateScorer()
