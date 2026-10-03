"""Email template seeder: the canonical cold-email library, written frank.

Every template follows the frank rule (the frank first contact of September 2026 got 35 % of
real clicks where the earlier pitch emails got one or two on 27): the prospect reads who writes, what was
prepared for him (one link), the price in the very first message, the real day the demo goes
offline, how to say no, and a single light ask. Rules baked in:
  - Subjects: short, lower-case, like a mail between two people (« le site de {entreprise} »),
    never naming a big brand (Apple hard-bounces "Google" in the subject).
  - Bodies end NUDE: no sign-off line and no ``{signature}`` token. The optional signature block
    is appended at send time by the "Inclure une signature" switch (see
    ``services/email_signatures.py``), so a hard-coded sign-off would double up.
  - Plain words: no em or en dash, no emoji, never « voici », « cliquez » or « ici ».
  - The price always goes through a variable: ``{prix}`` for a website (the user's configured
    sale price), ``{prix_assistant}`` for the receptionist (the user's monthly price). The
    Swiss variant (« ≈ 470 CHF ») is NOT a separate template: ``{prix}`` is resolved per
    country at send time, so one template serves every country.
  - The withdrawal day is ``{date_expiration}``, resolved from the demo actually linked.
  - One door per email: a demo link, or the video thumbnail for the « vidéo » templates
    (``{vignette_video}`` / ``{vignette_video_assistant}``, held back by the queue until the
    video exists).
  - The receptionist templates say plainly that the receptionist is a virtual assistant (an
    AI) living at an address of its own (a hosted page, the prospect needs no website), and
    that the first month is satisfied or refunded. Half the casting is masculine (Hugo, Marc,
    Nathan): the gendered words come from ``{receptionniste}`` and ``{assistant_virtuel}``,
    and the text names the receptionist by first name rather than « il » or « elle ».
  - A follow-up says at most « Dernier mail de ma part », never the last message: a J+30 SMS
    may still come. Giving time replaces begging for an answer (« Besoin d'y réfléchir ? Prenez
    votre temps »).

Variables: {salutation} {prenom} {nom} {entreprise} {ville} {metier} {lien_demo}
{lien_assistant} {prenom_receptionniste} {receptionniste} {assistant_virtuel} {lien_video}
{vignette_video} {vignette_video_assistant} {ancien_site} {prix} {prix_assistant} {date_expiration}.

``sort_order`` (higher = pinned) marks the recommended templates at the top of the list: the
frank first contact, the frank follow-ups (with and without video), the short reminder and its
video twin, then the receptionist templates.

Safe to re-run: templates are matched by (user_id, name) and skipped if present, so the seeder
only APPENDS. The prod cut-over to this frank library (rename the receptionist templates in
place, rewrite the kept angles, deactivate the never-used ones) lives in the
``reseed_frank_email_template_library`` migration, which consumes ``EMAIL_TEMPLATE_LIBRARY``.
"""

from __future__ import annotations

import json
import re

from enums.email_template_category import EmailTemplateCategory

_FIRST = EmailTemplateCategory.FIRST_EMAIL.value
_FOLLOW = EmailTemplateCategory.FOLLOW_UP.value

_WEBSITE_PRICE_LINE = (
    "<p>C'est {prix}, une seule fois. Pas d'abonnement : je le mets sur votre propre adresse, et vous "
    "modifiez ensuite textes et photos vous-même, sans dépendre de personne.</p>"
)
_WEBSITE_EXPIRY_LINE = "<p>Je le garde en ligne jusqu'au {date_expiration}. Après, je le retire.</p>"
_SINGLE_ASK_WITH_EXIT = (
    "<p>Un mot me suffit : oui, non, ou une question. Si c'est non, dites-le-moi et je ne vous recontacte plus.</p>"
)
_SHORT_ASK_WITH_EXIT = "<p>Un mot me suffit, même un non.</p>"
_WEBSITE_TIME_TO_THINK_LINE = (
    "<p>Besoin d'y réfléchir ? Prenez votre temps : il reste en ligne jusqu'au {date_expiration}.</p>"
)
_RECEPTIONIST_PRICE_LINE = (
    "<p>C'est {prix_assistant} par mois, sans engagement. Le premier mois est satisfait ou remboursé.</p>"
)
_RECEPTIONIST_EXPIRY_LINE = "<p>La démo reste en ligne jusqu'au {date_expiration}. Après, je la retire.</p>"
_RECEPTIONIST_TIME_TO_THINK_LINE = (
    "<p>Besoin d'y réfléchir ? Prenez votre temps : la démo reste en ligne jusqu'au {date_expiration}.</p>"
)

