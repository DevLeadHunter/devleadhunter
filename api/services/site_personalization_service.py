"""
Automatic personalisation of a demo site: the business's own words and photos instead of the template's.

From the prospect's real data (description, services listed, reviews) and the labels of its own photos, a text
model writes the hero sentence, the « À propos », the service cards and the realizations, and picks the photo of
every slot: hero, « À propos », cards, realizations and the template's other photos. Everything it answers is
checked here: a slot only takes a showable photo of the business (never a flyer, a customer or a photo without
subject), each photo is used once when possible, lengths are capped, there is no em dash, and a sentence promising
what the data never says (« gratuit », « garanti », « 24h/24 », a number of years…) is dropped. The badge, the
facts under the title and the rating sentence are computed, never written by the model.

Craft trades only (every template but food, whose dish cards have their own flow): the result is stored as the
site's overrides by :mod:`services.demo_site_service`, so it survives every regeneration and stays editable.
"""

from __future__ import annotations

import json
import logging
import re
from dataclasses import dataclass, field
from typing import Any

from core.config import settings
from services.llm_service import llm_service
from services.mistral_service import MistralRequestRejectedError, mistral_service
from services.photo_labels import (
    CRAFT_KIND_PREMISES,
    CRAFT_KIND_TEAM,
    CRAFT_KIND_WORK,
    has_text_overlay,
    is_showable_craft_photo,
    rank_craft_photos,
)
from services.regional_lexicon import RegionalLexicon
from services.templates import registry as template_registry
from services.templates.site_content import experience_years_from_text

logger = logging.getLogger(__name__)

MAX_HERO_SENTENCE_CHARS = 110
MAX_ABOUT_CHARS = 600
MAX_CARD_TITLE_CHARS = 40
MAX_CARD_DESCRIPTION_CHARS = 150
MAX_PORTFOLIO_TITLE_CHARS = 80
MAX_BADGE_CHARS = 30
MAX_HERO_POINT_CHARS = 28
MAX_HERO_POINTS = 3
MIN_CARDS = 3
MAX_CARDS = 8
MIN_WORK_PHOTOS_FOR_PORTFOLIO = 3
RATING_FLOOR_FOR_PRAISE = 4.5
REVIEWS_FLOOR_FOR_PRAISE = 5
PORTFOLIO_CATEGORIES: tuple[str, ...] = (
    "Création",
    "Aménagement",
    "Entretien",
    "Rénovation",
    "Installation",
    "Réparation",
    "Terrasse",
    "Clôture",
    "Plantation",
    "Déneigement",
)
_MAX_REVIEWS_IN_PROMPT = 10
_MAX_REVIEW_CHARS = 400
_MAX_DESCRIPTION_IN_PROMPT = 1200
_DEFAULT_HERO_KINDS: tuple[str, ...] = (CRAFT_KIND_WORK, CRAFT_KIND_PREMISES, CRAFT_KIND_TEAM)
_ABOUT_PHOTO_KINDS: tuple[str, ...] = (CRAFT_KIND_TEAM, CRAFT_KIND_PREMISES, CRAFT_KIND_WORK)
_PORTFOLIO_PHOTO_KINDS: tuple[str, ...] = (CRAFT_KIND_WORK,)
_DASHES_RE = re.compile(r"\s*[—–]\s*")
_EXCLAMATION_RE = re.compile(r"\s*!")
_EMOJI_RE = re.compile(r"[\U0001F300-\U0001FAFF☀-➿️]")
_SENTENCE_END_RE = re.compile(r"(?<=[.!?])\s+")
_CUSTOMER_TALK_RE = re.compile(r"\bclient", re.IGNORECASE)
# Words a cut sentence must not end on (« … avec des livrées et des »).
_DANGLING_WORDS: frozenset[str] = frozenset(
    {"à", "au", "aux", "avec", "comme", "dans", "de", "des", "du", "en", "et", "la", "le", "les", "ou", "par"}
    | {"pour", "sans", "sur", "un", "une", "votre", "vos", "d'", "l'"}
)
_MIN_REVIEWS_TO_QUOTE_CUSTOMERS = 2
# A promise the business must have made itself: kept only when the data holds the same words.
_UNSUPPORTED_CLAIM_RES: tuple[re.Pattern[str], ...] = tuple(
    re.compile(pattern, re.IGNORECASE)
    for pattern in (
        r"\bgratuit\w*",
        r"\boffert\w*",
        r"\bgaranti\w*",
        r"\b24\s*h\b|\b24\s*h\s*/\s*24\b",
        r"\b7\s*j\s*/\s*7\b|\b7\s*jours\s*sur\s*7\b",
        r"\burgence\w*",
        r"\bcertifi\w*",
        r"\bagré\w*",
        r"\bassurance\w*|\bassuré[es]*\b",
        r"\bmeilleur\w*",
        r"\brapide\w*",
        r"\bdepuis\s+(?:plus\s+de\s+)?(?:\d+|plusieurs|de\s+nombreuses)",
        r"\b\d+\s*(?:ans|années)\b",
        r"\b\d+\s*(?:€|euros?|chf|\$)",
    )
)

