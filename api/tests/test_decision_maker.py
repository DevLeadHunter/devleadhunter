"""
Unit tests for the decision-maker name cascade — greeting rules, name
normalisation, registry parsing and the resolver's confidence/agreement logic.
All offline: strategy parsers are exercised on fixtures, never the network.
"""

from services.decision_maker.greeting import build_greeting
from services.decision_maker.normalize import (
    company_similarity,
    infer_gender,
    split_registry_full_name,
    title_case_name,
)
from services.decision_maker.resolver import DecisionMakerResolver
from services.decision_maker.strategies import (
    LegalMentionsStrategy,
    LlmAggregateStrategy,
    OwnerResponseStrategy,
    RegistreGouvStrategy,
    WebRegistryStrategy,
)
from services.decision_maker.types import NameCandidate, NameResolution, ResolutionContext

# ── Greeting rules (Léo's decisions) ─────────────────────────────────────────


def test_greeting_first_name_only_even_when_last_known() -> None:
    """First name known → « Bonjour Léo » — NEVER first+last (mail-merge feel)."""
    assert build_greeting("Léo", "Guillaume", "M") == "Bonjour Léo"
    assert build_greeting("Léo", None, None) == "Bonjour Léo"


def test_greeting_nothing_known_is_neutral() -> None:
    """No trusted name → plain « Bonjour » (never a company word)."""
    assert build_greeting(None, None, None) == "Bonjour"
    assert build_greeting("", "", None) == "Bonjour"


def test_greeting_last_name_needs_a_sure_gender() -> None:
    """Last name only: civility ONLY when the gender is known, else neutral."""
    assert build_greeting(None, "Guillaume", "M") == "Bonjour M. Guillaume"
    assert build_greeting(None, "Guillaume", "F") == "Bonjour Mme Guillaume"
    assert build_greeting(None, "Guillaume", None) == "Bonjour"


def test_greeting_normalises_registry_uppercase() -> None:
    """Registry UPPERCASE input renders as clean title-case."""
    assert build_greeting("LÉO", None, None) == "Bonjour Léo"
    assert build_greeting(None, "GUILLAUME", "M") == "Bonjour M. Guillaume"


# ── Normalisation ────────────────────────────────────────────────────────────


def test_title_case_handles_particles_and_hyphens() -> None:
    """Particles stay lowercase; hyphenated names capitalize each part."""
    assert title_case_name("jean-pierre") == "Jean-Pierre"
    assert title_case_name("DE LA TOUR") == "De la Tour"


def test_split_registry_full_name_ei_pattern() -> None:
    """« NOM Prénom » (EI denomination) splits into (first, last)."""
    first, last = split_registry_full_name("GUILLAUME Léo")
    assert (first, last) == ("Léo", "Guillaume")


def test_split_registry_full_name_drops_parenthesized_brand() -> None:
    """« LESNE Geoffrey (LESNE SERVICE) » ignores the parenthesized brand."""
    first, last = split_registry_full_name("LESNE Geoffrey (LESNE SERVICE)")
    assert (first, last) == ("Geoffrey", "Lesne")


def test_infer_gender_is_conservative() -> None:
    """Known first names resolve; unknown ones yield None (→ neutral greeting)."""
    assert infer_gender("Léo") == "M"
    assert infer_gender("Marie") == "F"
    assert infer_gender("Xxyyzz") is None


def test_company_similarity_ignores_legal_noise() -> None:
    """Legal forms (SARL…) don't count as matching tokens."""
    assert company_similarity("SARL Dubois Plomberie", "DUBOIS PLOMBERIE") == 1.0
    assert company_similarity("Plomberie Dubois", "Boulangerie Martin") == 0.0


# ── Registry parsing ─────────────────────────────────────────────────────────


def _context() -> ResolutionContext:
    return ResolutionContext(company_name="Plomberie Dubois", city="Rennes", postal_code="35000")


def test_registre_ei_gets_high_confidence() -> None:
    """An EI whose denomination carries the person's name scores above threshold."""
    results = [
        {
            "nom_complet": "DUBOIS Michel (PLOMBERIE DUBOIS)",
            "nom_raison_sociale": "PLOMBERIE DUBOIS",
            "nature_juridique": "1000",
            "siren": "123456789",
            "siege": {"code_postal": "35000", "libelle_commune": "RENNES"},
            "dirigeants": [
                {"nom": "DUBOIS", "prenoms": "Michel", "qualite": "", "type_dirigeant": "personne physique"}
            ],
        }
    ]
    candidates = RegistreGouvStrategy().parse_results(results, _context())
    assert len(candidates) == 1
    assert candidates[0].first == "Michel"
    assert candidates[0].last == "Dubois"
    assert candidates[0].confidence >= 0.8
    assert candidates[0].primary is True
    assert candidates[0].geo_confirmed is True
    assert "SIREN 123456789" in candidates[0].provenance


