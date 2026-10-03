"""The SMS template library, written frank: one message says who writes, what was prepared, the price and how to answer.

Mirrors the cold-email library (``seeders/email_template_seeder.py``) at SMS scale: a
first-contact family for prospects reached by SMS first (a mobile, no email) and a
follow-up family for prospects who ignored the email. A prospecting SMS may take TWO
GSM-7 segments (306 characters, opt-out mention included): a frank message does not fit
in one. The sending service (``services/sms_service.py``) allows two
segments for a send to a prospect; the service messages (receptionist alerts) keep
one. Every frank template says:
  - who writes (« je fais des sites web », the receptionist is « une assistante
    virtuelle (une IA) ») and signs with the sender's first name;
  - what was prepared, through ONE short link (``{lien_demo}``, ``{lien_video}``,
    ``{lien_assistant}``, ``{lien_video_assistant}``, already in the branded
    ``demo.dibodev.fr/s/…`` form without scheme, handled by the callers);
  - the price (``{prix}`` once, no subscription; ``{prix_assistant}`` a month, no
    commitment, first month satisfied or refunded);
  - how to answer: the alphanumeric sender (« Dibodev ») receives no reply, so the
    message gives the sender's public phone, ``{telephone}`` (``users.contact_phone``,
    the one shown on the demo banner). A template using it needs that phone to be set.
Trust rules kept from the first library: an action at the first person, no imperative
(« voici », « cliquez », « ici »), no artificial urgency, GSM-7 transliteration at send
time. smsmode appends the opt-out mention at send time (``body.stop``), never written
here; the budget tests reserve its room in France (14 characters) and Switzerland (25).

Variables: {salutation} {entreprise} {ville} {metier} {lien_demo} {lien_assistant}
{lien_video} {lien_video_assistant} {prenom_receptionniste} {ancien_site} {prix} {prix_assistant}
{telephone} {signature}.
"""

from __future__ import annotations

import re
from dataclasses import dataclass

from enums.sms_template_category import SmsTemplateCategory
from services.regional_lexicon import RegionalLexicon

_VARIABLE_PATTERN: re.Pattern[str] = re.compile(r"\{([a-zA-Z_][a-zA-Z0-9_]*)\}")
_REPEATED_SPACES: re.Pattern[str] = re.compile(r" {2,}")

# Template used by the automated first contact (cold SMS worker and SMS campaigns).
DEFAULT_FIRST_CONTACT_KEY: str = "direct"

# Template a J+30 relance renders until the user picks another one in Paramètres → Relance SMS.
DEFAULT_FOLLOW_UP_KEY: str = "rappel-court"

_WEBSITE_PRICE_LINE: str = "C'est {prix}, une seule fois, sans abonnement."
_RECEPTIONIST_PRICE_LINE: str = "{prix_assistant}/mois sans engagement, 1er mois satisfait ou remboursé."
_ASK_WITH_PHONE: str = "Un mot me suffit, oui ou non, au {telephone}. {signature}"
_RECEPTIONIST_INTRO: str = "j'ai préparé {prenom_receptionniste}, votre réceptionniste virtuelle (une IA)"