_SYSTEM_PROMPT = """Tu écris le contenu du site web d'une entreprise, à partir de ses VRAIES données (fiche Google,
avis, description, prestations citées) et de l'inventaire de SES photos. Le patron doit reconnaître SON entreprise :
le moins possible de contenu générique.

Règles absolues :
- Que du vrai : chaque affirmation vient des données ou d'une photo. Aucune promesse absente des données : pas de
  « gratuit », « offert », « garanti », « 24h/24 », « 7j/7 », « urgence », « rapide », « certifié », « agréé »,
  « assuré », aucun chiffre, prix, année ou durée qui n'est pas dans les données, pas de « depuis plusieurs
  années ». Sans avis clients, ne dis rien de ce que pensent les clients.
- Pas de tiret cadratin, pas de point d'exclamation, pas d'émoji, pas de note Google (elle est ajoutée ailleurs).
- Pas de mots creux de publicité : « sublimer », « passion », « savoir-faire », « professionnalisme », « excellence »,
  « expertise », « à votre écoute », « n'hésitez pas », « de qualité ». Des faits simples à la place.
- Québec (pays CA) : français du Québec (« soumission » jamais « devis », « courriel », « cellulaire »,
  « panneau électrique » jamais « tableau électrique », « entrepreneur » plutôt qu'« artisan »). France et Suisse :
  français neutre.
- Les photos se désignent par leur numéro « n » de l'inventaire ; 0 = aucune photo. Une photo dont « texte » vaut
  true (légende, logo, coordonnées) ne va que sur une carte, jamais en en-tête, à propos, réalisation ou emplacement.

Réponds UNIQUEMENT par un objet JSON avec ces clés :
- "accroche_metier" : comment l'entreprise se présente, en un ou deux mots (« Paysagiste », « Carrosserie »,
  « Électricien », « Garage »).
- "accroche_prestations" : les 3 prestations les plus caractéristiques de CETTE entreprise, 2 à 4 mots chacune, en
  minuscules (« taille de haies », « pose de clôtures », « aménagement de jardins »).
- "a_propos" : 2 ou 3 phrases, 450 caractères maximum. À la première personne : « je » si le patron est connu
  (« Je suis {Prénom Nom} et je tiens {Entreprise} à {Ville}. »), sinon « nous ». Ce que fait l'entreprise (ses
  vraies spécialités) et ce que ses clients disent d'elle d'après les avis, sans citer de client.
- "photo_entete" : la photo la plus forte (un travail fini, ou les locaux pour un garage), nette et lumineuse.
- "photo_a_propos" : une autre photo, de préférence l'équipe, les locaux ou un travail.
- "prestations" : exactement N_prestations cartes. Les vraies prestations de l'entreprise d'abord, avec ses mots ;
  puis, pour compléter, des prestations_du_metier. Chaque carte : "titre" (40 caractères maximum), "description" (une
  phrase courte de 120 caractères maximum : ce que le client y gagne, simplement), "photo" (une photo qui montre CETTE
  prestation, différente pour chaque carte et des photos d'en-tête et d'à propos quand c'est possible ; 0 si aucune).
- "realisations" : exactement R_realisations éléments (liste vide si R_realisations vaut 0). Chaque élément :
  "photo" (un travail fini, pas encore utilisé si possible) et "categorie" (le mot de categories_realisations qui
  décrit cette photo).
- "emplacements" : pour chaque clé d'emplacements, le numéro d'une bonne photo pas encore utilisée, ou 0.
"""