def test_registre_department_counts_as_geo_confirmation() -> None:
    """An HQ one commune away (same département) still confirms the location."""
    results = [
        {
            "nom_complet": "DUBOIS Michel",
            "nom_raison_sociale": "PLOMBERIE DUBOIS",
            "nature_juridique": "1000",
            "siren": "123456789",
            "siege": {"code_postal": "35400", "libelle_commune": "SAINT-MALO"},
            "dirigeants": [
                {"nom": "DUBOIS", "prenoms": "Michel", "qualite": "", "type_dirigeant": "personne physique"}
            ],
        }
    ]
    candidates = RegistreGouvStrategy().parse_results(results, _context())
    assert candidates[0].geo_confirmed is True


def test_registre_other_department_is_not_geo_confirmed() -> None:
    """The seed-test homonym: same name, another département → no geo confirmation."""
    results = [
        {
            "nom_complet": "DUBOIS Michel",
            "nom_raison_sociale": "PLOMBERIE DUBOIS",
            "nature_juridique": "1000",
            "siren": "987654321",
            "siege": {"code_postal": "59000", "libelle_commune": "LILLE"},
            "dirigeants": [
                {"nom": "DUBOIS", "prenoms": "Michel", "qualite": "", "type_dirigeant": "personne physique"}
            ],
        }
    ]
    candidates = RegistreGouvStrategy().parse_results(results, _context())
    assert candidates[0].geo_confirmed is False
    assert candidates[0].confidence >= 0.8  # still a strong-name match…
    resolution = DecisionMakerResolver(strategies=[]).pick_best(candidates)
    assert resolution.status == NameResolution.PROPOSED  # …but never used alone


def test_registre_multi_dirigeants_scores_below_solo() -> None:
    """Ambiguous multi-director companies are scored lower (golden rule)."""
    base = {
        "nom_complet": "PLOMBERIE DUBOIS",
        "nom_raison_sociale": "PLOMBERIE DUBOIS",
        "nature_juridique": "5498",
        "siren": "123456789",
        "siege": {"code_postal": "35000", "libelle_commune": "RENNES"},
    }
    solo = RegistreGouvStrategy().parse_results(
        [
            {
                **base,
                "dirigeants": [
                    {"nom": "DUBOIS", "prenoms": "Michel", "qualite": "Gérant", "type_dirigeant": "personne physique"}
                ],
            }
        ],
        _context(),
    )
    multi = RegistreGouvStrategy().parse_results(
        [
            {
                **base,
                "dirigeants": [
                    {"nom": "DUBOIS", "prenoms": "Michel", "qualite": "Gérant", "type_dirigeant": "personne physique"},
                    {"nom": "MARTIN", "prenoms": "Paul", "qualite": "Associé", "type_dirigeant": "personne physique"},
                ],
            }
        ],
        _context(),
    )
    assert solo[0].confidence > multi[0].confidence


def test_registre_rejects_unrelated_company() -> None:
    """A registry match with a different company name is discarded."""
    results = [
        {
            "nom_complet": "BOULANGERIE MARTIN",
            "nom_raison_sociale": "BOULANGERIE MARTIN",
            "nature_juridique": "1000",
            "siege": {},
            "dirigeants": [{"nom": "MARTIN", "prenoms": "Paul", "type_dirigeant": "personne physique"}],
        }
    ]
    assert RegistreGouvStrategy().parse_results(results, _context()) == []


# ── Signal extraction ────────────────────────────────────────────────────────


def test_legal_mentions_extracts_role_declaration() -> None:
    """« Gérant : Prénom Nom » on a legal page yields a candidate."""
    pages = ["<html><body><p>Mentions légales</p><p>Gérant : Michel Dubois</p></body></html>"]
    candidates = LegalMentionsStrategy().parse_pages(pages)
    assert len(candidates) == 1
    assert (candidates[0].first, candidates[0].last) == ("Michel", "Dubois")


def test_llm_answer_rejected_without_literal_quote() -> None:
    """The anti-hallucination gate discards answers whose quote is not in the corpus."""
    strategy = LlmAggregateStrategy()
    corpus = "Bienvenue chez Plomberie Dubois, votre artisan à Rennes."
    hallucinated = "PRENOM: Michel\nNOM: Dubois\nCITATION: Michel Dubois vous accueille"
    assert strategy.parse_answer(hallucinated, corpus) == []
    grounded_corpus = "Votre gérant Michel Dubois vous accueille du lundi au vendredi."
    grounded = "PRENOM: Michel\nNOM: Dubois\nCITATION: gérant Michel Dubois vous accueille"
    assert len(strategy.parse_answer(grounded, grounded_corpus)) == 1


