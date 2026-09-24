"""Email template seeder — the canonical cold-email library for the admin user.

Twelve templates, six per step, rewritten to sound human (no em dashes, one soft
CTA, ≤ 4 lines). Rules baked in:
  - Subjects: short, capitalised, comprehensible, never naming a big brand
    (Apple hard-bounces "Google" in the subject).
  - Bodies end NUDE — no "Léo" line and no ``{signature}`` token. The optional
    signature block is appended at send time by the "Inclure une signature"
    switch (see ``services/email_signatures.py``), so a hard-coded sign-off would
    double up.
  - Price only appears in follow-ups, through the ``{prix}`` variable (the user's
    configured sale price), never a hard-coded "500 €".
  - The three text angles carry ``{vignette_video}`` too: with a generated video
    it renders the thumbnail (combo), without one it collapses to the demo link
    (the queue guard degrades instead of skipping). The "Vidéo" template has the
    video as its only door and is meant for phase 2.

Variables: {salutation} {prenom} {nom} {entreprise} {ville} {metier} {lien_demo}
{lien_assistant} {lien_video} {vignette_video} {ancien_site} {prix}.

``sort_order`` (higher = pinned) marks the recommended templates at the top of the list.

Safe to re-run: templates are matched by (user_id, name) and skipped if present,
so the seeder only APPENDS. The one-time prod cut-over of the previous 17-template
library (rewrite bodies, archive dropped angles) lives in the
``reseed_email_template_library`` migration, which consumes ``EMAIL_TEMPLATE_LIBRARY``.
"""

from __future__ import annotations

import json
import re

from enums.email_template_category import EmailTemplateCategory

_FIRST = EmailTemplateCategory.FIRST_EMAIL.value
_FOLLOW = EmailTemplateCategory.FOLLOW_UP.value