@dataclass(frozen=True)
class TemplatePersonalizationProfile:
    """What a template lets the personalisation fill.

    Attributes:
        default_cards: The template's own service grid (title, description), the count to reach and the trade's
            core services to complete it with.
        portfolio_count: How many realizations the template shows (0 when it has no realizations section).
        image_slots: The template's other photos, field → what the editor calls it.
        hero_kinds: The photo kinds that suit the hero best, most wanted first.
    """

    default_cards: list[dict[str, str]]
    portfolio_count: int
    image_slots: dict[str, str]
    hero_kinds: tuple[str, ...]


@dataclass(frozen=True)
class BusinessFacts:
    """The real data of a business the personalisation draws from.

    Attributes:
        business_name: Its name.
        trade: Its trade, as a client would say it (« paysagiste »).
        city: Its city, empty when unknown.
        country: ISO code of its country.
        boss_first_name: The trusted first name of its head, or None.
        boss_last_name: The trusted last name of its head, or None.
        description: What it says about itself.
        services_listed: The services its listings name.
        reviews: Its positive reviews' texts.
        rating: Its Google rating, or None.
        reviews_count: Its number of Google reviews, or None.
    """

    business_name: str
    trade: str
    city: str
    country: str
    boss_first_name: str | None = None
    boss_last_name: str | None = None
    description: str = ""
    services_listed: list[str] = field(default_factory=list)
    reviews: list[str] = field(default_factory=list)
    rating: float | None = None
    reviews_count: int | None = None

    @property
    def has_known_boss(self) -> bool:
        """Whether the head is known by first and last name (the « À propos » then says « je »)."""
        return bool(self.boss_first_name and self.boss_last_name)

    @property
    def deserves_praise(self) -> bool:
        """Whether the rating is high enough, on enough reviews, to be said on the site."""
        return (
            self.rating is not None
            and self.rating >= RATING_FLOOR_FOR_PRAISE
            and (self.reviews_count or 0) >= REVIEWS_FLOOR_FOR_PRAISE
        )

    def corpus(self) -> str:
        """Everything the business or its customers wrote, lower-cased: what a claim must be found in."""
        return " ".join([self.description, *self.services_listed, *self.reviews]).lower()


@dataclass
class SitePersonalization:
    """The personalised content of a site, ready to be stored as its overrides.

    Attributes:
        hero_sentence: The sentence under the title.
        about: The « À propos » text.
        hero_badge: The small label above the title.
        hero_points: Up to three facts under the title.
        photo_order: The site's photos, hero first and « À propos » second.
        service_cards: The service cards (title, description, photo URL or empty).
        portfolio: The realizations (photo URL, title, category).
        section_images: The template's other photos, field → photo URL.
    """

    hero_sentence: str
    about: str
    hero_badge: str
    hero_points: list[str]
    photo_order: list[str]
    service_cards: list[dict[str, str]]
    portfolio: list[dict[str, str]]
    section_images: dict[str, str]


