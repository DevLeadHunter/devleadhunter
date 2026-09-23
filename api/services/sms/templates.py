"""The SMS template library — one angle per message, written to fit one GSM-7 segment.

Mirrors the cold-email library (``seeders/email_template_seeder.py``) at SMS scale: a
first-contact family for prospects reached by SMS first (a mobile, no email) and a
follow-up family for prospects who ignored the email. Bodies stay short on purpose —
the STOP mention (14 chars) and the plain demo link (up to ~45 chars) already eat a
third of the 160-character budget, so every template says one thing, names the
business (in the text or through the link's slug), and signs with the sender's first
name. Trust rules baked in: an action at the first person (« j'ai préparé »), a reason
taken from the matching email, no imperative (« voici », « cliquez »), no urgency.
The mandatory STOP mention is appended at send time, never written here.

Variables: {salutation} {entreprise} {ville} {metier} {lien_demo} {lien_assistant}
{lien_video} {ancien_site} {prix} {signature}.
"""

from __future__ import annotations

import re
from dataclasses import dataclass

from enums.sms_template_category import SmsTemplateCategory

_VARIABLE_PATTERN: re.Pattern[str] = re.compile(r"\{([a-zA-Z_][a-zA-Z0-9_]*)\}")
_REPEATED_SPACES: re.Pattern[str] = re.compile(r" {2,}")

# Template used by the automated first contact (cold SMS worker and SMS campaigns).
DEFAULT_FIRST_CONTACT_KEY: str = "direct"

# Template a J+30 relance renders until the user picks another one in Paramètres → Relance SMS.
DEFAULT_FOLLOW_UP_KEY: str = "rappel-court"


@dataclass(frozen=True, slots=True)
class SmsTemplate:
    """One library template: a stable key, a display name, its touch and its body.

    A template built around ``{lien_video}`` names a ``fallback_key``: the template
    actually rendered for a prospect whose video is not generated (a video body with
    an empty link would send a broken message).
    """

    key: str
    name: str
    category: SmsTemplateCategory
    body: str
    fallback_key: str | None = None

    @property
    def variables(self) -> list[str]:
        """Unique variable names used by the body, in order of appearance."""
        seen: list[str] = []
        for name in _VARIABLE_PATTERN.findall(self.body):
            if name not in seen:
                seen.append(name)
        return seen

    def uses(self, variable: str) -> bool:
        """Whether the body references ``{variable}``.

        Args:
            variable: The variable name, without braces.

        Returns:
            ``True`` when the body needs that variable to render.
        """
        return f"{{{variable}}}" in self.body


