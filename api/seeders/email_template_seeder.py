"""
Email template seeder — pre-populate cold-email templates for the admin user.

Templates follow the /cold-email skill rules:
  - Subjects: 2-4 words, lowercase, no salesy punctuation
  - Bodies: ruthlessly short, "you" before "I", one link, one low-friction CTA
  - Price only appears in follow-ups, never in J1
  - Unsubscribe footer is added automatically at send time (not in the body)

Variables available: {salutation}, {prenom}, {nom}, {entreprise}, {ville}, {metier}, {lien_demo},
{lien_video} (player page of the prospection video), {vignette_video} (clickable
personalised thumbnail block — the recommended way to put the video in a J1).
({salutation} always renders a safe greeting — « Bonjour » / « Bonjour Léo » /
« Bonjour M. Guillaume » — from the resolved decision-maker; {prenom}/{nom}
are EMPTY when unknown, never a company word.)

Ordering: ``sort_order`` (higher = pinned higher) drives the app's template list
order. The "★ Recommandé" entries are the two best first-email angles and the two
best follow-ups to A/B test first — they stay pinned at the top.

Safe to re-run: templates are matched by (user_id, name) and skipped if present,
so this only APPENDS new templates (never overwrites manual edits). The one-time
fix of an already-seeded body (variant B's English CTA) lives in the
``add_email_template_sort_order`` migration.
"""
from __future__ import annotations

import json
import re


# ---------------------------------------------------------------------------
# Template definitions.
#   sort_order: higher = pinned higher in the app list (0 = normal).
#   ★ Recommandé = the picks to A/B test first (2 first-emails, 2 follow-ups).
# ---------------------------------------------------------------------------