def profile_for_template(template_id: str) -> TemplatePersonalizationProfile:
    """
    Read what a template lets the personalisation fill, from what it generates for a business without data.

    Args:
        template_id: The template.

    Returns:
        Its default cards, realizations count, other photo slots and hero photo preferences.
    """
    module = template_registry.get_module(template_id)
    blank = template_registry.build_site_content(
        template_id=template_id,
        business_name="Entreprise",
        phone="",
        email="",
        city="",
        area="",
        subtitle="",
        palette=template_registry.default_theme(template_id),
        enrichment={},
    )
    default_cards = [
        {"title": str(card.get("title", "")).strip(), "description": str(card.get("description", "")).strip()}
        for card in blank.get("services") or []
        if isinstance(card, dict) and str(card.get("title", "")).strip()
    ]
    used_sections: list[str] = list(getattr(module, "USED_SECTIONS", []) or [])
    portfolio = blank.get("portfolio") if "portfolio" in used_sections else None
    meta: dict[str, Any] = getattr(module, "TEMPLATE_META", {}) or {}
    hero_kinds = tuple(meta.get("hero_photo_kinds") or _DEFAULT_HERO_KINDS)
    return TemplatePersonalizationProfile(
        default_cards=default_cards,
        portfolio_count=len(portfolio) if isinstance(portfolio, list) else 0,
        image_slots=template_registry.section_image_slots(template_id),
        hero_kinds=hero_kinds,
    )


def clean_copy(text: Any, limit: int, *, is_sentence: bool = True) -> str:
    """
    Tidy a text the model wrote: one line, no em dash, no exclamation mark, no emoji, within ``limit``.

    A text too long is cut where it still reads whole: at its last comma (when that keeps half of it), else after
    its last full word, never on « de », « et », « avec »…; a cut sentence ends with a full stop.

    Args:
        text: The raw text.
        limit: The longest length allowed.
        is_sentence: Whether the text is a sentence (a title is cut without a full stop).

    Returns:
        The clean text, empty when there was none.
    """
    cleaned = " ".join(str(text or "").split())
    cleaned = _EXCLAMATION_RE.sub(".", _DASHES_RE.sub(", ", cleaned))
    cleaned = " ".join(_EMOJI_RE.sub("", cleaned).split())
    cleaned = cleaned.replace(" .", ".")
    if len(cleaned) <= limit:
        return cleaned
    head = cleaned[:limit]
    comma = head.rfind(",")
    if comma >= limit // 2:
        return f"{head[:comma]}." if is_sentence else head[:comma]
    words = head.rsplit(" ", 1)[0].rstrip(",;:").split(" ")
    while len(words) > 1 and words[-1].lower() in _DANGLING_WORDS:
        words.pop()
    shortened = " ".join(words).rstrip(",;:.")
    return f"{shortened}." if is_sentence else shortened


def without_unsupported_claims(text: str, corpus: str) -> str:
    """
    Drop every sentence that promises what the business never said (« gratuit », « garanti », a number of years…).

    Args:
        text: A text the model wrote.
        corpus: What the business and its customers wrote, lower-cased.

    Returns:
        The sentences whose promises are all found in the corpus.
    """
    kept: list[str] = []
    for sentence in _SENTENCE_END_RE.split(text.strip()):
        claims = [match.group(0).lower() for pattern in _UNSUPPORTED_CLAIM_RES for match in pattern.finditer(sentence)]
        if all(claim in corpus for claim in claims):
            kept.append(sentence)
    return " ".join(kept).strip()


