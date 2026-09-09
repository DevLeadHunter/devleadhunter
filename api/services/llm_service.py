"""
LLM helper backed by Groq (OpenAI-compatible API).

Used for the behaviour summary shown in the prospect drawer and for the
behaviour-based personalised follow-up. Every method degrades gracefully to a
rule-based output when ``GROQ_API_KEY`` is not configured, so the product works
without the LLM and lights up automatically once a key is provided.
"""

from __future__ import annotations

import json
import logging
import re
import time
from typing import Any

import httpx

from core.config import settings

logger = logging.getLogger(__name__)

_GROQ_URL = "https://api.groq.com/openai/v1/chat/completions"
_GROQ_MODELS_URL = "https://api.groq.com/openai/v1/models"
# Known Groq vision models, most preferred first. The configured ``GROQ_VISION_MODEL`` is tried
# ahead of these; whichever is listed by the account's live ``/models`` endpoint wins, so a
# decommissioned id degrades to the next one instead of killing photo labelling.
_VISION_MODEL_CANDIDATES: tuple[str, ...] = (
    "qwen/qwen3.6-27b",
    "meta-llama/llama-4-scout-17b-16e-instruct",
    "meta-llama/llama-4-maverick-17b-128e-instruct",
    "qwen/qwen3.8-27b",
)
_VISION_MODEL_CACHE_SECONDS = 3600.0
_JSON_FENCE_RE = re.compile(r"^```(?:json)?\s*|\s*```$", re.IGNORECASE)
# gpt-oss / qwen3 models reason before answering, and the reasoning tokens count against
# ``max_tokens`` — a tiny budget (e.g. 10 for a one-word verdict) is entirely consumed by
# reasoning, leaving the content empty. Force a low reasoning effort and a floor that leaves
# room for the answer. Non-reasoning models (a future llama override) reject the param, so it
# is only sent when the model id looks like a reasoning model.
_MIN_MAX_TOKENS = 512
_REASONING_MODEL_HINTS = ("gpt-oss", "qwen3")


def _uses_reasoning(model: str) -> bool:
    """Whether the model id is a reasoning model that needs ``reasoning_effort``."""
    lowered = model.lower()
    return any(hint in lowered for hint in _REASONING_MODEL_HINTS)


def _format_sender_identity(*, sender_name: str, company_name: str | None) -> str:
    """Build the « Name (Company) » label injected into outreach prompts."""
    name = (sender_name or "").strip() or "le commercial"
    company = (company_name or "").strip()
    return f"{name} ({company})" if company else name