# The canonical library. ``sort_order`` > 0 = recommended (pinned to the top of the list).
EMAIL_TEMPLATE_LIBRARY: list[dict[str, object]] = [
    {
        "name": "Franc - premier contact",
        "category": _FIRST,
        "sort_order": 100,
        "subject": "le site de {entreprise}",
        "body_html": (
            "<p>{salutation},</p>"
            "<p>Je fais des sites web, et j'ai construit celui de {entreprise}. Il est déjà en ligne : {lien_demo}</p>"
            + _WEBSITE_PRICE_LINE
            + _WEBSITE_EXPIRY_LINE
            + _SINGLE_ASK_WITH_EXIT
        ),
    },
    {
        "name": "Visibilité - on vous cherche",
        "category": _FIRST,
        "sort_order": 0,
        "subject": "{entreprise} sur internet",
        "body_html": (
            "<p>{salutation},</p>"
            "<p>Quand quelqu'un cherche un {metier} à {ville}, il tombe sur ceux qui ont un site. Je fais des "
            "sites web, et j'ai construit celui de {entreprise}. Il est déjà en ligne : {lien_demo}</p>"
            + _WEBSITE_PRICE_LINE
            + _WEBSITE_EXPIRY_LINE
            + _SINGLE_ASK_WITH_EXIT
        ),
    },
    {
        "name": "Crédibilité - la première impression",
        "category": _FIRST,
        "sort_order": 0,
        "subject": "avant qu'on vous appelle",
        "body_html": (
            "<p>{salutation},</p>"
            "<p>Avant d'appeler un {metier}, on regarde son site. Je fais des sites web, et j'ai construit celui "
            "de {entreprise} pour qu'on voie votre travail avant de vous appeler. Il est déjà en ligne : "
            "{lien_demo}</p>" + _WEBSITE_PRICE_LINE + _WEBSITE_EXPIRY_LINE + _SINGLE_ASK_WITH_EXIT
        ),
    },
    {
        "name": "Vidéo - je vous montre",
        "category": _FIRST,
        "sort_order": 0,
        "subject": "le site de {entreprise}, en vidéo",
        "body_html": (
            "<p>{salutation},</p>"
            "<p>Je fais des sites web, et j'ai construit celui de {entreprise}. Plutôt que de l'expliquer, je "
            "vous le montre en 30 secondes :</p>"
            "{vignette_video}" + _WEBSITE_PRICE_LINE + _WEBSITE_EXPIRY_LINE + _SINGLE_ASK_WITH_EXIT
        ),
    },
    {
        "name": "Site en panne - premier email",
        "category": _FIRST,
        "sort_order": 0,
        "subject": "votre site ne répond plus",
        "body_html": (
            "<p>{salutation},</p>"
            "<p>En cherchant {entreprise}, je suis tombé sur {ancien_site} : il ne répond plus. Je fais des sites "
            "web, et j'en ai construit un nouveau pour vous. Il est déjà en ligne : {lien_demo}</p>"
            "<p>C'est {prix}, une seule fois. Pas d'abonnement : je le mets sur votre adresse actuelle, et vous "
            "modifiez ensuite textes et photos vous-même, sans dépendre de personne.</p>"
            + _WEBSITE_EXPIRY_LINE
            + _SINGLE_ASK_WITH_EXIT
        ),
    },
    {
        "name": "Refonte - premier email",
        "category": _FIRST,
        "sort_order": 0,
        "subject": "une nouvelle version de votre site",
        "body_html": (
            "<p>{salutation},</p>"
            "<p>Je fais des sites web. Je suis tombé sur celui de {entreprise}, et j'en ai construit une version "
            "plus moderne, à comparer avec l'actuel. Elle est déjà en ligne : {lien_demo}</p>"
            "<p>C'est {prix}, une seule fois. Pas d'abonnement : je la mets sur votre adresse actuelle, et vous "
            "modifiez ensuite textes et photos vous-même, sans dépendre de personne.</p>"
            "<p>Je la garde en ligne jusqu'au {date_expiration}. Après, je la retire.</p>" + _SINGLE_ASK_WITH_EXIT
        ),
    },
    {
        "name": "Franc - relance",
        "category": _FOLLOW,
        "sort_order": 90,
        "subject": "avant que je le retire",
        "body_html": (
            "<p>{salutation},</p>"
            "<p>Dernier mail de ma part. Le site de {entreprise} est toujours en ligne : {lien_demo}</p>"
            "<p>Si vous le voulez, c'est {prix}, une seule fois. Sinon, rien à faire.</p>" + _WEBSITE_TIME_TO_THINK_LINE
        ),
    },
    {
        "name": "Franc - relance vidéo",
        "category": _FOLLOW,
        "sort_order": 85,
        "subject": "le site de {entreprise}, en vidéo",
        "body_html": (
            "<p>{salutation},</p>"
            "<p>Je vous ai écrit il y a quelques jours au sujet du site de {entreprise}. Cette fois, je vous le "
            "montre en 30 secondes :</p>"
            "{vignette_video}"
            "<p>Si vous le voulez, c'est {prix}, une seule fois, sans abonnement. Sinon, rien à faire.</p>"
            + _WEBSITE_TIME_TO_THINK_LINE
        ),
    },
    # A first email on purpose: it opens its own campaign towards the prospects whose demo is about to expire.
    {
        "name": "Franc - dernier rappel avant retrait",
        "category": _FIRST,
        "sort_order": 0,
        "subject": "votre site sera retiré le {date_expiration}",
        "body_html": (
            "<p>{salutation},</p>"
            "<p>Le site que j'ai construit pour {entreprise} sera retiré le {date_expiration}. Il est encore en "
            "ligne : {lien_demo}</p>"
            "<p>Si vous voulez le garder, c'est {prix}, une seule fois. Je le mets sur votre propre adresse, et "
            "vous pourrez ensuite tout modifier vous-même.</p>" + _SHORT_ASK_WITH_EXIT
        ),
    },
    {
        "name": "Rappel court",
        "category": _FOLLOW,
        "sort_order": 80,
        "subject": "vous avez vu votre site ?",
        "body_html": (
            "<p>{salutation},</p>"
            "<p>Le site de {entreprise} est toujours en ligne : {lien_demo}</p>"
            "<p>C'est {prix}, une seule fois, sans abonnement. Je le retire le {date_expiration}.</p>"
            + _SHORT_ASK_WITH_EXIT
        ),
    },
    {
        "name": "Rappel court - vidéo",
        "category": _FOLLOW,
        "sort_order": 75,
        "subject": "votre site, en 30 secondes",
        "body_html": (
            "<p>{salutation},</p>"
            "<p>Le site de {entreprise}, en 30 secondes :</p>"
            "{vignette_video}"
            "<p>C'est {prix}, une seule fois, sans abonnement. Je le retire le {date_expiration}.</p>"
            + _SHORT_ASK_WITH_EXIT
        ),
    },
    {
        "name": "Offre à vie",
        "category": _FOLLOW,
        "sort_order": 0,
        "subject": "un seul paiement, le site est à vous",
        "body_html": (
            "<p>{salutation},</p>"
            "<p>Le site de {entreprise} est toujours en ligne : {lien_demo}</p>"
            "<p>{prix} une seule fois, et il est à vous : pas d'abonnement, vous ne me repayez jamais, et je "
            "m'occupe de la mise en ligne sur votre propre adresse.</p>"
            "<p>Je le garde jusqu'au {date_expiration}. Après, je le retire.</p>" + _SHORT_ASK_WITH_EXIT
        ),
    },
    {
        "name": "Refonte - relance",
        "category": _FOLLOW,
        "sort_order": 0,
        "subject": "votre ancien site ou le nouveau ?",
        "body_html": (
            "<p>{salutation},</p>"
            "<p>La nouvelle version du site de {entreprise} est toujours en ligne, à comparer avec l'actuel : "
            "{lien_demo}</p>"
            "<p>C'est {prix}, une seule fois, sans abonnement. Je la mets sur votre adresse actuelle, et vous "
            "gardez la main sur tout le contenu.</p>"
            "<p>Je la garde en ligne jusqu'au {date_expiration}. Après, je la retire.</p>" + _SHORT_ASK_WITH_EXIT
        ),
    },
    {
        "name": "Réceptionniste IA - franc",
        "category": _FIRST,
        "sort_order": 16,
        "subject": "{receptionniste} pour {entreprise}",
        "body_html": (
            "<p>{salutation},</p>"
            "<p>Je fais des outils web pour les artisans et les commerçants, et j'ai préparé "
            "{prenom_receptionniste} pour {entreprise} : {assistant_virtuel} (IA) qui répond à vos clients quand "
            "vous ne pouvez pas. {prenom_receptionniste} est déjà en ligne, à une adresse à son nom : "
            "{lien_assistant}</p>" + _RECEPTIONIST_PRICE_LINE + _RECEPTIONIST_EXPIRY_LINE + _SINGLE_ASK_WITH_EXIT
        ),
    },
    # Everything the receptionist does, in keywords: the prospect sees it is more than a chatbot.
    {
        "name": "Réceptionniste IA - en bref",
        "category": _FIRST,
        "sort_order": 15,
        "subject": "votre réceptionniste, en bref",
        "body_html": (
            "<p>{salutation},</p>"
            "<p>Je fais des outils web pour les artisans et les commerçants, et j'ai préparé "
            "{prenom_receptionniste} pour {entreprise} : {assistant_virtuel} (IA). En bref :</p>"
            "<ul>"
            "<li>Réponses à vos clients 24 h sur 24, dans leur langue</li>"
            "<li>Demandes de devis avec photo</li>"
            "<li>Prise de rendez-vous dans votre agenda Google</li>"
            "<li>Chaque demande transmise par mail, les urgentes aussi par SMS</li>"
            "<li>Uniquement vos vraies informations : rien d'inventé</li>"
            "<li>Une adresse à son nom pour votre fiche Google, pas besoin de site</li>"
            "<li>Un bilan chaque mois</li>"
            "</ul>"
            "<p>{prenom_receptionniste} est déjà en ligne : {lien_assistant}</p>"
            + _RECEPTIONIST_PRICE_LINE
            + _RECEPTIONIST_EXPIRY_LINE
            + _SINGLE_ASK_WITH_EXIT
        ),
    },
    {
        "name": "Réceptionniste IA - le soir, personne ne répond",
        "category": _FIRST,
        "sort_order": 10,
        "subject": "vos clients du soir",
        "body_html": (
            "<p>{salutation},</p>"
            "<p>Je fais des outils web pour les artisans et les commerçants, et j'ai préparé "
            "{prenom_receptionniste} pour {entreprise} : {assistant_virtuel} (IA) qui, le soir et le week-end, "
            "répond tout de suite à vos clients et vous transmet chaque demande. {prenom_receptionniste} est déjà "
            "en ligne, à une adresse à son nom : {lien_assistant}</p>"
            "{vignette_video_assistant}" + _RECEPTIONIST_PRICE_LINE + _RECEPTIONIST_EXPIRY_LINE + _SINGLE_ASK_WITH_EXIT
        ),
    },
    {
        "name": "Réceptionniste IA - devis par photo",
        "category": _FIRST,
        "sort_order": 11,
        "subject": "une photo, une demande de devis",
        "body_html": (
            "<p>{salutation},</p>"
            "<p>Je fais des outils web pour les artisans et les commerçants, et j'ai préparé "
            "{prenom_receptionniste} pour {entreprise} : {assistant_virtuel} (IA). Un client envoie la photo de son "
            "problème à 22 h, et vous recevez une demande de devis complète, avec les bonnes questions déjà posées. "
            "{prenom_receptionniste} est déjà en ligne, à une adresse à son nom, et accepte n'importe quelle "
            "photo : {lien_assistant}</p>"
            "{vignette_video_assistant}" + _RECEPTIONIST_PRICE_LINE + _RECEPTIONIST_EXPIRY_LINE + _SINGLE_ASK_WITH_EXIT
        ),
    },
    {
        "name": "Réceptionniste IA - dans leur langue",
        "category": _FIRST,
        "sort_order": 12,
        "subject": "vos clients, dans leur langue",
        "body_html": (
            "<p>{salutation},</p>"
            "<p>Une partie des clients de {entreprise} n'ose pas écrire en français et repart sans rien demander. "
            "Je fais des outils web pour les artisans et les commerçants, et j'ai préparé pour vous "
            "{prenom_receptionniste} : {assistant_virtuel} (IA) qui répond à vos clients dans leur langue, "
            "24 h sur 24, et vous transmet leur demande en français. {prenom_receptionniste} est déjà en ligne, à "
            "une adresse à son nom : {lien_assistant}</p>"
            "{vignette_video_assistant}" + _RECEPTIONIST_PRICE_LINE + _RECEPTIONIST_EXPIRY_LINE + _SINGLE_ASK_WITH_EXIT
        ),
    },
    # The video as its only door, held back until generated.
    {
        "name": "Réceptionniste IA - en vidéo",
        "category": _FIRST,
        "sort_order": 9,
        "subject": "votre réceptionniste, en vidéo",
        "body_html": (
            "<p>{salutation},</p>"
            "<p>Je fais des outils web pour les artisans et les commerçants, et j'ai préparé "
            "{prenom_receptionniste} pour {entreprise} : {assistant_virtuel} (IA) qui répond à vos clients le soir "
            "et le week-end et vous transmet chaque demande. Je vous montre comment ça marche, en 30 secondes :</p>"
            "{vignette_video_assistant}" + _RECEPTIONIST_PRICE_LINE + _RECEPTIONIST_EXPIRY_LINE + _SINGLE_ASK_WITH_EXIT
        ),
    },
    {
        "name": "Réceptionniste IA - relance",
        "category": _FOLLOW,
        "sort_order": 10,
        "subject": "avant que je retire la démo",
        "body_html": (
            "<p>{salutation},</p>"
            "<p>Dernier mail de ma part. Pour {entreprise}, {prenom_receptionniste} ({assistant_virtuel}, IA) "
            "répond toujours à cette adresse : {lien_assistant}</p>"
            "<p>Pour garder {prenom_receptionniste}, c'est {prix_assistant} par mois, sans engagement, premier mois "
            "satisfait ou remboursé. Sinon, rien à faire.</p>" + _RECEPTIONIST_TIME_TO_THINK_LINE
        ),
    },
    {
        "name": "Réceptionniste IA - le prix, sans détour",
        "category": _FOLLOW,
        "sort_order": 13,
        "subject": "le prix, sans détour",
        "body_html": (
            "<p>{salutation},</p>"
            "<p>Sans détour : {prix_assistant} par mois pour que {prenom_receptionniste}, votre réceptionniste "
            "({assistant_virtuel}, IA), réponde à vos clients à votre place quand vous ne pouvez pas. Sans "
            "engagement, premier mois satisfait ou remboursé.</p>"
            "<p>{prenom_receptionniste} répond déjà à cette adresse : {lien_assistant}</p>"
            "<p>Je retire la démo le {date_expiration}. Un mot me suffit, même un non.</p>"
        ),
    },
]