def build_hero_sentence(trade: Any, city: str, services: Any, corpus: str) -> str:
    """
    The sentence under the title, « Paysagiste à Gland : taille de haies, pose de clôtures, aménagement de jardins. »

    Its three services come from the model; the ones promising what the data never says are dropped, and the last
    ones too while the sentence is longer than the template's line.

    Args:
        trade: How the business presents itself (« Carrosserie »), from the model.
        city: The business's city.
        services: Its most characteristic services, from the model.
        corpus: What the business and its customers wrote, lower-cased.

    Returns:
        The sentence, or empty when the model gave no trade or no usable service.
    """
    trade_words = clean_copy(trade, MAX_CARD_TITLE_CHARS, is_sentence=False).rstrip(".")
    raw_services = services if isinstance(services, list) else []
    kept: list[str] = []
    for service in raw_services[:3]:
        words = without_unsupported_claims(clean_copy(service, MAX_CARD_TITLE_CHARS, is_sentence=False), corpus)
        words = words.rstrip(".")
        if words and words.lower() not in (existing.lower() for existing in kept):
            kept.append(words[0].lower() + words[1:])
    if not trade_words or not kept:
        return ""
    lead = f"{trade_words[0].upper()}{trade_words[1:]} à {city}" if city else trade_words[0].upper() + trade_words[1:]
    while kept:
        sentence = f"{lead} : {', '.join(kept)}."
        if len(sentence) <= MAX_HERO_SENTENCE_CHARS:
            return sentence
        kept.pop()
    return ""


def hero_badge(facts: BusinessFacts) -> str:
    """
    The label above the title: the trade and the city, the trade alone when that is too long.

    Args:
        facts: The business's data.

    Returns:
        The badge, empty when the trade is unknown.
    """
    trade = facts.trade.strip()
    if not trade:
        return ""
    trade = trade[0].upper() + trade[1:]
    with_city = f"{trade} à {facts.city}" if facts.city else trade
    return with_city if len(with_city) <= MAX_BADGE_CHARS else trade[:MAX_BADGE_CHARS]


def hero_points(facts: BusinessFacts, card_titles: list[str]) -> list[str]:
    """
    Up to three facts under the title, all read from the data: rating, years in business, area, a real service.

    Args:
        facts: The business's data.
        card_titles: The service cards' titles, the business's own services first.

    Returns:
        The facts, each short enough for the template's chips.
    """
    points: list[str] = []
    if facts.deserves_praise and facts.rating is not None:
        points.append(f"{_french_rating(facts.rating)}/5 sur {facts.reviews_count} avis Google")
    years = experience_years_from_text(facts.description)
    if years:
        points.append(f"{years} ans d'expérience")
    if facts.city:
        points.append(f"{facts.city} et alentours")
    points = [point for point in points if len(point) <= MAX_HERO_POINT_CHARS]
    short_titles = [title for title in card_titles if len(title) <= MAX_HERO_POINT_CHARS]
    return (points + short_titles)[:MAX_HERO_POINTS]


def praise_sentence(facts: BusinessFacts) -> str:
    """
    The rating sentence closing the « À propos », in the voice of the text, when the rating deserves it.

    Args:
        facts: The business's data.

    Returns:
        « Mes clients me donnent 4,9 sur 5 sur Google. », or empty.
    """
    if not facts.deserves_praise or facts.rating is None:
        return ""
    rating = _french_rating(facts.rating)
    if facts.has_known_boss:
        return f"Mes clients me donnent {rating} sur 5 sur Google."
    return f"Nos clients nous donnent {rating} sur 5 sur Google."


def _french_rating(rating: float) -> str:
    """A rating written the French way, « 4,9 »."""
    return f"{rating:.1f}".replace(".", ",")


def _closest_default_description(title: str, profile: TemplatePersonalizationProfile) -> str:
    """The template's description of the default card sharing the most words with ``title``, empty when none does."""
    words = set(re.findall(r"\w{4,}", title.lower()))
    best_description = ""
    best_overlap = 0
    for card in profile.default_cards:
        overlap = len(words & set(re.findall(r"\w{4,}", card["title"].lower())))
        if overlap > best_overlap:
            best_overlap, best_description = overlap, card["description"]
    return best_description


