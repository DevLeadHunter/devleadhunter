"""
Vision labelling of prospect photos — what each photo shows, read once and kept on the enrichment.

A food truck's Google/Facebook photos mix dishes, the truck itself, photographed menu boards,
events and flyers. Site generation used to place them by position only, so the truck regularly
landed on a « Nos spécialités » card. Labelling each photo once (kind + short description + the
dishes it shows or lists) lets generation and the specialties editor pick real dish photos, and
turns photographed menus into the menu text that was never scraped.

Labels live in ``ProspectEnrichment.photo_labels`` keyed by photo URL, so a photo is analysed once
for its lifetime (re-labelled only when the URL changes, e.g. after an R2 rehost, or when the
prompt version moves). Everything degrades cleanly without a Groq key: no labels, legacy behaviour.

Groq's vision endpoint is rate limited per minute: batches run one after the other, each result is
saved as soon as it lands, and a run stops launching batches past its time budget — the photos left
over are simply labelled at the next call.
"""

from __future__ import annotations

import asyncio
import logging
import time
from collections import Counter
from typing import Any

from sqlalchemy.orm import Session

from models.prospect_enrichment import ProspectEnrichment
from services.llm_service import llm_service
from services.photo_labels import (  # noqa: F401 — re-exported for callers of this service
    CARD_WORTHY_KINDS,
    PHOTO_KIND_MENU_BOARD,
    PHOTO_KINDS,
    PHOTO_LABEL_VERSION,
    is_card_worthy,
    is_unfit_for_card,
    labels_for_urls,
    normalize_label,
    rank_card_photos,
)

logger = logging.getLogger(__name__)

# Groq vision models accept a handful of images per request (3 to 5 depending on the model) and the
# account is capped in tokens per minute (2 048 tokens per image): small sequential batches.
_IMAGES_PER_REQUEST = 3
_MAX_PHOTOS_PER_RUN = 40
# A run inside an HTTP request must answer before the proxy gives up: past this budget the
# remaining photos wait for the next call (the caller reports them as pending).
_DEFAULT_TIME_BUDGET_SECONDS = 45.0

# Prospect categories worth labelling at enrichment time (every other trade labels lazily, on demand).
_FOOD_CATEGORY_HINTS: tuple[str, ...] = (
    "food",
    "restau",
    "truck",
    "traiteur",
    "snack",
    "pizz",
    "burger",
    "kebab",
    "tacos",
    "sandwich",
    "crêp",
    "crep",
    "sushi",
    "wok",
    "grill",
    "rôtisserie",
    "rotisserie",
    "bistro",
    "brasserie",
    "cantine",
    "cuisine",
    "glacier",
    "gaufre",
    "friterie",
    "chef",
    "cater",
    "diner",
    "bar à",
    "salon de thé",
    "café",
    "cafe",
    "coffee",
    "boulanger",
    "pâtisser",
    "patisser",
)

_SYSTEM_PROMPT = (
    "Tu analyses les photos publiques d'un commerce de restauration français (food truck, restaurant, "
    "crêperie, traiteur) pour construire son site web. Pour CHAQUE photo fournie, tu décris ce qu'elle "
    "montre. Réponds UNIQUEMENT par un objet JSON de la forme "
    '{"photos": [{"index": 1, "kind": "dish", "description": "…", "dishes": ["…"], "appeal": 4}]} '
    "avec exactement une entrée par photo, dans l'ordre reçu.\n"
    "kind, une valeur parmi (en anglais, exactement) :\n"
    "- dish : de la nourriture prête à manger en sujet principal — plat, assiette, burger, crêpe, galette, "
    "pizza, sandwich, dessert, barquette à emporter, plat tenu en main\n"
    "- drink : une boisson en sujet principal\n"
    "- truck : le camion, la remorque, la façade ou le stand vus de l'extérieur\n"
    "- menu_board : une ardoise, une carte, un menu ou des prix écrits et lisibles\n"
    "- interior : intérieur, cuisine, comptoir, matériel, sans plat en vedette\n"
    "- people : l'équipe ou des clients en sujet principal, sans plat en vedette\n"
    "- event : événement, festival, foule, mariage\n"
    "- logo_or_flyer : logo, affiche, flyer, visuel promotionnel, capture de texte\n"
    "- other : tout le reste\n"
    "En cas de doute, dès que de la nourriture est bien visible et occupe une bonne part de l'image, "
    "choisis dish.\n"
    "description : une phrase en français de 120 caractères max décrivant précisément ce qu'on voit "
    "(pour un plat, nomme-le : « Galette complète jambon, œuf, fromage avec salade »).\n"
    "dishes : pour un menu_board, TOUS les noms de plats lisibles (avec le prix s'il est lisible, "
    "ex. « Galette complète 8€ ») ; pour un dish, le nom le plus probable du plat ; sinon une liste vide. "
    "N'invente jamais un plat que la photo ne montre pas.\n"
    "appeal : de 1 à 5, l'attrait visuel de la photo pour illustrer une carte « spécialité » "
    "(5 = photo appétissante et nette, 1 = floue, sombre ou hors sujet)."
)