def _extract_variables(*texts: str) -> list[str]:
    """Extract unique {variable} names from the given texts."""
    pattern = r"\{([a-zA-Z_][a-zA-Z0-9_]*)\}"
    found: set[str] = set()
    for text in texts:
        found.update(re.findall(pattern, text))
    return sorted(found)


def seed_email_templates() -> None:
    """
    Insert the canonical cold-email library for the admin user.

    Each template is matched by (user_id, name); existing rows are left untouched
    so the seeder is safe to re-run (only new templates are added). The rewrite of
    already-seeded rows lives in the ``reseed_frank_email_template_library`` migration.
    """
    from sqlalchemy import select

    from core.config import settings
    from core.database import get_db, init_db
    from models.email_template import EmailTemplate
    from models.user import User

    init_db()
    db = next(get_db())

    try:
        admin: User | None = db.execute(select(User).where(User.email == settings.admin_email)).scalar_one_or_none()

        if admin is None:
            print(f"[SKIP] Admin user {settings.admin_email!r} not found — run user seeder first")
            return

        created = 0
        for tpl in EMAIL_TEMPLATE_LIBRARY:
            name = str(tpl["name"])
            subject = str(tpl["subject"])
            body_html = str(tpl["body_html"])
            exists = db.execute(
                select(EmailTemplate).where(
                    EmailTemplate.user_id == admin.id,
                    EmailTemplate.name == name,
                )
            ).scalar_one_or_none()
            if exists is not None:
                continue

            variables = _extract_variables(subject, body_html)
            db.add(
                EmailTemplate(
                    user_id=admin.id,
                    email_account_id=None,
                    name=name,
                    subject=subject,
                    body_html=body_html,
                    variables=json.dumps(variables),
                    is_active=True,
                    category=str(tpl["category"]),
                    sort_order=int(tpl["sort_order"]),  # type: ignore[arg-type]
                    is_library=True,
                )
            )
            created += 1

        db.commit()
        print(
            f"[OK] Email templates seeded — {created} created, {len(EMAIL_TEMPLATE_LIBRARY) - created} already present"
        )

    except Exception as exc:
        print(f"[ERROR] Email template seeder failed: {exc}")
        db.rollback()
    finally:
        db.close()


if __name__ == "__main__":
    seed_email_templates()
