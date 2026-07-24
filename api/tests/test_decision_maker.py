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
)
from services.decision_maker.types import NameCandidate, ResolutionContext

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


def test_agreement_between_sources_boosts_confidence() -> None:
    """Two independent sources agreeing push a borderline candidate over the bar."""
    resolver = DecisionMakerResolver(strategies=[])
    candidates = [
        NameCandidate(first="Michel", last="Dubois", source="registre_gouv", confidence=0.6),
        NameCandidate(first="Michel", last=None, source="owner_response", confidence=0.55),
    ]
    best = resolver.pick_best(candidates)
    assert best is not None
    assert best.first == "Michel"
    assert best.confidence >= 0.7


def test_below_threshold_yields_none() -> None:
    """A single weak candidate is rejected — neutral greeting instead."""
    resolver = DecisionMakerResolver(strategies=[])
    assert resolver.pick_best([NameCandidate(first="Paul", source="llm_aggregate", confidence=0.6)]) is None


def test_top_level_disagreement_yields_none() -> None:
    """Two different identities tied at the top → trust neither."""
    resolver = DecisionMakerResolver(strategies=[])
    candidates = [
        NameCandidate(first="Michel", last="Dubois", source="registre_gouv", confidence=0.8),
        NameCandidate(first="Paul", last="Martin", source="pappers", confidence=0.8),
    ]
    assert resolver.pick_best(candidates) is None


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