class _PhotoChooser:
    """Hands out the business's showable photos to the site's slots, each photo once while some are left."""

    def __init__(self, inventory: list[str], labels: dict[str, dict[str, Any]], pool: list[str]) -> None:
        self._inventory = inventory
        self._labels = labels
        self._pool = pool
        self.used: set[str] = set()

    def _is_certain(self, url: str) -> bool:
        """Whether the vision read the photo and found no text on it (a caption, a logo, a phone number)."""
        label = self._labels.get(url)
        return label is not None and not has_text_overlay(label)

    def by_number(self, number: Any, *, allow_uncertain: bool) -> str:
        """The unused showable photo the model named by its inventory number, or empty."""
        try:
            index = int(number) - 1
        except (TypeError, ValueError):
            return ""
        if not 0 <= index < len(self._inventory):
            return ""
        url = self._inventory[index]
        if url in self.used or not (allow_uncertain or self._is_certain(url)):
            return ""
        return url

    def best(self, kinds: tuple[str, ...], *, allow_uncertain: bool) -> str:
        """The best unused showable photo for a slot wanting these kinds, or empty."""
        ranked = rank_craft_photos(self._pool, self._labels, preferred_kinds=kinds, exclude=self.used)
        usable = [url for url in ranked if allow_uncertain or self._is_certain(url)]
        return usable[0] if usable else ""

    def take(self, number: Any, kinds: tuple[str, ...], *, fallback: bool = True, allow_uncertain: bool = False) -> str:
        """
        The photo the model chose when it is usable, else the best one for the slot; marked used.

        Args:
            number: The inventory number the model gave.
            kinds: The kinds that suit the slot, most wanted first.
            fallback: Whether to pick the best photo when the model's choice is not usable.
            allow_uncertain: Whether a photo carrying text, or one the vision did not read, may take the slot.

        Returns:
            The photo's URL, or empty when none fits.
        """
        url = self.by_number(number, allow_uncertain=allow_uncertain) or (
            self.best(kinds, allow_uncertain=allow_uncertain) if fallback else ""
        )
        if url:
            self.used.add(url)
        return url

    def take_prominent(self, number: Any, kinds: tuple[str, ...]) -> str:
        """A photo for a slot everyone sees (hero, « À propos »): a clean one, an uncertain one only when none is left."""
        return self.take(number, kinds) or self.take(number, kinds, allow_uncertain=True)


