"""Pre-send spam scoring — SpamAssassin (free Postmark endpoint) + local checks.

Two complementary layers:
1. ``spamcheck.postmarkapp.com`` — a free public API running SpamAssassin on a
   raw MIME message; returns the score and the per-rule diagnostics.
2. Local heuristics tuned for our French cold emails: unsubscribe link,
   link count, shouty subject, spammy vocabulary, HTML weight.

Used by the "Tester un email" panel of the email-health page BEFORE launching
a campaign.
"""
from __future__ import annotations

import logging
import re
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from typing import Any

import httpx

logger = logging.getLogger(__name__)

_SPAMCHECK_URL: str = "https://spamcheck.postmarkapp.com/filter"

# French cold-email vocabulary that reliably trips content filters.
_SPAMMY_WORDS: tuple[str, ...] = (
    "gratuit", "urgent", "cliquez ici", "offre exceptionnelle", "promotion",
    "gagnez", "félicitations", "100%", "garanti", "sans engagement",
    "dernière chance", "profitez", "incroyable", "miracle", "argent facile",
)


def _strip_html(html: str) -> str:
    """Plain-text version of an HTML body (rough, good enough for ratios).

    @param html - HTML source.
    @returns Visible text.
    """
    text = re.sub(r"<(script|style)[^>]*>.*?</\1>", " ", html, flags=re.S | re.I)
    text = re.sub(r"<[^>]+>", " ", text)
    return re.sub(r"\s+", " ", text).strip()


class EmailSpamTestService:
    """Score an email draft before sending it."""

    async def test(self, *, subject: str, body_html: str, from_email: str, to_email: str) -> dict[str, Any]:
        """Run SpamAssassin + local heuristics on a draft.

        @param subject - Email subject.
        @param body_html - HTML body (template variables may remain — scored as-is).
        @param from_email - Sender address (used in the MIME envelope).
        @param to_email - Any recipient address for the envelope.
        @returns SpamAssassin verdict (or its error) + the local checklist.
        """
        spamassassin = await self._spamassassin(subject, body_html, from_email, to_email)
        checks = self._local_checks(subject, body_html)
        return {"spamassassin": spamassassin, "checks": checks}

    async def _spamassassin(
        self, subject: str, body_html: str, from_email: str, to_email: str
    ) -> dict[str, Any]:
        """POST the raw MIME to Postmark SpamCheck.

        @param subject - Email subject.
        @param body_html - HTML body.
        @param from_email - Sender.
        @param to_email - Recipient.
        @returns ``score``/``rules`` on success, ``error`` otherwise.
        """
        message = MIMEMultipart("alternative")
        message["Subject"] = subject
        message["From"] = from_email
        message["To"] = to_email
        message.attach(MIMEText(_strip_html(body_html), "plain", "utf-8"))
        message.attach(MIMEText(body_html, "html", "utf-8"))

        try:
            async with httpx.AsyncClient(timeout=20.0) as client:
                response = await client.post(
                    _SPAMCHECK_URL,
                    json={"email": message.as_string(), "options": "long"},
                )
                response.raise_for_status()
                payload = response.json()
        except Exception as exc:  # noqa: BLE001 — the tester must degrade gracefully
            logger.warning("SpamCheck call failed: %s", exc)
            return {"available": False, "error": "Le service SpamAssassin ne répond pas — réessayez plus tard."}

        if not payload.get("success", False):
            return {"available": False, "error": payload.get("message", "Analyse impossible.")}

        score = float(payload.get("score", 0) or 0)
        rules = [
            {
                "score": rule.get("score"),
                "description": rule.get("description"),
            }
            for rule in payload.get("rules", [])
        ]
        # SpamAssassin convention: >= 5.0 is spam; we warn from 3.0.
        status = "ok" if score < 3.0 else ("warn" if score < 5.0 else "danger")
        return {"available": True, "score": score, "status": status, "rules": rules}

    def _local_checks(self, subject: str, body_html: str) -> list[dict[str, Any]]:
        """French-cold-email heuristics (each check → ok/warn/danger + advice).

        @param subject - Email subject.
        @param body_html - HTML body.
        @returns The checklist for the UI.
        """
        checks: list[dict[str, Any]] = []
        text = _strip_html(body_html)
        lowered_all = f"{subject} {text}".lower()

        # 1. Unsubscribe link (RGPD + Gmail/Yahoo requirement).
        has_unsubscribe = bool(
            re.search(r"d[ée]sinscri|unsubscribe|\{\{?\s*unsubscribe", body_html, flags=re.I)
        )
        checks.append(
            {
                "key": "unsubscribe",
                "label": "Lien de désinscription",
                "status": "ok" if has_unsubscribe else "danger",
                "detail": "Présent." if has_unsubscribe else "Absent — obligatoire (RGPD + exigence Gmail/Yahoo 2024).",
            }
        )

        # 2. Link count (cold emails should stay lean).
        link_count = len(re.findall(r"<a\s", body_html, flags=re.I))
        link_status = "ok" if link_count <= 3 else ("warn" if link_count <= 6 else "danger")
        checks.append(
            {
                "key": "links",
                "label": "Nombre de liens",
                "status": link_status,
                "detail": f"{link_count} lien(s) — visez 1 à 3 pour un cold email.",
            }
        )

        # 3. Shouty subject.
        letters = [c for c in subject if c.isalpha()]
        caps_ratio = (sum(1 for c in letters if c.isupper()) / len(letters)) if letters else 0.0
        exclamations = subject.count("!")
        shouty = caps_ratio > 0.4 or exclamations >= 2
        checks.append(
            {
                "key": "subject",
                "label": "Objet",
                "status": "warn" if shouty else "ok",
                "detail": "MAJUSCULES/exclamations excessives — signal spam classique." if shouty else "Sobre, rien à signaler.",
            }
        )

        # 4. Spammy vocabulary.
        hits = sorted({word for word in _SPAMMY_WORDS if word in lowered_all})
        checks.append(
            {
                "key": "vocabulary",
                "label": "Vocabulaire",
                "status": "ok" if not hits else ("warn" if len(hits) <= 2 else "danger"),
                "detail": "Aucun mot déclencheur." if not hits else f"Mots à risque : {', '.join(hits)}.",
            }
        )

        # 5. Text volume (image-only or one-liner emails look like spam).
        word_count = len(text.split())
        checks.append(
            {
                "key": "text_volume",
                "label": "Volume de texte",
                "status": "ok" if word_count >= 40 else "warn",
                "detail": f"{word_count} mots — en dessous de 40, les filtres manquent de matière.",
            }
        )

        # 6. HTML weight (heavy markup → promo folder).
        size_kb = len(body_html.encode("utf-8")) / 1024
        checks.append(
            {
                "key": "html_weight",
                "label": "Poids du HTML",
                "status": "ok" if size_kb <= 60 else ("warn" if size_kb <= 100 else "danger"),
                "detail": f"{size_kb:.0f} Ko — au-delà de 100 Ko, Gmail tronque le message.",
            }
        )

        return checks


email_spam_test_service = EmailSpamTestService()