class LLMService:
    """Thin Groq client with rule-based fallbacks."""

    def __init__(self) -> None:
        # (resolved_at, model id or None) — the vision model verified against the live model list.
        self._vision_model_cache: tuple[float, str | None] | None = None

    @property
    def is_configured(self) -> bool:
        """True when a Groq API key is available."""
        return bool(settings.groq_api_key)

    async def _chat(
        self,
        messages: list[dict[str, Any]],
        *,
        max_tokens: int = 600,
        temperature: float = 0.6,
        model: str | None = None,
        json_mode: bool = False,
        timeout: float = 40.0,
    ) -> str | None:
        """Call Groq chat completions. Returns the text, or None on failure.

        Args:
            messages: OpenAI-style messages; ``content`` may be a string or a list of parts
                (``text`` / ``image_url``) for vision models.
            max_tokens: Answer budget (floored so reasoning models keep room for the content).
            temperature: Sampling temperature.
            model: Model id override (default: ``settings.groq_model``).
            json_mode: Ask for a JSON object answer (``response_format``).
            timeout: HTTP timeout in seconds.
        """
        if not self.is_configured:
            return None
        chosen_model = model or settings.groq_model
        payload: dict[str, Any] = {
            "model": chosen_model,
            "messages": messages,
            "temperature": temperature,
            "max_tokens": max(max_tokens, _MIN_MAX_TOKENS),
        }
        if json_mode:
            payload["response_format"] = {"type": "json_object"}
        if _uses_reasoning(chosen_model):
            payload["reasoning_effort"] = "low"
        try:
            async with httpx.AsyncClient(timeout=timeout) as client:
                response = await client.post(_GROQ_URL, headers=self._headers(), json=payload)
                # A model that rejects ``reasoning_effort`` (not every qwen/gpt-oss variant takes it)
                # answers 400: retry once without the knob rather than failing the whole call.
                if (
                    response.status_code == 400
                    and "reasoning" in response.text.lower()
                    and "reasoning_effort" in payload
                ):
                    payload.pop("reasoning_effort")
                    response = await client.post(_GROQ_URL, headers=self._headers(), json=payload)
                response.raise_for_status()
                data: dict[str, Any] = response.json()
                return data["choices"][0]["message"]["content"].strip()
        except Exception as exc:
            logger.warning("Groq call failed (%s): %s", chosen_model, exc)
            return None

    async def complete_json(
        self,
        messages: list[dict[str, Any]],
        *,
        max_tokens: int = 900,
        temperature: float = 0.2,
        model: str | None = None,
        timeout: float = 60.0,
    ) -> dict[str, Any] | None:
        """Chat completion in JSON mode, parsed into a dict.

        Returns None when Groq is off, the call failed, or the answer is not a JSON object —
        callers always keep a rule-based path.
        """
        text = await self._chat(
            messages, max_tokens=max_tokens, temperature=temperature, model=model, json_mode=True, timeout=timeout
        )
        return self._parse_json_object(text)

    async def resolve_vision_model(self) -> str | None:
        """The vision model to use: the configured one when the account lists it, else the first known one.

        The live ``/models`` list is consulted at most once an hour; when it cannot be read the
        configured id is trusted as-is. None when Groq is not configured or no candidate exists.
        """
        if not self.is_configured:
            return None
        now = time.monotonic()
        if self._vision_model_cache and now - self._vision_model_cache[0] < _VISION_MODEL_CACHE_SECONDS:
            return self._vision_model_cache[1]
        preferred = (settings.groq_vision_model or "").strip()
        candidates: list[str] = [preferred] if preferred else []
        candidates.extend(candidate for candidate in _VISION_MODEL_CANDIDATES if candidate not in candidates)
        available = await self._list_model_ids()
        resolved: str | None
        if available is None:
            resolved = candidates[0] if candidates else None
        else:
            resolved = next((candidate for candidate in candidates if candidate in available), None)
            if resolved is None:
                logger.warning("No known Groq vision model available (tried %s)", ", ".join(candidates))
        self._vision_model_cache = (now, resolved)
        return resolved

    async def _list_model_ids(self) -> set[str] | None:
        """Model ids the account can use, or None when the list could not be read."""
        try:
            async with httpx.AsyncClient(timeout=15.0) as client:
                response = await client.get(_GROQ_MODELS_URL, headers=self._headers())
                response.raise_for_status()
                data: dict[str, Any] = response.json()
                return {str(item.get("id", "")) for item in data.get("data", []) if isinstance(item, dict)}
        except Exception as exc:
            logger.warning("Groq model list unavailable: %s", exc)
            return None

    @staticmethod
    def _headers() -> dict[str, str]:
        """Authorization header for the Groq API."""
        return {"Authorization": f"Bearer {settings.groq_api_key}"}

    @staticmethod
    def _parse_json_object(text: str | None) -> dict[str, Any] | None:
        """Parse a model answer as a JSON object, tolerating code fences and leading prose."""
        if not text:
            return None
        cleaned = _JSON_FENCE_RE.sub("", text.strip())
        try:
            parsed = json.loads(cleaned)
        except ValueError:
            start = cleaned.find("{")
            end = cleaned.rfind("}")
            if start == -1 or end <= start:
                return None
            try:
                parsed = json.loads(cleaned[start : end + 1])
            except ValueError:
                return None
        return parsed if isinstance(parsed, dict) else None

    async def classify_reply_intent(self, reply_text: str) -> str | None:
        """
        Classify what a prospect's reply means, in one deterministic word.

        Called at most once per reply (the verdict is persisted by the caller);
        ``temperature=0`` so the same content always yields the same verdict.

        Args:
            reply_text: The reply as plain text (already stripped of HTML).

        Returns:
            The raw model output (single word expected), or ``None`` when Groq is
            not configured or the call failed. Validation happens in the caller.
        """
        excerpt = reply_text.strip()[:1500]
        if not excerpt:
            return None
        prompt = (
            "Tu classes la réponse d'un prospect (artisan/commerçant français) à un email de "
            "prospection pour la création d'un site web. Réponds par UN SEUL mot, exactement "
            "parmi : interested, not_interested, later, question, unsubscribe, other.\n"
            "- interested : intérêt clair (oui, rdv, rappelez-moi, envoyez le devis…)\n"
            "- not_interested : refus (pas intéressé, j'ai déjà un site, non merci…)\n"
            "- later : pas maintenant mais ouvert (recontactez-moi en septembre, trop tôt…)\n"
            "- question : demande d'information (prix, délais, comment ça marche…)\n"
            "- unsubscribe : demande explicite d'arrêter les emails\n"
            "- other : tout le reste (hors sujet, illisible…)\n\n"
            f"Réponse du prospect :\n« {excerpt} »"
        )
        return await self._chat([{"role": "user", "content": prompt}], max_tokens=10, temperature=0.0)

    async def summarize_behavior(
        self,
        *,
        sender_name: str,
        company_name: str | None,
        business_name: str,
        temperature: str,
        signals: dict[str, Any],
    ) -> str:
        """Produce a short behavioural read + relance advice for a prospect."""
        sender = _format_sender_identity(sender_name=sender_name, company_name=company_name)
        prompt = (
            f"Tu es l'assistant commercial de {sender}, qui vend des sites web aux artisans. "
            "Voici le comportement d'un prospect : son activité sur la démo de site ET son engagement "
            "email (emails_sent/opened/clicked).\n"
            f"Entreprise : {business_name}\n"
            f"Température : {temperature}\n"
            f"Signaux (démo + email) : {signals}\n\n"
            "En 3-4 phrases max, en français, interprète ce comportement (démo + email) et conseille "
            "concrètement comment relancer ce prospect (angle, ton, urgence). Sois direct, pas de blabla."
        )
        result = await self._chat([{"role": "user", "content": prompt}], max_tokens=300)
        return result or self._fallback_summary(temperature, signals)

    async def draft_followup(
        self,
        *,
        sender_name: str,
        company_name: str | None,
        business_name: str,
        first_name: str,
        temperature: str,
        signals: dict[str, Any],
        base_subject: str,
        base_body_html: str,
    ) -> dict[str, str]:
        """Draft a behaviour-personalised follow-up, falling back to the base template."""
        sender = _format_sender_identity(sender_name=sender_name, company_name=company_name)
        prompt = (
            f"Tu écris un email de relance B2B court et naturel (français), de la part de {sender} "
            "qui a envoyé une démo de site web à un artisan.\n"
            f"Prénom du contact : {first_name or 'le contact'}\n"
            f"Entreprise : {business_name}\n"
            f"Température du lead : {temperature}\n"
            f"Comportement (démo + engagement email) : {signals}\n\n"
            "Relance existante (à personnaliser, garde l'esprit) :\n"
            f"Objet: {base_subject}\n{base_body_html}\n\n"
            "Réécris une relance personnalisée selon ce qu'il a regardé/cliqué sur la démo. "
            "Réponds STRICTEMENT au format:\n"
            "SUBJECT: <objet>\nBODY: <corps en HTML simple>"
        )
        result = await self._chat([{"role": "user", "content": prompt}], max_tokens=700)
        if not result:
            return {"subject": base_subject, "body_html": base_body_html}
        return self._parse_subject_body(result, base_subject, base_body_html)

    async def suggest_domain_names(self, *, business_name: str, city: str | None, category: str | None) -> list[str]:
        """Propose a few short, brandable domain labels for a business (no extension).

        Enriches the code-logic candidates when the exact business name is taken or ugly.
        Returns bare labels (no ``.fr``, no accents), lowercase — the caller validates and
        appends ``.fr``. Degrades to ``[]`` when Groq is off or the call fails, so the
        suggestion still works on the rule-based candidates alone.

        Args:
            business_name: The prospect's business name.
            city: The prospect's city, when known (helps disambiguate).
            category: The prospect's trade, when known (e.g. « restaurant »).

        Returns:
            Up to five candidate labels, or ``[]``.
        """
        name = (business_name or "").strip()
        if not name:
            return []
        context = f"Entreprise : {name}"
        if city:
            context += f"\nVille : {city}"
        if category:
            context += f"\nMétier : {category}"
        prompt = (
            "Propose 4 idées de nom de domaine pour le site de cette entreprise artisanale/commerçante "
            "française. Contraintes STRICTES : court, mémorable, SANS accent, SANS espace, uniquement "
            "lettres minuscules / chiffres / tirets, PAS d'extension (pas de .fr). Reste proche du nom de "
            "l'entreprise, évite le générique. Réponds UNIQUEMENT par les 4 labels, un par ligne, rien d'autre.\n\n"
            f"{context}"
        )
        result = await self._chat([{"role": "user", "content": prompt}], max_tokens=80, temperature=0.7)
        if not result:
            return []
        labels: list[str] = []
        for line in result.splitlines():
            cleaned = line.strip().strip("-•*0123456789. ").lower()
            if cleaned:
                labels.append(cleaned)
        return labels[:5]

    # ── Fallbacks / parsing ────────────────────────────────────────────────

    @staticmethod
    def _fallback_summary(temperature: str, signals: dict[str, Any]) -> str:
        """Rule-based summary when no LLM is available."""
        if temperature == "unknown":
            return "Aucune visite détectée sur la démo pour l'instant. Relancer sur l'intérêt d'avoir un site."
        bits: list[str] = []
        if signals.get("phone_clicks"):
            bits.append("a cliqué sur le téléphone (intérêt fort)")
        if signals.get("contact_clicks"):
            bits.append("a cliqué sur le contact")
        if signals.get("cta_clicks"):
            bits.append("a cliqué sur un bouton d'action")
        if signals.get("visits", 0) > 1:
            bits.append(f"est revenu {signals['visits']} fois sur la démo")
        if signals.get("total_seconds", 0) >= 60:
            bits.append("a passé du temps sur la page")
        if signals.get("video_completes"):
            bits.append("a regardé la vidéo en entier")
        elif signals.get("video_max_progress", 0) >= 50:
            bits.append(f"a regardé {signals['video_max_progress']}% de la vidéo")
        elif signals.get("video_plays"):
            bits.append("a lancé la vidéo")
        if signals.get("video_replays"):
            bits.append(f"a revu la vidéo {signals['video_replays']}x")
        if signals.get("video_fullscreen"):
            bits.append("a mis la vidéo en plein écran")
        if signals.get("emails_clicked"):
            bits.append("a cliqué le lien dans l'email")
        elif signals.get("emails_opened"):
            bits.append(f"a ouvert l'email ({signals['emails_opened']}x)")
        detail = ", ".join(bits) if bits else "a consulté la démo brièvement"
        advice = {
            "hot": "Lead chaud — relancer vite, proposer un appel ou finaliser la vente.",
            "warm": "Lead tiède — relancer en mettant en avant le bénéfice concret du site.",
            "cold": "Lead froid — relancer une fois avec un angle simple et une preuve sociale.",
        }.get(temperature, "")
        return f"Le prospect {detail}. {advice}"

    @staticmethod
    def _parse_subject_body(text: str, base_subject: str, base_body_html: str) -> dict[str, str]:
        """Parse a 'SUBJECT: ... BODY: ...' LLM response."""
        subject = base_subject
        body = base_body_html
        if "SUBJECT:" in text and "BODY:" in text:
            try:
                after_subject = text.split("SUBJECT:", 1)[1]
                subject_part, body_part = after_subject.split("BODY:", 1)
                subject = subject_part.strip() or base_subject
                body = body_part.strip() or base_body_html
            except (IndexError, ValueError):
                pass
        else:
            body = text.strip() or base_body_html
        return {"subject": subject, "body_html": body}


llm_service = LLMService()
