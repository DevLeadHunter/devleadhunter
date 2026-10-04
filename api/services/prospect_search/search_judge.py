"""
Search judge — a language model reading search results the rules cannot settle.

The judge never supplies a fact from memory: it is shown the result lines of one
search about one business and answers closed questions about them (is one of these
its own website, is it a chain, whose email is this). Every answer it gives points
at the result it was read on, and an answer that cannot be found back in that result
is dropped.
"""

from __future__ import annotations

import logging
import re
from dataclasses import dataclass, field
from typing import Any

from services.decision_maker.normalize import fold
from services.llm_service import llm_service

logger = logging.getLogger(__name__)

_EMAIL_RE: re.Pattern[str] = re.compile(r"[a-z0-9._%+-]+@[a-z0-9.-]+\.[a-z]{2,}", re.IGNORECASE)
_MAX_RESULTS_SHOWN: int = 10
_ANSWER_MAX_TOKENS: int = 700

_SYSTEM_PROMPT: str = (
    "Tu vérifies une entreprise locale à partir des résultats d'une recherche web. "
    "Tu réponds uniquement d'après les résultats fournis, jamais de mémoire. "
    "Quand une information n'est pas écrite dans les résultats, tu réponds null. "
    "Tu réponds par un seul objet JSON, sans texte autour."
)

_ANSWER_FORMAT: str = """Réponds avec cet objet JSON :
{
  "own_website_index": numéro du résultat qui est le site web PROPRE de cette entreprise (son nom de domaine à elle), sinon null. Un annuaire, un registre d'entreprises, un réseau social, une place de marché, un site d'avis, un site de devis, ou sa page sur le site d'un réseau, d'une marque ou d'un organisme n'est pas son site.
  "is_chain_or_franchise": true si l'entreprise est une succursale d'une chaîne, une franchise ou une agence d'un groupe (le patron ne décide pas seul), sinon false. Un indépendant affilié à un réseau (garage AD, Motrio, Top Garage, Precisium, Eurorepar, Bosch Car Service, agent d'une marque automobile, artisan labellisé) n'est PAS une chaîne : réponds false,
  "is_other_business": true si les résultats parlent d'une AUTRE entreprise du même nom, dans une autre ville, sinon false,
  "matches_trade": false seulement si les résultats montrent clairement que l'entreprise n'exerce pas le métier cherché, sinon true,
  "owner_name": prénom et nom du dirigeant s'ils sont écrits dans un résultat, sinon null,
  "owner_name_index": numéro du résultat où ce nom est écrit, sinon null,
  "emails": [{"email": "adresse écrite dans un résultat", "index": numéro du résultat, "belongs_to_business": true si le résultat présente cette adresse comme celle de cette entreprise, sinon false}]
}"""


@dataclass(frozen=True)
class SearchResultLine:
    """One result of a web search, as shown to the judge."""

    link: str
    host: str
    title: str
    description: str

    @property
    def text(self) -> str:
        """Title and snippet together, the only text an answer may be read from."""
        return f"{self.title} {self.description}"


@dataclass(frozen=True)
class JudgedEmail:
    """An email the judge read in a result, and whether that result gives it to the business."""

    email: str
    result_index: int
    belongs_to_business: bool


@dataclass(frozen=True)
class JudgeVerdict:
    """What the judge read in the results of one business."""

    own_website_index: int | None = None
    is_chain_or_franchise: bool = False
    is_other_business: bool = False
    matches_trade: bool = True
    owner_name: str | None = None
    owner_name_index: int | None = None
    emails: list[JudgedEmail] = field(default_factory=list)


class SearchJudge:
    """Asks the language model closed questions about one business's search results."""

    async def judge(
        self,
        *,
        name: str,
        city: str | None,
        trade_label: str,
        google_category: str | None,
        results: list[SearchResultLine],
    ) -> JudgeVerdict | None:
        """
        Read the search results of one business.

        Args:
            name: Business name.
            city: Town of the business.
            trade_label: Trade the search is after.
            google_category: Category Google shows for the business, when known.
            results: Result lines of the search, in page order.

        Returns:
            The verdict, or ``None`` when the model is unavailable or answered nothing usable
            (the caller then keeps its rule-based reading).
        """
        shown = results[:_MAX_RESULTS_SHOWN]
        if not shown:
            return None
        lines = "\n".join(
            f"[{index}] {line.host} | {line.title} | {line.description}" for index, line in enumerate(shown)
        )
        question = (
            f"Entreprise : {name}\n"
            f"Ville : {city or 'inconnue'}\n"
            f"Métier cherché : {trade_label}\n"
            f"Catégorie Google : {google_category or 'inconnue'}\n\n"
            f"Résultats de la recherche :\n{lines}\n\n{_ANSWER_FORMAT}"
        )
        answer = await llm_service.complete_json(
            [{"role": "system", "content": _SYSTEM_PROMPT}, {"role": "user", "content": question}],
            max_tokens=_ANSWER_MAX_TOKENS,
            temperature=0.0,
        )
        if answer is None:
            return None
        return self.parse_answer(answer, shown)

    @classmethod
    def parse_answer(cls, answer: dict[str, Any], results: list[SearchResultLine]) -> JudgeVerdict:
        """
        Keep only what the answer can prove against the results it was read on.

        Args:
            answer: The model's JSON object.
            results: The result lines the model was shown.

        Returns:
            The verdict, with out-of-range indexes and unfound names or emails dropped.
        """
        own_website_index = cls._valid_index(answer.get("own_website_index"), results)
        owner_index = cls._valid_index(answer.get("owner_name_index"), results)
        owner_name = str(answer.get("owner_name") or "").strip() or None
        if owner_name is None or owner_index is None or not cls._is_written_in(owner_name, results[owner_index]):
            owner_name, owner_index = None, None

        emails: list[JudgedEmail] = []
        for entry in answer.get("emails") or []:
            if not isinstance(entry, dict):
                continue
            email = str(entry.get("email") or "").strip().lower()
            index = cls._valid_index(entry.get("index"), results)
            if index is None or not _EMAIL_RE.fullmatch(email) or email not in results[index].text.lower():
                continue
            emails.append(
                JudgedEmail(email=email, result_index=index, belongs_to_business=bool(entry.get("belongs_to_business")))
            )

        return JudgeVerdict(
            own_website_index=own_website_index,
            is_chain_or_franchise=bool(answer.get("is_chain_or_franchise")),
            is_other_business=bool(answer.get("is_other_business")),
            matches_trade=answer.get("matches_trade") is not False,
            owner_name=owner_name,
            owner_name_index=owner_index,
            emails=emails,
        )

    @staticmethod
    def _valid_index(raw_index: Any, results: list[SearchResultLine]) -> int | None:
        """A result index the model gave, when it points at a shown result."""
        if isinstance(raw_index, bool) or not isinstance(raw_index, int):
            return None
        return raw_index if 0 <= raw_index < len(results) else None

    @staticmethod
    def _is_written_in(person_name: str, result: SearchResultLine) -> bool:
        """Whether every word of a person's name appears in the result it is said to come from."""
        words = [word for word in re.split(r"[^a-z]+", fold(person_name)) if len(word) > 1]
        result_text = fold(result.text)
        return len(words) >= 2 and all(word in result_text for word in words)


search_judge = SearchJudge()