def assemble_personalization(
    answer: dict[str, Any],
    *,
    facts: BusinessFacts,
    profile: TemplatePersonalizationProfile,
    pool: list[str],
    labels: dict[str, dict[str, Any]],
    inventory: list[str],
) -> SitePersonalization:
    """
    Turn the model's answer into a site's personalised content, checking every text and every photo.

    Args:
        answer: The model's JSON answer.
        facts: The business's data.
        profile: What the template lets the personalisation fill.
        pool: The site's photos, in their order.
        labels: The craft labels of the pool's photos.
        inventory: The showable photos as numbered for the model (number n = ``inventory[n - 1]``).

    Returns:
        The content to store, every text worded the way the business's country reads it.
    """
    corpus = facts.corpus()
    country = facts.country
    chooser = _PhotoChooser(inventory, labels, pool)

    hero_photo = chooser.take_prominent(answer.get("photo_entete"), profile.hero_kinds)
    about_photo = chooser.take_prominent(answer.get("photo_a_propos"), _ABOUT_PHOTO_KINDS)

    cards: list[dict[str, str]] = []
    card_count = max(MIN_CARDS, min(MAX_CARDS, len(profile.default_cards) or MIN_CARDS))
    raw_cards = answer.get("prestations") if isinstance(answer.get("prestations"), list) else []
    for raw in raw_cards:
        if not isinstance(raw, dict) or len(cards) >= card_count:
            continue
        title = clean_copy(raw.get("titre"), MAX_CARD_TITLE_CHARS, is_sentence=False)
        if not title or any(card["title"].lower() == title.lower() for card in cards):
            continue
        description = without_unsupported_claims(
            clean_copy(raw.get("description"), MAX_CARD_DESCRIPTION_CHARS), corpus
        ) or _closest_default_description(title, profile)
        if not description:
            continue
        image = chooser.take(raw.get("photo"), (CRAFT_KIND_WORK,), fallback=False, allow_uncertain=True)
        cards.append({"title": title, "description": description, "image": image})
    for default in profile.default_cards:
        if len(cards) >= card_count:
            break
        if any(card["title"].lower() == default["title"].lower() for card in cards):
            continue
        cards.append({"title": default["title"], "description": default["description"], "image": ""})

    portfolio: list[dict[str, str]] = []
    work_photos = [url for url in inventory if labels.get(url, {}).get("kind") == CRAFT_KIND_WORK]
    if profile.portfolio_count and len(work_photos) >= MIN_WORK_PHOTOS_FOR_PORTFOLIO:
        raw_items = answer.get("realisations") if isinstance(answer.get("realisations"), list) else []
        for raw in raw_items:
            if not isinstance(raw, dict) or len(portfolio) >= profile.portfolio_count:
                continue
            image = chooser.take(raw.get("photo"), _PORTFOLIO_PHOTO_KINDS)
            described = labels.get(image, {}).get("description")
            title = clean_copy(described, MAX_PORTFOLIO_TITLE_CHARS, is_sentence=False).rstrip(".")
            if not image or not title:
                continue
            category = str(raw.get("categorie") or "").strip()
            portfolio.append(
                {
                    "image": image,
                    "title": title,
                    "category": category if category in PORTFOLIO_CATEGORIES else PORTFOLIO_CATEGORIES[0],
                }
            )

    raw_slots = answer.get("emplacements") if isinstance(answer.get("emplacements"), dict) else {}
    section_images: dict[str, str] = {}
    for slot in profile.image_slots:
        url = chooser.take(raw_slots.get(slot), (CRAFT_KIND_WORK, CRAFT_KIND_PREMISES))
        if url:
            section_images[slot] = url

    about = without_unsupported_claims(clean_copy(answer.get("a_propos"), MAX_ABOUT_CHARS), corpus)
    if len(facts.reviews) < _MIN_REVIEWS_TO_QUOTE_CUSTOMERS:
        about = " ".join(
            sentence for sentence in _SENTENCE_END_RE.split(about) if not _CUSTOMER_TALK_RE.search(sentence)
        )
    praise = praise_sentence(facts)
    if about and praise:
        about = f"{about.rstrip('.')}. {praise}"

    first_photos = [url for url in (hero_photo, about_photo) if url]
    others = rank_craft_photos(pool, labels, preferred_kinds=(CRAFT_KIND_WORK,), exclude=set(first_photos))
    return SitePersonalization(
        hero_sentence=RegionalLexicon.localize(
            build_hero_sentence(answer.get("accroche_metier"), facts.city, answer.get("accroche_prestations"), corpus),
            country,
        ),
        about=RegionalLexicon.localize(about, country),
        hero_badge=RegionalLexicon.localize(hero_badge(facts), country),
        hero_points=[
            RegionalLexicon.localize(point, country) for point in hero_points(facts, [card["title"] for card in cards])
        ],
        photo_order=first_photos + others,
        service_cards=[
            {
                "title": RegionalLexicon.localize(card["title"], country),
                "description": RegionalLexicon.localize(card["description"], country),
                "image": card["image"],
            }
            for card in cards
        ],
        portfolio=[{**item, "title": RegionalLexicon.localize(item["title"], country)} for item in portfolio],
        section_images=section_images,
    )