SMS_TEMPLATE_LIBRARY: list[SmsTemplate] = [
    # ── Premier contact ──────────────────────────────────────────────────────
    SmsTemplate(
        key="direct",
        name="Direct",
        category=SmsTemplateCategory.FIRST_CONTACT,
        body="{salutation}, j'ai préparé un site pour {entreprise}, il est déjà en ligne : {lien_demo} {signature}",
    ),
    SmsTemplate(
        key="visibilite",
        name="Visibilité - on vous cherche",
        category=SmsTemplateCategory.FIRST_CONTACT,
        body="{salutation}, sans site, on ne vous trouve pas. J'ai préparé votre site : {lien_demo} {signature}",
    ),
    SmsTemplate(
        key="credibilite",
        name="Crédibilité - la première impression",
        category=SmsTemplateCategory.FIRST_CONTACT,
        body=(
            "{salutation}, on vous cherche en ligne avant d'appeler. J'ai préparé votre site : {lien_demo} {signature}"
        ),
    ),
    SmsTemplate(
        key="bouche-a-oreille",
        name="Bouche-à-oreille - on vous retrouve",
        category=SmsTemplateCategory.FIRST_CONTACT,
        body=(
            "{salutation}, un site aide vos clients à parler de vous. J'ai préparé votre site : {lien_demo} {signature}"
        ),
    ),
    SmsTemplate(
        key="video",
        name="Vidéo - je vous montre",
        category=SmsTemplateCategory.FIRST_CONTACT,
        body="{salutation}, j'ai préparé un site pour {entreprise}. En 30 s de vidéo : {lien_video} {signature}",
        fallback_key="direct",
    ),
    SmsTemplate(
        key="site-en-panne",
        name="Site en panne",
        category=SmsTemplateCategory.FIRST_CONTACT,
        body="{salutation}, {ancien_site} ne répond plus. J'ai préparé votre nouveau site : {lien_demo} {signature}",
    ),
    SmsTemplate(
        key="refonte",
        name="Refonte",
        category=SmsTemplateCategory.FIRST_CONTACT,
        body="{salutation}, j'ai modernisé le site de {entreprise}, comparez avec l'actuel : {lien_demo} {signature}",
    ),
    # ── Module Assistant IA — premier contact ────────────────────────────────
    SmsTemplate(
        key="assistant-24-7",
        name="Assistant IA - répond 24/7",
        category=SmsTemplateCategory.FIRST_CONTACT,
        body="{salutation}, j'ai préparé un assistant qui répond à vos clients 24h/24 : {lien_assistant} {signature}",
    ),
    SmsTemplate(
        key="assistant-langues",
        name="Assistant IA - dans leur langue",
        category=SmsTemplateCategory.FIRST_CONTACT,
        body=(
            "{salutation}, votre nouvel assistant répond à vos clients dans leur langue : {lien_assistant} {signature}"
        ),
    ),
    SmsTemplate(
        key="assistant-demandes",
        name="Assistant IA - demandes captées",
        category=SmsTemplateCategory.FIRST_CONTACT,
        body="{salutation}, mon assistant capte les demandes de vos clients, même la nuit : {lien_assistant} {signature}",
    ),
    # ── Relance J+30 (email resté sans réaction) ─────────────────────────────
    SmsTemplate(
        key="rappel-court",
        name="Rappel court",
        category=SmsTemplateCategory.FOLLOW_UP,
        body=(
            "{salutation}, le site envoyé par email est toujours en ligne : {lien_demo} "
            "Un mot me suffit, oui ou non. {signature}"
        ),
    ),
    SmsTemplate(
        key="offre-a-vie",
        name="Offre à vie",
        category=SmsTemplateCategory.FOLLOW_UP,
        body=(
            "{salutation}, votre site envoyé par email : {lien_demo} "
            "{prix} une fois, sans abonnement, et il est à vous. {signature}"
        ),
    ),
    SmsTemplate(
        key="offre-a-vie-video",
        name="Offre à vie - vidéo",
        category=SmsTemplateCategory.FOLLOW_UP,
        body=(
            "{salutation}, votre site envoyé par email, en vidéo : {lien_video} "
            "{prix} une fois, sans abonnement, à vie. {signature}"
        ),
        fallback_key="offre-a-vie",
    ),
    SmsTemplate(
        key="autonomie",
        name="Autonomie - vous gardez la main",
        category=SmsTemplateCategory.FOLLOW_UP,
        body=(
            "{salutation}, le site envoyé par email est en ligne : {lien_demo} "
            "Vous y changez tout, sans développeur. {signature}"
        ),
    ),
    SmsTemplate(
        key="urgence-douce",
        name="Urgence douce",
        category=SmsTemplateCategory.FOLLOW_UP,
        body=(
            "{salutation}, le site envoyé par email ne restera pas en ligne : {lien_demo} "
            "Un mot et je le garde. {signature}"
        ),
    ),
    SmsTemplate(
        key="site-en-panne-relance",
        name="Site en panne - relance",
        category=SmsTemplateCategory.FOLLOW_UP,
        body="{salutation}, {ancien_site} est toujours en erreur. Le nouveau, envoyé par email : {lien_demo} {signature}",
    ),
    SmsTemplate(
        key="refonte-relance",
        name="Refonte - relance",
        category=SmsTemplateCategory.FOLLOW_UP,
        body=(
            "{salutation}, la version modernisée de votre site, envoyée par email, est en ligne : "
            "{lien_demo} {signature}"
        ),
    ),
    SmsTemplate(
        key="assistant-relance",
        name="Assistant IA - relance",
        category=SmsTemplateCategory.FOLLOW_UP,
        body=(
            "{salutation}, l'assistant IA envoyé par email répond toujours à vos clients : {lien_assistant} {signature}"
        ),
    ),
    SmsTemplate(
        key="assistant-prix-cash",
        name="Assistant IA - le prix cash",
        category=SmsTemplateCategory.FOLLOW_UP,
        body="{salutation}, l'assistant envoyé par email est prêt : {lien_assistant} {prix_assistant}/mois, sans engagement. {signature}",
    ),
]


def list_sms_templates(category: SmsTemplateCategory | None = None) -> list[SmsTemplate]:
    """Return the library, optionally narrowed to one touch.

    Args:
        category: The touch to keep, or ``None`` for the whole library.

    Returns:
        The templates, in library order.
    """
    if category is None:
        return list(SMS_TEMPLATE_LIBRARY)
    return [template for template in SMS_TEMPLATE_LIBRARY if template.category == category]


def find_sms_template(key: str) -> SmsTemplate | None:
    """Return the template registered under *key*, or ``None``.

    Args:
        key: The template key (e.g. ``direct``).

    Returns:
        The template, or ``None`` when unknown.
    """
    return next((template for template in SMS_TEMPLATE_LIBRARY if template.key == key), None)


def resolve_sms_template(template: SmsTemplate, *, video_ready: bool) -> SmsTemplate:
    """The template to actually render: its fallback when it links a video the prospect lacks.

    Args:
        template: The template the user picked.
        video_ready: Whether the prospect's prospection video is generated.

    Returns:
        *template* itself, or its declared fallback when the body needs ``{lien_video}``
        and no video exists (the original when no fallback is declared).
    """
    if video_ready or not template.uses("lien_video") or template.fallback_key is None:
        return template
    return find_sms_template(template.fallback_key) or template


def render_sms_template(body: str, variables: dict[str, str]) -> str:
    """Substitute every ``{variable}`` of *body*; an unknown or empty variable renders as nothing.

    Args:
        body: The template body.
        variables: The variable name to value map.

    Returns:
        The rendered text, single-spaced and trimmed.
    """
    rendered = _VARIABLE_PATTERN.sub(lambda match: variables.get(match.group(1), ""), body)
    return _REPEATED_SPACES.sub(" ", rendered).strip()
