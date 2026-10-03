"""The SMS template library, written frank and short: one segment gives what was prepared, the price and a phone.

Mirrors the cold-email library (``seeders/email_template_seeder.py``) at SMS scale: a
first-contact family for prospects reached by SMS first (a mobile, no email) and a
follow-up family for prospects who ignored the first message. Every template fits ONE
GSM-7 segment in France (160 characters, opt-out mention included), billed as one SMS.
The sending service (``services/sms_service.py``) drops the first name when that saves a
segment, and allows two segments for what still overflows (a long business name, the
longer Swiss price and opt-out mention); the service messages (receptionist alerts) keep
one. Every template gives:
  - what was prepared, through ONE short link (``{lien_demo}``, ``{lien_video}``,
    ``{lien_assistant}``, ``{lien_video_assistant}``, ``{lien_carte}``, already in the
    branded ``demo.dibodev.fr/s/…`` form without scheme, handled by the callers);
  - the price (``{prix}`` once; ``{prix_assistant}`` or ``{prix_carte}`` a month);
  - how to answer: the alphanumeric sender (« Dibodev ») receives no reply, so the
    message ends on the sender's first name and public phone, « {signature}, {telephone} »
    (``users.contact_phone``, the one shown on the demo banner). A template using it needs
    that phone to be set.
The receptionist goes by its first name and « réceptionniste IA »: no word agrees with its
gender. The loyalty-card family (``carte-…``) names the iPhone (the card lives in Apple
Wallet) and never leaves without the prospect's card demo. No withdrawal day: the email
gives it.
Trust rules kept from the first library: an action at the first person, no imperative
(« voici », « cliquez », « ici »), no artificial urgency, GSM-7 transliteration at send
time. smsmode appends the opt-out mention at send time (``body.stop``), never written
here; the budget tests reserve its room in France (14 characters) and Switzerland (25).

Variables: {salutation} {entreprise} {ville} {metier} {lien_demo} {lien_assistant}
{lien_video} {lien_video_assistant} {lien_carte} {prenom_receptionniste} {receptionniste}
{assistant_virtuel} {ancien_site} {prix} {prix_assistant} {prix_carte} {date_expiration}
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

_SIGN_OFF: str = "{signature}, {telephone}"


@dataclass(frozen=True, slots=True)
class SmsTemplate:
    """One library template: a stable key, a display name, its touch and its body.

    A template built around ``{lien_video}`` or ``{lien_video_assistant}`` names a
    ``fallback_key``: the template actually rendered for a prospect whose video is not
    generated (a video body with an empty link would send a broken message).

    A relance written as a reminder of an email (« le site de mon email ») sets
    ``recalls_an_email``: it cannot follow a first SMS.
    """

    key: str
    name: str
    category: SmsTemplateCategory
    body: str
    fallback_key: str | None = None
    recalls_an_email: bool = False

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
        body="{salutation}, j'ai créé votre site : {lien_demo} {prix} une fois, sans abonnement. " + _SIGN_OFF,
    ),
    SmsTemplate(
        key="video",
        name="Vidéo - je vous montre",
        category=SmsTemplateCategory.FIRST_CONTACT,
        body="{salutation}, j'ai créé votre site, en vidéo : {lien_video} {prix} une fois, sans abonnement. "
        + _SIGN_OFF,
        fallback_key="direct",
    ),
    SmsTemplate(
        key="site-en-panne",
        name="Site en panne",
        category=SmsTemplateCategory.FIRST_CONTACT,
        body="{salutation}, {ancien_site} ne répond plus. Votre nouveau site : {lien_demo} {prix} une fois. "
        + _SIGN_OFF,
    ),
    SmsTemplate(
        key="refonte",
        name="Refonte",
        category=SmsTemplateCategory.FIRST_CONTACT,
        body="{salutation}, j'ai refait votre site en plus moderne : {lien_demo} {prix} une fois. " + _SIGN_OFF,
    ),
    SmsTemplate(
        key="assistant-24-7",
        name="Réceptionniste IA - le soir, personne ne répond",
        category=SmsTemplateCategory.FIRST_CONTACT,
        body=(
            "{salutation}, {prenom_receptionniste}, votre réceptionniste IA, répond le soir : {lien_assistant} "
            "{prix_assistant}/mois. " + _SIGN_OFF
        ),
    ),
    SmsTemplate(
        key="assistant-langues",
        name="Réceptionniste IA - dans leur langue",
        category=SmsTemplateCategory.FIRST_CONTACT,
        body=(
            "{salutation}, {prenom_receptionniste}, votre réceptionniste IA multilingue : {lien_assistant} "
            "{prix_assistant}/mois. " + _SIGN_OFF
        ),
    ),
    SmsTemplate(
        key="assistant-demandes",
        name="Réceptionniste IA - devis par photo",
        category=SmsTemplateCategory.FIRST_CONTACT,
        body=(
            "{salutation}, {prenom_receptionniste}, réceptionniste IA, prend vos demandes par photo : {lien_assistant} "
            "{prix_assistant}/mois. " + _SIGN_OFF
        ),
    ),
    SmsTemplate(
        key="assistant-video",
        name="Réceptionniste IA - en vidéo",
        category=SmsTemplateCategory.FIRST_CONTACT,
        body=(
            "{salutation}, {prenom_receptionniste}, votre réceptionniste IA, en 30 s de vidéo : {lien_video_assistant} "
            "{prix_assistant}/mois. " + _SIGN_OFF
        ),
        fallback_key="assistant-24-7",
    ),
    SmsTemplate(
        key="carte-direct",
        name="Carte fidélité - premier contact franc",
        category=SmsTemplateCategory.FIRST_CONTACT,
        body=(
            "{salutation}, j'ai créé votre carte fidélité iPhone : {lien_carte} {prix_carte}/mois, 1er mois offert. "
            + _SIGN_OFF
        ),
    ),
    SmsTemplate(
        key="carte-sans-appli",
        name="Carte fidélité - sans appli",
        category=SmsTemplateCategory.FIRST_CONTACT,
        body=(
            "{salutation}, votre carte fidélité iPhone sans appli : {lien_carte} {prix_carte}/mois, essai 1 mois. "
            + _SIGN_OFF
        ),
    ),
    SmsTemplate(
        key="rappel-court",
        name="Rappel court",
        category=SmsTemplateCategory.FOLLOW_UP,
        body="{salutation}, le site de mon email est toujours en ligne : {lien_demo} {prix} une fois. " + _SIGN_OFF,
        recalls_an_email=True,
    ),
    SmsTemplate(
        key="offre-a-vie",
        name="Offre à vie",
        category=SmsTemplateCategory.FOLLOW_UP,
        body="{salutation}, le site envoyé par email : {lien_demo} {prix} une fois et il est à vous. " + _SIGN_OFF,
        recalls_an_email=True,
    ),
    SmsTemplate(
        key="offre-a-vie-video",
        name="Offre à vie - vidéo",
        category=SmsTemplateCategory.FOLLOW_UP,
        body="{salutation}, votre site en vidéo : {lien_video} {prix} une fois et il est à vous. " + _SIGN_OFF,
        fallback_key="offre-a-vie",
    ),
    SmsTemplate(
        key="site-en-panne-relance",
        name="Site en panne - relance",
        category=SmsTemplateCategory.FOLLOW_UP,
        body="{salutation}, {ancien_site} est toujours en panne. Le nouveau : {lien_demo} {prix} une fois. "
        + _SIGN_OFF,
    ),
    SmsTemplate(
        key="refonte-relance",
        name="Refonte - relance",
        category=SmsTemplateCategory.FOLLOW_UP,
        body="{salutation}, votre nouveau site est toujours en ligne : {lien_demo} {prix} une fois. " + _SIGN_OFF,
    ),
    SmsTemplate(
        key="assistant-relance",
        name="Réceptionniste IA - relance",
        category=SmsTemplateCategory.FOLLOW_UP,
        body=(
            "{salutation}, après mon email, {prenom_receptionniste} (IA) répond toujours : {lien_assistant} "
            "{prix_assistant}/mois. " + _SIGN_OFF
        ),
        recalls_an_email=True,
    ),
    SmsTemplate(
        key="assistant-relance-video",
        name="Réceptionniste IA - relance vidéo",
        category=SmsTemplateCategory.FOLLOW_UP,
        body=(
            "{salutation}, la vidéo de mon email : {prenom_receptionniste}, réceptionniste IA : {lien_video_assistant} "
            "{prix_assistant}/mois. " + _SIGN_OFF
        ),
        fallback_key="assistant-relance",
        recalls_an_email=True,
    ),
    SmsTemplate(
        key="assistant-prix-cash",
        name="Réceptionniste IA - le prix, sans détour",
        category=SmsTemplateCategory.FOLLOW_UP,
        body=(
            "{salutation}, {prenom_receptionniste}, votre réceptionniste IA : {prix_assistant}/mois, 1er mois "
            "remboursé. {lien_assistant} " + _SIGN_OFF
        ),
    ),
    SmsTemplate(
        key="carte-relance",
        name="Carte fidélité - relance franche",
        category=SmsTemplateCategory.FOLLOW_UP,
        body=(
            "{salutation}, la carte fidélité iPhone de mon email : {lien_carte} {prix_carte}/mois, 1er mois offert. "
            + _SIGN_OFF
        ),
        recalls_an_email=True,
    ),
    SmsTemplate(
        key="carte-rappel-court",
        name="Carte fidélité - rappel court",
        category=SmsTemplateCategory.FOLLOW_UP,
        body=(
            "{salutation}, votre carte fidélité iPhone : {lien_carte} {prix_carte}/mois sans engagement. " + _SIGN_OFF
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