# ── Resolver fusion rules ────────────────────────────────────────────────────


def _registry(first: str, last: str, confidence: float, geo_confirmed: bool) -> NameCandidate:
    return NameCandidate(
        first=first,
        last=last,
        source="registre_gouv",
        confidence=confidence,
        primary=True,
        geo_confirmed=geo_confirmed,
        evidence_group="registry",
    )


def test_agreement_between_independent_sources_boosts_confidence() -> None:
    """Two sources reading DIFFERENT documents agreeing boost each other."""
    resolver = DecisionMakerResolver(strategies=[])
    candidates = [
        NameCandidate(first="Michel", last="Dubois", source="registre_gouv", confidence=0.6, evidence_group="registry"),
        NameCandidate(first="Michel", source="owner_response", confidence=0.55, evidence_group="scraped_text"),
    ]
    resolution = resolver.pick_best(candidates)
    assert resolution.candidate is not None
    assert resolution.candidate.first == "Michel"
    assert resolution.candidate.confidence >= 0.7


def test_same_document_sources_never_corroborate_each_other() -> None:
    """The regex and the LLM both reading owner replies = ONE observation, no boost."""
    resolver = DecisionMakerResolver(strategies=[])
    candidates = [
        NameCandidate(first="Marie", source="owner_response", confidence=0.55, evidence_group="scraped_text"),
        NameCandidate(
            first="Marie", last="Petit", source="llm_aggregate", confidence=0.6, evidence_group="scraped_text"
        ),
    ]
    resolution = resolver.pick_best(candidates)
    assert resolution.status == NameResolution.PROPOSED
    assert resolution.candidate is not None
    assert resolution.candidate.confidence == 0.6  # untouched — no fake independence


def test_supporting_sources_alone_never_reach_auto() -> None:
    """Whatever their stacked confidence, non-primary sources stay proposals."""
    resolver = DecisionMakerResolver(strategies=[])
    candidates = [
        NameCandidate(first="Julien", last="Faure", source="legal_mentions", confidence=0.75, evidence_group="website"),
        NameCandidate(first="Julien", source="owner_response", confidence=0.7, evidence_group="scraped_text"),
    ]
    resolution = resolver.pick_best(candidates)
    assert resolution.status == NameResolution.PROPOSED
    assert resolution.candidate is not None
    assert resolution.candidate.confidence >= 0.85  # boosted, yet still not AUTO


def test_geo_confirmed_primary_reaches_auto() -> None:
    """Registry match + geo confirmation + threshold → used automatically."""
    resolver = DecisionMakerResolver(strategies=[])
    resolution = resolver.pick_best([_registry("Michel", "Dubois", 0.95, geo_confirmed=True)])
    assert resolution.status == NameResolution.AUTO
    assert resolution.candidate is not None
    assert resolution.candidate.first == "Michel"


def test_below_proposal_floor_yields_none() -> None:
    """A candidate under the proposal floor is dropped — neutral greeting."""
    resolver = DecisionMakerResolver(strategies=[])
    resolution = resolver.pick_best(
        [NameCandidate(first="Paul", source="llm_aggregate", confidence=0.5, evidence_group="scraped_text")]
    )
    assert resolution.status == NameResolution.NONE
    assert resolution.candidate is None


def test_weak_single_source_becomes_a_proposal_not_auto() -> None:
    """The old auto-or-nothing 0.7 bar: 0.6 now surfaces as a human-reviewed proposal."""
    resolver = DecisionMakerResolver(strategies=[])
    resolution = resolver.pick_best(
        [NameCandidate(first="Paul", source="llm_aggregate", confidence=0.6, evidence_group="scraped_text")]
    )
    assert resolution.status == NameResolution.PROPOSED


def test_top_level_disagreement_yields_none() -> None:
    """Two different identities tied at the top → trust neither."""
    resolver = DecisionMakerResolver(strategies=[])
    candidates = [
        NameCandidate(
            first="Michel",
            last="Dubois",
            source="registre_gouv",
            confidence=0.8,
            primary=True,
            evidence_group="registry",
        ),
        NameCandidate(
            first="Paul", last="Martin", source="pappers", confidence=0.8, primary=True, evidence_group="registry"
        ),
    ]
    resolution = resolver.pick_best(candidates)
    assert resolution.status == NameResolution.NONE


def test_homonym_from_another_department_cannot_rival_a_geo_confirmed_match() -> None:
    """Name-only registry noise is ignored once geography disambiguated the company."""
    resolver = DecisionMakerResolver(strategies=[])
    candidates = [
        _registry("Michel", "Dubois", 0.95, geo_confirmed=True),
        _registry("Paul", "Martin", 0.95, geo_confirmed=False),
    ]
    resolution = resolver.pick_best(candidates)
    assert resolution.status == NameResolution.AUTO
    assert resolution.candidate is not None
    assert resolution.candidate.first == "Michel"