# The canonical library. ``sort_order`` > 0 = recommended (pinned to the top of the list).
EMAIL_TEMPLATE_LIBRARY: list[dict[str, object]] = [
    # ── Premier email ────────────────────────────────────────────────────────
    {
        "name": "Visibilité - on vous cherche",
        "category": _FIRST,
        "sort_order": 100,
        "subject": "On vous cherche, on trouve les autres",
        "body_html": (
            "<p>{salutation},</p>"
            "<p>Quand quelqu'un cherche un {metier} à {ville}, ce sont les pros qui ont un site qui "
            "ressortent en premier. Les autres restent invisibles, même les meilleurs.</p>"
            "<p>J'ai préparé un site pour {entreprise} qui vous remet en avant. Il est déjà en ligne : {lien_demo}</p>"
            "{vignette_video}"
            "<p>Vous en pensez quoi ?</p>"
        ),
    },
    {
        "name": "Crédibilité - la première impression",
        "category": _FIRST,
        "sort_order": 95,
        "subject": "Votre site est déjà prêt",
        "body_html": (
            "<p>{salutation},</p>"
            "<p>Aujourd'hui, avant d'appeler un {metier}, on vérifie en ligne. Pas de site, et le doute "
            "s'installe, même quand le travail est excellent.</p>"
            "<p>J'ai créé un site pour {entreprise} qui lève ce doute. Il est déjà en ligne : {lien_demo}</p>"
            "{vignette_video}"
            "<p>Envie d'y jeter un œil ?</p>"
        ),
    },
    {
        "name": "Bouche-à-oreille - on vous retrouve",
        "category": _FIRST,
        "sort_order": 90,
        "subject": "Quand on vous recommande à un proche",
        "body_html": (
            "<p>{salutation},</p>"
            "<p>Vos clients parlent de vous, encore faut-il vous retrouver au bon moment. Sinon la "
            "personne appelle le premier venu.</p>"
            "<p>Avec un site, on vous retrouve en deux secondes. J'en ai préparé un pour {entreprise}, "
            "il est déjà en ligne : {lien_demo}</p>"
            "{vignette_video}"
            "<p>Ça vaut le coup d'œil ?</p>"
        ),
    },
    {
        "name": "Vidéo - je vous montre",
        "category": _FIRST,
        "sort_order": 0,
        "subject": "Votre site en vidéo, en 30 secondes",
        "body_html": (
            "<p>{salutation},</p>"
            "<p>J'ai créé un site pour {entreprise}. Plutôt que de vous l'expliquer, je vous le montre "
            "en quelques secondes :</p>"
            "{vignette_video}"
            "<p>Ça vous parle ?</p>"
        ),
    },
    {
        "name": "Site en panne - premier email",
        "category": _FIRST,
        "sort_order": 0,
        "subject": "Votre site ne répond plus",
        "body_html": (
            "<p>{salutation},</p>"
            "<p>En cherchant {entreprise}, je suis tombé sur {ancien_site} : il ne répond plus. Vos "
            "clients qui vous cherchent tombent sur une page d'erreur.</p>"
            "<p>J'en ai préparé un nouveau, prêt à prendre le relais, à votre nom : {lien_demo}</p>"
            "<p>On en parle ?</p>"
        ),
    },
    {
        "name": "Refonte - premier email",
        "category": _FIRST,
        "sort_order": 0,
        "subject": "Votre nouveau site est déjà en ligne",
        "body_html": (
            "<p>{salutation},</p>"
            "<p>Je suis tombé sur le site de {entreprise}. Il fait le travail, mais je pense qu'il peut "
            "vous rapporter plus.</p>"
            "<p>Plutôt que d'en parler, j'en ai monté une version modernisée. Comparez vous-même : {lien_demo}</p>"
            "<p>Vous en pensez quoi ?</p>"
        ),
    },
    # ── Relance ──────────────────────────────────────────────────────────────
    {
        "name": "Rappel court",
        "category": _FOLLOW,
        "sort_order": 90,
        "subject": "Vous avez vu votre site ?",
        "body_html": (
            "<p>{salutation},</p>"
            "<p>Le site de {entreprise} est toujours en ligne : {lien_demo}</p>"
            "<p>Un mot me suffit, même un non.</p>"
        ),
    },
    {
        "name": "Offre à vie",
        "category": _FOLLOW,
        "sort_order": 85,
        "subject": "Un seul paiement, le site est à vous",
        "body_html": (
            "<p>{salutation},</p>"
            "<p>Le site de {entreprise} est prêt : {lien_demo}</p>"
            "<p>{prix} une fois, et il est à vous. Pas d'abonnement, vous ne me repayez jamais, et je "
            "m'occupe de la mise en ligne.</p>"
            "<p>Ça vous intéresse ?</p>"
        ),
    },
    {
        "name": "Autonomie - vous gardez la main",
        "category": _FOLLOW,
        "sort_order": 0,
        "subject": "Vous gérez votre site vous-même",
        "body_html": (
            "<p>{salutation},</p>"
            "<p>J'ai oublié de vous dire le plus pratique : ce site, il est à vous jusque dans le contenu.</p>"
            "<p>Un espace simple vous laisse changer vos horaires, vos photos et vos tarifs, ou ajouter "
            "une page quand vous voulez, sans développeur ni frais en plus : {lien_demo}</p>"
            "<p>Ça vous tente d'essayer ?</p>"
        ),
    },
    {
        "name": "Urgence douce",
        "category": _FOLLOW,
        "sort_order": 0,
        "subject": "Jusqu'à quand je garde votre site ?",
        "body_html": (
            "<p>{salutation},</p>"
            "<p>Petite précision : je ne garde pas les démos en ligne indéfiniment, et celle de "
            "{entreprise} arrive bientôt à échéance.</p>"
            "<p>Si le projet vous tente, un mot suffit pour que je la prolonge : {lien_demo}</p>"
            "<p>Sinon pas de souci, je la retire tranquillement.</p>"
        ),
    },
    {
        "name": "Site en panne - relance",
        "category": _FOLLOW,
        "sort_order": 0,
        "subject": "Votre nouveau site est prêt, lui",
        "body_html": (
            "<p>{salutation},</p>"
            "<p>Votre ancien site ({ancien_site}) est toujours en erreur. Le remplaçant, lui, est déjà "
            "en ligne : {lien_demo}</p>"
            "<p>{prix} une fois, sans abonnement, mise en ligne comprise.</p>"
            "<p>On le met à votre nom ?</p>"
        ),
    },
    {
        "name": "Refonte - relance",
        "category": _FOLLOW,
        "sort_order": 0,
        "subject": "Votre ancien site ou le nouveau ?",
        "body_html": (
            "<p>{salutation},</p>"
            "<p>La comparaison avec votre site actuel est toujours en ligne : {lien_demo}</p>"
            "<p>{prix} une fois, sans abonnement. Je bascule votre nom de domaine dessus et vous gardez "
            "la main sur tout le contenu.</p>"
            "<p>Ça vous intéresse ?</p>"
        ),
    },
    # Assistant IA: the request left unanswered, one link (the demo), the price said plainly.
    {
        "name": "Assistant IA - réponses 24/7",
        "category": _FIRST,
        "sort_order": 10,
        "subject": "Vos clients écrivent le soir, personne ne répond",
        "body_html": (
            "<p>{salutation},</p>"
            "<p>Le soir et le week-end, les clients qui écrivent à {entreprise} attendent le lendemain, "
            "et beaucoup vont voir ailleurs.</p>"
            "<p>J'ai préparé pour vous un assistant qui leur répond tout de suite, 24h/24, et vous transmet "
            "chaque demande : {lien_assistant}</p>"
            "<p>{prix_assistant}/mois, installé sur votre site, sans engagement. On le met en place ?</p>"
        ),
    },
    {
        "name": "Assistant IA - devis par photo",
        "category": _FIRST,
        "sort_order": 11,
        "subject": "Une photo, un devis demandé",
        "body_html": (
            "<p>{salutation},</p>"
            "<p>Un client vous envoie la photo de son problème à 22h : l'assistant que j'ai préparé pour "
            "{entreprise} la regarde, pose les bonnes questions et vous transmet une demande de devis "
            "complète.</p>"
            "<p>Essayez avec n'importe quelle photo : {lien_assistant}</p>"
            "<p>{prix_assistant}/mois, installé sur votre site, sans engagement. Ça vous parle ?</p>"
        ),
    },
    {
        "name": "Assistant IA - multilingue",
        "category": _FIRST,
        "sort_order": 12,
        "subject": "Vos clients, dans leur langue",
        "body_html": (
            "<p>{salutation},</p>"
            "<p>Une partie des clients de {entreprise} n'ose pas écrire en français et repart sans rien "
            "demander.</p>"
            "<p>L'assistant que j'ai préparé leur répond dans leur langue, 24h/24, et vous transmet leur "
            "demande en français : {lien_assistant}</p>"
            "<p>{prix_assistant}/mois, installé sur votre site, sans engagement. On en parle ?</p>"
        ),
    },
    {
        "name": "Assistant IA - relance",
        "category": _FOLLOW,
        "sort_order": 10,
        "subject": "L'assistant de {entreprise} tourne toujours",
        "body_html": (
            "<p>{salutation},</p>"
            "<p>L'assistant de {entreprise} tourne toujours. Chaque soir sans lui, des demandes partent "
            "chez un concurrent.</p>"
            "<p>Posez-lui une question ou envoyez-lui une photo, vous verrez : {lien_assistant}</p>"
            "<p>{prix_assistant}/mois, installation comprise, sans engagement. Je vous l'installe cette "
            "semaine ?</p>"
        ),
    },
    {
        "name": "Assistant IA - le prix cash",
        "category": _FOLLOW,
        "sort_order": 13,
        "subject": "Le prix de l'assistant, sans détour",
        "body_html": (
            "<p>{salutation},</p>"
            "<p>Sans détour : {prix_assistant}/mois pour ne plus laisser une seule demande sans réponse chez "
            "{entreprise}. Installation comprise, sans engagement, premier mois satisfait ou remboursé.</p>"
            "<p>La démo est toujours en ligne : {lien_assistant}</p>"
            "<p>Je vous le mets en place ?</p>"
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
    so the seeder is safe to re-run (only new templates are added). The one-time
    rewrite of already-seeded rows lives in ``reseed_email_template_library``.
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