@dataclass(frozen=True, slots=True)
class SmsTemplate:
    """One library template: a stable key, a display name, its touch and its body.

    A template built around ``{lien_video}`` or ``{lien_video_assistant}`` names a
    ``fallback_key``: the template actually rendered for a prospect whose video is not
    generated (a video body with an empty link would send a broken message).
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
    SmsTemplate(
        key="direct",
        name="Franc - premier contact",
        category=SmsTemplateCategory.FIRST_CONTACT,
        body=(
            "{salutation}, je fais des sites web et j'ai construit celui de {entreprise}, il est en ligne : "
            "{lien_demo} " + _WEBSITE_PRICE_LINE + " " + _ASK_WITH_PHONE
        ),
    ),
    SmsTemplate(
        key="video",
        name="Vidéo - je vous montre",
        category=SmsTemplateCategory.FIRST_CONTACT,
        body=(
            "{salutation}, je fais des sites web et j'ai construit celui de {entreprise}. En 30 s de vidéo : "
            "{lien_video} " + _WEBSITE_PRICE_LINE + " " + _ASK_WITH_PHONE
        ),
        fallback_key="direct",
    ),
    SmsTemplate(
        key="site-en-panne",
        name="Site en panne",
        category=SmsTemplateCategory.FIRST_CONTACT,
        body=(
            "{salutation}, {ancien_site} ne répond plus. Je fais des sites web et j'en ai construit un nouveau, il "
            "est en ligne : {lien_demo} " + _WEBSITE_PRICE_LINE + " " + _ASK_WITH_PHONE
        ),
    ),
    SmsTemplate(
        key="refonte",
        name="Refonte",
        category=SmsTemplateCategory.FIRST_CONTACT,
        body=(
            "{salutation}, je fais des sites web et j'ai construit une version plus moderne de votre site, à "
            "comparer avec l'actuel : {lien_demo} " + _WEBSITE_PRICE_LINE + " " + _ASK_WITH_PHONE
        ),
    ),
    SmsTemplate(
        key="assistant-24-7",
        name="Réceptionniste IA - le soir, personne ne répond",
        category=SmsTemplateCategory.FIRST_CONTACT,
        body=(
            "{salutation}, "
            + _RECEPTIONIST_INTRO
            + " : le soir, elle répond. {lien_assistant} "
            + _RECEPTIONIST_PRICE_LINE
            + " "
            + _ASK_WITH_PHONE
        ),
    ),
    SmsTemplate(
        key="assistant-langues",
        name="Réceptionniste IA - dans leur langue",
        category=SmsTemplateCategory.FIRST_CONTACT,
        body=(
            "{salutation}, " + _RECEPTIONIST_INTRO + ", qui parle la langue du client. "
            "{lien_assistant} " + _RECEPTIONIST_PRICE_LINE + " " + _ASK_WITH_PHONE
        ),
    ),
    SmsTemplate(
        key="assistant-demandes",
        name="Réceptionniste IA - devis par photo",
        category=SmsTemplateCategory.FIRST_CONTACT,
        body=(
            "{salutation}, " + _RECEPTIONIST_INTRO + " : demande de devis par photo. "
            "{lien_assistant} " + _RECEPTIONIST_PRICE_LINE + " " + _ASK_WITH_PHONE
        ),
    ),
    SmsTemplate(
        key="assistant-video",
        name="Réceptionniste IA - en vidéo",
        category=SmsTemplateCategory.FIRST_CONTACT,
        body=(
            "{salutation}, "
            + _RECEPTIONIST_INTRO
            + ". En 30 s de vidéo : {lien_video_assistant} "
            + _RECEPTIONIST_PRICE_LINE
            + " "
            + _ASK_WITH_PHONE
        ),
        fallback_key="assistant-24-7",
    ),
    SmsTemplate(
        key="rappel-court",
        name="Rappel court",
        category=SmsTemplateCategory.FOLLOW_UP,
        body=(
            "{salutation}, le site envoyé par email est toujours en ligne : {lien_demo} C'est {prix}, une seule "
            "fois. " + _ASK_WITH_PHONE
        ),
    ),
    SmsTemplate(
        key="offre-a-vie",
        name="Offre à vie",
        category=SmsTemplateCategory.FOLLOW_UP,
        body=(
            "{salutation}, le site de {entreprise} envoyé par email reste en ligne : {lien_demo} "
            "{prix} une seule fois, sans abonnement, il est à vous, sur votre propre adresse. " + _ASK_WITH_PHONE
        ),
    ),
    SmsTemplate(
        key="offre-a-vie-video",
        name="Offre à vie - vidéo",
        category=SmsTemplateCategory.FOLLOW_UP,
        body=(
            "{salutation}, le site envoyé par email, en 30 s de vidéo : {lien_video} "
            "{prix} une seule fois, sans abonnement, et il est à vous. " + _ASK_WITH_PHONE
        ),
        fallback_key="offre-a-vie",
    ),
    SmsTemplate(
        key="site-en-panne-relance",
        name="Site en panne - relance",
        category=SmsTemplateCategory.FOLLOW_UP,
        body=(
            "{salutation}, {ancien_site} est toujours en erreur. Le nouveau site, envoyé par email, est en ligne : "
            "{lien_demo} " + _WEBSITE_PRICE_LINE + " " + _ASK_WITH_PHONE
        ),
    ),
    SmsTemplate(
        key="refonte-relance",
        name="Refonte - relance",
        category=SmsTemplateCategory.FOLLOW_UP,
        body=(
            "{salutation}, la nouvelle version de votre site, envoyée par email, est en ligne : {lien_demo} "
            + _WEBSITE_PRICE_LINE
            + " "
            + _ASK_WITH_PHONE
        ),
    ),
    SmsTemplate(
        key="assistant-relance",
        name="Réceptionniste IA - relance",
        category=SmsTemplateCategory.FOLLOW_UP,
        body=(
            "{salutation}, après mon email, {prenom_receptionniste}, votre réceptionniste virtuelle (une IA), répond "
            "toujours : {lien_assistant} " + _RECEPTIONIST_PRICE_LINE + " " + _ASK_WITH_PHONE
        ),
    ),
    SmsTemplate(
        key="assistant-relance-video",
        name="Réceptionniste IA - relance vidéo",
        category=SmsTemplateCategory.FOLLOW_UP,
        body=(
            "{salutation}, la vidéo de mon email : votre réceptionniste virtuelle (une IA) en 30 s : "
            "{lien_video_assistant} " + _RECEPTIONIST_PRICE_LINE + " " + _ASK_WITH_PHONE
        ),
        fallback_key="assistant-relance",
    ),
    SmsTemplate(
        key="assistant-prix-cash",
        name="Réceptionniste IA - le prix, sans détour",
        category=SmsTemplateCategory.FOLLOW_UP,
        body=(
            "{salutation}, le prix de mon email, sans détour : {prix_assistant}/mois pour {prenom_receptionniste}, "
            "votre réceptionniste virtuelle (une IA). Sans engagement, 1er mois satisfait ou remboursé. "
            "{lien_assistant} " + _ASK_WITH_PHONE
        ),
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


def resolve_sms_template(
    template: SmsTemplate, *, video_ready: bool, assistant_video_ready: bool = False
) -> SmsTemplate:
    """The template to actually render: its fallback when it links a video the prospect lacks.

    Args:
        template: The template the user picked.
        video_ready: Whether the prospect's site prospection video is generated.
        assistant_video_ready: Whether the prospect's receptionist video is generated.

    Returns:
        *template* itself, or its declared fallback when the body needs ``{lien_video}`` or
        ``{lien_video_assistant}`` and that video does not exist (the original when no fallback is declared).
    """
    is_site_video_missing = template.uses("lien_video") and not video_ready
    is_assistant_video_missing = template.uses("lien_video_assistant") and not assistant_video_ready
    if template.fallback_key is None or not (is_site_video_missing or is_assistant_video_missing):
        return template
    return find_sms_template(template.fallback_key) or template


def render_sms_template(body: str, variables: dict[str, str]) -> str:
    """Substitute every ``{variable}`` of *body*; an unknown or empty variable renders as nothing.

    The text is then written in the regional French of the country a prospect's map carries.

    Args:
        body: The template body.
        variables: The variable name to value map.

    Returns:
        The rendered text, single-spaced and trimmed.
    """
    rendered = _VARIABLE_PATTERN.sub(lambda match: variables.get(match.group(1), ""), body)
    return RegionalLexicon.localize_rendered(_REPEATED_SPACES.sub(" ", rendered).strip(), variables)
