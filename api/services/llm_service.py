"""
LLM helper backed by Groq (OpenAI-compatible API).

Used for the behaviour summary shown in the prospect drawer and for the
behaviour-based personalised follow-up. Every method degrades gracefully to a
rule-based output when ``GROQ_API_KEY`` is not configured, so the product works
without the LLM and lights up automatically once a key is provided.
"""
from __future__ import annotations

import logging
from typing import Any, Optional

import httpx

from core.config import settings

logger = logging.getLogger(__name__)

_GROQ_URL = "https://api.groq.com/openai/v1/chat/completions"


class LLMService:
    """Thin Groq client with rule-based fallbacks."""

    @property
    def is_configured(self) -> bool:
        """True when a Groq API key is available."""
        return bool(settings.groq_api_key)

    async def _chat(self, messages: list[dict[str, str]], *, max_tokens: int = 600) -> Optional[str]:
        """Call Groq chat completions. Returns the text, or None on failure."""
        if not self.is_configured:
            return None
        try:
            async with httpx.AsyncClient(timeout=40.0) as client:
                response = await client.post(
                    _GROQ_URL,
                    headers={"Authorization": f"Bearer {settings.groq_api_key}"},
                    json={
                        "model": settings.groq_model,
                        "messages": messages,
                        "temperature": 0.6,
                        "max_tokens": max_tokens,
                    },
                )
                response.raise_for_status()
                data: dict[str, Any] = response.json()
                return data["choices"][0]["message"]["content"].strip()
        except Exception as exc:  # noqa: BLE001
            logger.warning("Groq call failed: %s", exc)
            return None

    async def summarize_behavior(
        self, *, business_name: str, temperature: str, signals: dict[str, Any]
    ) -> str:
        """Produce a short behavioural read + relance advice for a prospect."""
        prompt = (
            "Tu es l'assistant commercial de Léo (Dibodev), qui vend des sites web aux artisans. "
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
        business_name: str,
        first_name: str,
        temperature: str,
        signals: dict[str, Any],
        base_subject: str,
        base_body_html: str,
    ) -> dict[str, str]:
        """Draft a behaviour-personalised follow-up, falling back to the base template."""
        prompt = (
            "Tu écris un email de relance B2B court et naturel (français), de la part de Léo (Dibodev) "
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
            # No structured markers — treat the whole text as the body.
            body = text.strip() or base_body_html
        return {"subject": subject, "body_html": body}


llm_service = LLMService()