def personalization_prompt_facts(
    facts: BusinessFacts,
    profile: TemplatePersonalizationProfile,
    inventory: list[str],
    labels: dict[str, dict[str, Any]],
) -> dict[str, Any]:
    """
    The facts handed to the model: the business's data, its numbered photos and what the template expects.

    Args:
        facts: The business's data.
        profile: What the template lets the personalisation fill.
        inventory: The showable photos, numbered from 1 in this order.
        labels: Their craft labels.

    Returns:
        The JSON-ready facts.
    """
    return {
        "entreprise": facts.business_name,
        "metier": facts.trade,
        "ville": facts.city,
        "pays": facts.country,
        "patron": ({"prenom": facts.boss_first_name, "nom": facts.boss_last_name} if facts.has_known_boss else None),
        "description": facts.description[:_MAX_DESCRIPTION_IN_PROMPT],
        "prestations_citees": facts.services_listed,
        "avis": [review[:_MAX_REVIEW_CHARS] for review in facts.reviews[:_MAX_REVIEWS_IN_PROMPT]],
        "photos": [
            {
                "n": number,
                "type": labels[url].get("kind", ""),
                "description": labels[url].get("description", ""),
                "prestations": labels[url].get("services") or [],
                "texte": has_text_overlay(labels[url]),
                "qualite": labels[url].get("appeal", 0),
            }
            for number, url in enumerate(inventory, start=1)
        ],
        "N_prestations": max(MIN_CARDS, min(MAX_CARDS, len(profile.default_cards) or MIN_CARDS)),
        "prestations_du_metier": [card["title"] for card in profile.default_cards],
        "R_realisations": profile.portfolio_count,
        "categories_realisations": list(PORTFOLIO_CATEGORIES),
        "emplacements": profile.image_slots,
    }


class SitePersonalizationService:
    """Writes a craft business's site content from its data and its labelled photos."""

    @property
    def is_available(self) -> bool:
        """True when a Mistral or a Groq key is configured."""
        return mistral_service.is_configured or llm_service.is_configured

    async def personalize(
        self,
        *,
        facts: BusinessFacts,
        template_id: str,
        pool: list[str],
        labels: dict[str, dict[str, Any]],
    ) -> SitePersonalization | None:
        """
        Compose a site's personalised content.

        Args:
            facts: The business's data.
            template_id: The site's template.
            pool: The site's photos, in their order.
            labels: The craft labels of those photos (a photo without one is never chosen by the model).

        Returns:
            The content, or None when no model answered.
        """
        if not self.is_available:
            return None
        profile = profile_for_template(template_id)
        inventory = [url for url in pool if is_showable_craft_photo(labels.get(url))]
        prompt_facts = personalization_prompt_facts(facts, profile, inventory, labels)
        answer = await self._compose(prompt_facts)
        if answer is None:
            logger.warning("Site personalisation: no model answered for %s", facts.business_name)
            return None
        return assemble_personalization(
            answer, facts=facts, profile=profile, pool=pool, labels=labels, inventory=inventory
        )

    @staticmethod
    async def _compose(prompt_facts: dict[str, Any]) -> dict[str, Any] | None:
        """Ask Mistral for the content, Groq when Mistral does not answer; None when neither does."""
        messages: list[dict[str, Any]] = [
            {"role": "system", "content": _SYSTEM_PROMPT},
            {"role": "user", "content": json.dumps(prompt_facts, ensure_ascii=False)},
        ]
        if mistral_service.is_configured:
            try:
                completion = await mistral_service.complete(
                    messages,
                    model=settings.mistral_chat_model,
                    max_tokens=3000,
                    temperature=0.3,
                    json_mode=True,
                    timeout=90.0,
                    retries=1,
                )
            except MistralRequestRejectedError as exc:
                logger.warning("Mistral refused a site personalisation call: %s", exc)
                completion = None
            answer = llm_service.parse_json_object(completion.text) if completion is not None else None
            if answer is not None:
                return answer
        if not llm_service.is_configured:
            return None
        return await llm_service.complete_json(messages, max_tokens=4000, temperature=0.3, timeout=120.0)


site_personalization_service = SitePersonalizationService()