def test_two_geo_confirmed_primaries_disagreeing_yield_none() -> None:
    """Two authoritative geo-anchored identities → genuine ambiguity, trust neither."""
    resolver = DecisionMakerResolver(strategies=[])
    candidates = [
        _registry("Michel", "Dubois", 0.9, geo_confirmed=True),
        NameCandidate(
            first="Paul",
            last="Martin",
            source="pappers",
            confidence=0.85,
            primary=True,
            geo_confirmed=True,
            evidence_group="registry",
        ),
    ]
    resolution = resolver.pick_best(candidates)
    assert resolution.status == NameResolution.NONE


def test_supporting_contradiction_demotes_auto_to_proposed() -> None:
    """A legal page naming someone else (the web agency?) forces a human look."""
    resolver = DecisionMakerResolver(strategies=[])
    candidates = [
        _registry("Michel", "Dubois", 0.9, geo_confirmed=True),
        NameCandidate(first="Jean", last="Agence", source="legal_mentions", confidence=0.75, evidence_group="website"),
    ]
    resolution = resolver.pick_best(candidates)
    assert resolution.status == NameResolution.PROPOSED
    assert resolution.candidate is not None
    assert resolution.candidate.first == "Michel"  # the registry keeps the lead


def test_all_candidates_are_kept_for_persistence() -> None:
    """Every merged candidate survives in the resolution (drawer + calibration)."""
    resolver = DecisionMakerResolver(strategies=[])
    candidates = [
        _registry("Michel", "Dubois", 0.9, geo_confirmed=True),
        NameCandidate(first="Marie", source="owner_response", confidence=0.55, evidence_group="scraped_text"),
    ]
    resolution = resolver.pick_best(candidates)
    assert len(resolution.candidates) == 2


def test_owner_response_signature_detection() -> None:
    """A recurring signature in owner replies becomes a first-name candidate."""
    import asyncio

    context = ResolutionContext(
        company_name="Plomberie Dubois",
        owner_responses=["Merci pour votre confiance !\n— Michel", "À bientôt,\nMichel"],
    )
    candidates = asyncio.run(OwnerResponseStrategy().resolve(context))
    assert len(candidates) == 1
    assert candidates[0].first == "Michel"
    assert candidates[0].confidence >= 0.7


def test_web_registry_extracts_legal_name_sharing_a_token() -> None:
    """Only all-caps runs sharing a token with the trade name survive (city dropped)."""
    html = (
        "<h3>Société GERMAIN SECOMAN</h3>"
        "<span>279 RUE DE GUETTELOUP, 72100 LE MANS</span>"
        "<p>Germain Paysagiste &amp; Élagage à Le Mans</p>"
    )
    names = WebRegistryStrategy(client=object()).extract_company_names(html, "Germain Paysagiste Élagage Espaces Verts")
    assert "GERMAIN SECOMAN" in names
    assert "LE MANS" not in names
    assert not any("GUETTELOUP" in name for name in names)


def test_web_registry_recovers_legal_name_then_delegates_to_registry() -> None:
    """SERP → recovered legal name → registry sub-lookup, retagged as web-sourced."""
    import asyncio

    class StubClient:
        is_configured = True

        async def google(self, query: str, *, num: int = 20) -> str:
            return "<h3>Société GERMAIN SECOMAN</h3><span>72100 LE MANS</span>"

    class StubRegistry:
        def __init__(self) -> None:
            self.calls: list[ResolutionContext] = []

        async def resolve(self, context: ResolutionContext) -> list[NameCandidate]:
            self.calls.append(context)
            if context.company_name != "GERMAIN SECOMAN":
                return []
            return [
                NameCandidate(
                    first="Germain",
                    last="Secoman",
                    source="registre_gouv",
                    confidence=0.95,
                    primary=True,
                    geo_confirmed=True,
                    evidence_group="registry",
                    provenance="Registre officiel (SIRENE) : SECOMAN GERMAIN, SIREN 431285493 — localisation confirmée",
                )
            ]

    registry = StubRegistry()
    strategy = WebRegistryStrategy(registry=registry, client=StubClient())
    context = ResolutionContext(company_name="Germain Paysagiste", city="Le Mans", postal_code="72000")

    resolved = asyncio.run(strategy.resolve(context))

    assert len(resolved) == 1
    candidate = resolved[0]
    assert (candidate.first, candidate.last) == ("Germain", "Secoman")
    assert candidate.source == "web_registry"
    assert candidate.primary and candidate.geo_confirmed
    assert candidate.provenance.startswith("Recherche web →")
    # The registry was queried with the RECOVERED legal name and without the strict postal filter.
    assert any(call.company_name == "GERMAIN SECOMAN" and call.postal_code is None for call in registry.calls)