def _is_http_url(value: Any) -> bool:
    """Whether a value is a fetchable http(s) URL (the only kind sent to the vision model)."""
    return isinstance(value, str) and value.strip().lower().startswith(("http://", "https://"))


def should_label_for_category(category: str | None) -> bool:
    """Whether a prospect's trade is food-related, so its photos are labelled right at enrichment."""
    lowered = (category or "").strip().lower()
    return bool(lowered) and any(hint in lowered for hint in _FOOD_CATEGORY_HINTS)


class PhotoLabelingService:
    """Labels prospect photos with the Groq vision model and persists the result on the enrichment."""

    @property
    def is_available(self) -> bool:
        """True when a Groq API key is configured (the model itself is resolved per call)."""
        return llm_service.is_configured

    async def label_photos(
        self,
        urls: list[str],
        *,
        time_budget_seconds: float | None = None,
        on_batch_labelled: Any = None,
    ) -> dict[str, dict[str, Any]]:
        """Label a list of photo URLs, batch after batch, within an optional time budget.

        Args:
            urls: Photo URLs (non-http entries are skipped).
            time_budget_seconds: Stop launching batches once this many seconds have elapsed.
            on_batch_labelled: Optional callback ``(labels: dict) -> None`` invoked after each batch,
                so a caller can save progress before the run ends.

        Returns:
            ``{url: label}`` for every photo the model answered for; photos of a failed or skipped
            batch are simply absent (they will be retried at the next call).
        """
        candidates = [url for url in dict.fromkeys(urls) if _is_http_url(url)][:_MAX_PHOTOS_PER_RUN]
        if not candidates or not self.is_available:
            return {}
        model = await llm_service.resolve_vision_model()
        if not model:
            return {}
        started = time.monotonic()
        budget = time_budget_seconds if time_budget_seconds is not None else _DEFAULT_TIME_BUDGET_SECONDS
        labels: dict[str, dict[str, Any]] = {}
        batches = [candidates[i : i + _IMAGES_PER_REQUEST] for i in range(0, len(candidates), _IMAGES_PER_REQUEST)]
        for position, batch in enumerate(batches):
            if position > 0 and time.monotonic() - started > budget:
                logger.info(
                    "Photo labelling paused after %.0fs: %s photo(s) left for the next call",
                    budget,
                    len(candidates) - len(labels),
                )
                break
            batch_labels = await self._label_batch(batch, model)
            if not batch_labels:
                continue
            labels.update(batch_labels)
            if on_batch_labelled is not None:
                on_batch_labelled(batch_labels)
        if labels:
            kinds = Counter(str(label.get("kind")) for label in labels.values())
            logger.info(
                "Photo labelling: %s/%s photos labelled with %s: %s", len(labels), len(candidates), model, dict(kinds)
            )
        return labels

    async def _label_batch(self, batch: list[str], model: str) -> dict[str, dict[str, Any]]:
        """Label up to ``_IMAGES_PER_REQUEST`` photos in one vision call, falling back to one call per photo.

        A batch the model rejects (one image it cannot fetch, a payload too large) must not sink its
        other photos: each is then tried alone.
        """
        labels = await self._request_labels(batch, model)
        if labels or len(batch) == 1:
            return labels
        for url in batch:
            labels.update(await self._request_labels([url], model))
        return labels

    async def _request_labels(self, batch: list[str], model: str) -> dict[str, dict[str, Any]]:
        """One vision call for a batch; empty when the call failed or answered nothing usable."""
        parts: list[dict[str, Any]] = [
            {"type": "text", "text": f"Voici {len(batch)} photo(s), numérotée(s) de 1 à {len(batch)} dans l'ordre."}
        ]
        for url in batch:
            parts.append({"type": "image_url", "image_url": {"url": url}})
        answer = await llm_service.complete_json(
            [
                {"role": "system", "content": _SYSTEM_PROMPT},
                {"role": "user", "content": parts},
            ],
            max_tokens=1200,
            temperature=0.1,
            model=model,
            timeout=90.0,
        )
        return self.parse_batch_answer(answer, batch)

    @staticmethod
    def parse_batch_answer(answer: dict[str, Any] | None, batch: list[str]) -> dict[str, dict[str, Any]]:
        """Map a batch answer back onto its URLs, by the 1-based ``index`` (falling back to position)."""
        if not isinstance(answer, dict):
            return {}
        entries = answer.get("photos")
        if not isinstance(entries, list):
            return {}
        labels: dict[str, dict[str, Any]] = {}
        for position, entry in enumerate(entries):
            label = normalize_label(entry)
            if label is None or not isinstance(entry, dict):
                continue
            try:
                index = int(entry.get("index", position + 1)) - 1
            except (TypeError, ValueError):
                index = position
            if not 0 <= index < len(batch):
                continue
            label["version"] = PHOTO_LABEL_VERSION
            labels[batch[index]] = label
        return labels

    async def ensure_labels(
        self,
        db: Session,
        record: ProspectEnrichment,
        urls: list[str],
        *,
        force: bool = False,
        time_budget_seconds: float | None = None,
    ) -> dict[str, dict[str, Any]]:
        """Label the photos of ``urls`` that have no current label yet, saving after every batch.

        Args:
            db: Active session (committed after each labelled batch).
            record: The enrichment to update.
            urls: The photos that need a label (typically the site's usable pool).
            force: Re-label even the photos that already have one.
            time_budget_seconds: Budget handed to :meth:`label_photos` (None = default).

        Returns:
            The labels for ``urls`` (existing + freshly computed), keyed by URL.
        """
        wanted = [url for url in dict.fromkeys(urls) if isinstance(url, str) and url.strip()]
        existing = labels_for_urls(record.photo_labels, wanted)
        missing = [url for url in wanted if force or url not in existing]
        if not missing or not self.is_available:
            return existing

        def save_batch(batch_labels: dict[str, dict[str, Any]]) -> None:
            existing.update(batch_labels)
            self._persist(db, record, batch_labels)

        await self.label_photos(missing, time_budget_seconds=time_budget_seconds, on_batch_labelled=save_batch)
        return existing

    @staticmethod
    def _persist(db: Session, record: ProspectEnrichment, labels: dict[str, dict[str, Any]]) -> None:
        """Merge labels into the record, pruning entries whose photo is no longer on the prospect."""
        current = record.photo_labels if isinstance(record.photo_labels, dict) else {}
        merged: dict[str, Any] = {**current, **labels}
        live_urls = {url for url in (record.photos or []) if isinstance(url, str)} | set(labels)
        record.photo_labels = {url: label for url, label in merged.items() if url in live_urls}
        db.add(record)
        db.commit()

    def schedule(self, prospect_id: int) -> None:
        """Fire-and-forget labelling of a prospect's photos (never blocks the caller)."""
        if not self.is_available:
            return
        try:
            asyncio.get_running_loop()
        except RuntimeError:
            return
        asyncio.create_task(self._label_in_background(prospect_id))

    async def _label_in_background(self, prospect_id: int) -> None:
        """Label a prospect's usable site photos on a fresh session, without a time budget."""
        from core.database import SessionLocal
        from services.enrichment_service import enrichment_service
        from services.templates.site_content import usable_site_photos

        db: Session = SessionLocal()
        try:
            record = db.query(ProspectEnrichment).filter(ProspectEnrichment.prospect_id == prospect_id).first()
            if record is None:
                return
            pool = usable_site_photos(enrichment_service.to_dict(record))
            labelled = await self.ensure_labels(db, record, pool, time_budget_seconds=float("inf"))
            logger.info("Photo labelling done for prospect_id=%s (%s/%s photos)", prospect_id, len(labelled), len(pool))
        except Exception as exc:
            logger.warning("Background photo labelling failed for prospect_id=%s: %s", prospect_id, exc)
        finally:
            db.close()


photo_labeling_service = PhotoLabelingService()