_TEMPLATES: list[dict[str, object]] = [
    # ── ★ Recommandés — Premier email (les 2 meilleurs angles à tester en A/B) ──
    {
        "name": "★ Recommandé 1 — Premier email (fiche Google)",
        "sort_order": 100,
        # Jamais « Google » dans l'objet : Apple rejette le message au niveau SMTP
        # (hard bounce, pas une mise en indésirables) — « votre fiche Google » est
        # la signature d'une arnaque massive au faux démarchage Google My Business
        # en France. Dans le CORPS, la marque ne pose aucun problème (testé).
        "subject": "votre fiche",
        "body_html": (
            "<p>{salutation},</p>"
            "<p>Quand quelqu'un cherche un {metier} à {ville}, Google met en avant les fiches "
            "reliées à un site — les autres passent derrière.</p>"
            "<p>J'ai monté un site pour {entreprise} qui renforce votre fiche Google : {lien_demo}</p>"
            "<p>Ça vous parle ?</p>"
            "<p>Léo</p>"
        ),
    },
    {
        "name": "★ Recommandé 2 — Premier email (crédibilité)",
        "sort_order": 95,
        "subject": "avant d'appeler",
        "body_html": (
            "<p>{salutation},</p>"
            "<p>Aujourd'hui, avant d'appeler un {metier}, on vérifie en ligne. Pas de site = un "
            "doute, même quand le travail est excellent.</p>"
            "<p>J'ai créé un site pour {entreprise} qui lève ce doute en quelques secondes : {lien_demo}</p>"
            "<p>Je vous montre ?</p>"
            "<p>Léo</p>"
        ),
    },
    # ── ★ Vidéo — Premier email avec la vidéo de prospection (A/B prêts) ──
    # Nécessite une vidéo générée pour chaque prospect ({vignette_video}) :
    # la file ignore automatiquement les prospects sans vidéo prête.
    {
        "name": "★ Vidéo 1 — Premier email (je vous montre)",
        "sort_order": 98,
        "subject": "votre site en vidéo",
        "body_html": (
            "<p>{salutation},</p>"
            "<p>J'ai créé un site pour {entreprise}. Plutôt que de l'expliquer, "
            "je vous le montre en 30 secondes :</p>"
            "{vignette_video}"
            "<p>Ça vous parle ?</p>"
            "<p>Léo</p>"
        ),
    },
    {
        "name": "★ Vidéo 2 — Premier email (pas un robot)",
        "sort_order": 97,
        "subject": "30 secondes pour vous",
        "body_html": (
            "<p>{salutation},</p>"
            "<p>Pas de démarchage anonyme : je me présente en 30 secondes, avec le site "
            "que j'ai créé pour {entreprise} à l'écran.</p>"
            "{vignette_video}"
            "<p>Je vous montre la suite ?</p>"
            "<p>Léo</p>"
        ),
    },
    # ── ★ Recommandés — Relance (les 2 meilleures relances à tester en A/B) ──
    {
        "name": "★ Recommandé 1 — Relance (question)",
        "sort_order": 90,
        "subject": "site ou timing",
        "body_html": (
            "<p>{salutation},</p>"
            "<p>Une question rapide : c'est le site qui ne vous convient pas, ou juste une "
            "histoire de timing ?</p>"
            "<p>Un mot et je m'adapte — il est toujours en ligne : {lien_demo}</p>"
            "<p>Léo</p>"
        ),
    },
    {
        "name": "★ Recommandé 2 — Relance (offre à vie)",
        "sort_order": 85,
        "subject": "à vous à vie",
        "body_html": (
            "<p>{salutation},</p>"
            "<p>Le site de {entreprise} est prêt : {lien_demo}</p>"
            "<p>500€ une fois, et il est à vous — pas d'abonnement, vous ne me repayez jamais. "
            "Je m'occupe de la mise en ligne.</p>"
            "<p>Ça vous intéresse ?</p>"
            "<p>Léo</p>"
        ),
    },
    # ── Premier email — autres angles (prospect SANS site) ──
    {
        "name": "J1 — Variante A (visibilité Google)",
        "sort_order": 0,
        "subject": "votre site demo",
        "body_html": (
            "<p>{salutation},</p>"
            "<p>J'ai créé un site vitrine pour {entreprise} — vous pouvez le voir ici : {lien_demo}</p>"
            "<p>Quand quelqu'un cherche un {metier} à {ville} sur Google, il tombe surtout sur ceux "
            "qui ont un site. Sans ça, vous passez sous le radar même quand votre travail est meilleur.</p>"
            "<p>Ça vous parle ?</p>"
            "<p>Léo</p>"
        ),
    },
    {
        "name": "J1 — Variante B (bouche-à-oreille)",
        "sort_order": 0,
        "subject": "{ville} - {metier}",
        "body_html": (
            "<p>{salutation},</p>"
            "<p>La plupart de vos clients arrivent par bouche-à-oreille. Le souci : pour vous "
            "recommander, il faut votre numéro sous la main au bon moment.</p>"
            "<p>J'ai monté un site pour {entreprise} qui règle ça — vos clients partagent un lien, "
            "et c'est réglé : {lien_demo}</p>"
            "<p>Ça vaut le coup d'œil ?</p>"
            "<p>Léo</p>"
        ),
    },
    {
        "name": "J1 — Variante E (on vous retrouve)",
        "sort_order": 0,
        "subject": "quand on vous recommande",
        "body_html": (
            "<p>{salutation},</p>"
            "<p>On vous recommande souvent, mais encore faut-il vous retrouver au bon moment — "
            "sinon la personne appelle le premier venu.</p>"
            "<p>Avec un site, on vous retrouve en 2 secondes. J'en ai fait un pour {entreprise} : {lien_demo}</p>"
            "<p>Ça vous parle ?</p>"
            "<p>Léo</p>"
        ),
    },
    {
        "name": "J1 — Variante F (autonomie)",
        "sort_order": 0,
        "subject": "vous gérez tout",
        "body_html": (
            "<p>{salutation},</p>"
            "<p>J'ai créé un site pour {entreprise} que vous modifiez vous-même, sans développeur "
            "et sans rien y connaître : {lien_demo}</p>"
            "<p>Vos horaires, vos photos, vos tarifs — vous changez ça en 2 clics.</p>"
            "<p>Je vous montre ?</p>"
            "<p>Léo</p>"
        ),
    },
    # ── Relances — autres options ──
    {
        "name": "Relance J+3 — rappel court",
        "sort_order": 0,
        "subject": "petit rappel",
        "body_html": (
            "<p>{salutation},</p>"
            "<p>Vous avez pu jeter un œil au site de {entreprise} ? {lien_demo}</p>"
            "<p>Un mot me suffit, même un non.</p>"
            "<p>Léo</p>"
        ),
    },
    {
        "name": "Relance 1 (J+5) — avec prix",
        "sort_order": 0,
        "subject": "vous avez pu jeter un oeil ?",
        "body_html": (
            "<p>{salutation},</p>"
            "<p>Je reviens vite — le site pour {entreprise} est toujours là : {lien_demo}</p>"
            "<p>500€ une fois, sans abonnement. Je m'occupe de la mise en ligne sur votre nom de domaine.</p>"
            "<p>Ça vous intéresse ?</p>"
            "<p>Léo</p>"
        ),
    },
    {
        "name": "Relance 2 (J+10) — clôture",
        "sort_order": 0,
        "subject": "je ferme le dossier",
        "body_html": (
            "<p>{salutation},</p>"
            "<p>Sans retour de votre part, je vais libérer le site de {entreprise} cette semaine.</p>"
            "<p>Si c'est juste une question de timing, dites-le moi et je le garde de côté : {lien_demo}</p>"
            "<p>Léo</p>"
        ),
    },
    # ── Refonte : prospects qui ONT déjà un site, jugé faible par l'audit
    #    Lighthouse (filtre « Améliorable » dans Mes prospects). Le pitch ne
    #    vend pas une création mais une V2 comparable côte à côte.
    {
        "name": "Refonte — J1 (site existant dépassé)",
        "sort_order": 0,
        "subject": "une v2 de votre site",
        "body_html": (
            "<p>{salutation},</p>"
            "<p>Je suis tombé sur le site de {entreprise}. Il fait le job, mais il vous dessert : "
            "lent sur mobile, et Google fait passer devant des {metier} de {ville} moins bons que vous.</p>"
            "<p>Plutôt que d'en parler, j'en ai monté une version moderne — comparez vous-même : {lien_demo}</p>"
            "<p>Vous en pensez quoi ?</p>"
            "<p>Léo</p>"
        ),
    },
    {
        "name": "Refonte — Relance (J+5, avec prix)",
        "sort_order": 0,
        "subject": "l'ancien ou le nouveau ?",
        "body_html": (
            "<p>{salutation},</p>"
            "<p>La comparaison avec votre site actuel est toujours en ligne : {lien_demo}</p>"
            "<p>500€ une fois, sans abonnement : je bascule votre nom de domaine dessus et vous "
            "gardez la main sur tout le contenu.</p>"
            "<p>On en discute ?</p>"
            "<p>Léo</p>"
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
    Insert the cold-email starter templates for the admin user.

    Each template is matched by (user_id, name); existing rows are left
    untouched so the seeder is safe to re-run (only new templates are added).
    """
    from sqlalchemy import select
    from core.config import settings
    from core.database import get_db, init_db
    from models.email_template import EmailTemplate
    from models.user import User

    init_db()
    db = next(get_db())

    try:
        admin: User | None = db.execute(
            select(User).where(User.email == settings.admin_email)
        ).scalar_one_or_none()

        if admin is None:
            print(f"[SKIP] Admin user {settings.admin_email!r} not found — run user seeder first")
            return

        created = 0
        for tpl in _TEMPLATES:
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
            db.add(EmailTemplate(
                user_id=admin.id,
                email_account_id=None,
                name=name,
                subject=subject,
                body_html=body_html,
                variables=json.dumps(variables),
                is_active=True,
                sort_order=int(tpl["sort_order"]),
            ))
            created += 1

        db.commit()
        print(f"[OK] Email templates seeded — {created} created, {len(_TEMPLATES) - created} already present")

    except Exception as exc:  # noqa: BLE001
        print(f"[ERROR] Email template seeder failed: {exc}")
        db.rollback()
    finally:
        db.close()


if __name__ == "__main__":
    seed_email_templates()
