"""
Email template seeder — pre-populate cold-email templates for the admin user.

Templates follow the /cold-email skill rules:
  - Subjects: 2-4 words, lowercase, no salesy punctuation
  - Bodies: ruthlessly short, "you" before "I", one link, one low-friction CTA
  - Price only appears in follow-ups, never in J1
  - Unsubscribe footer is added automatically at send time (not in the body)

Variables available: {prenom}, {entreprise}, {ville}, {metier}, {lien_demo}

Safe to re-run: templates are matched by (user_id, name) and skipped if present.
"""
from __future__ import annotations

import json
import re


# ---------------------------------------------------------------------------
# Template definitions — order matters only for display.
# ---------------------------------------------------------------------------

_TEMPLATES: list[dict[str, str]] = [
    {
        "name": "J1 — Variante A (visibilité Google)",
        "subject": "votre site demo",
        "body_html": (
            "<p>Bonjour {prenom},</p>"
            "<p>J'ai créé un site vitrine pour {entreprise} — vous pouvez le voir ici : {lien_demo}</p>"
            "<p>Quand quelqu'un cherche un {metier} à {ville} sur Google, il tombe surtout sur ceux "
            "qui ont un site. Sans ça, vous passez sous le radar même quand votre travail est meilleur.</p>"
            "<p>Ça vous parle ?</p>"
            "<p>Léo</p>"
        ),
    },
    {
        "name": "J1 — Variante B (bouche-à-oreille)",
        "subject": "{ville} - {metier}",
        "body_html": (
            "<p>Bonjour {prenom},</p>"
            "<p>La plupart de vos clients arrivent par bouche-à-oreille. Le souci : pour vous "
            "recommander, il faut votre numéro sous la main au bon moment.</p>"
            "<p>J'ai monté un site pour {entreprise} qui règle ça — vos clients partagent un lien, "
            "et c'est réglé : {lien_demo}</p>"
            "<p>Ça vaut le coup d'œil ?</p>"
            "<p>Léo</p>"
        ),
    },
    {
        "name": "J1 — Variante C (fiche Google/Maps)",
        "subject": "votre fiche google",
        "body_html": (
            "<p>Bonjour {prenom},</p>"
            "<p>Quand quelqu'un cherche un {metier} à {ville}, Google met en avant les fiches "
            "reliées à un site — les autres passent derrière.</p>"
            "<p>J'ai monté un site pour {entreprise} qui renforce votre fiche Google : {lien_demo}</p>"
            "<p>Ça vous parle ?</p>"
            "<p>Léo</p>"
        ),
    },
    {
        "name": "J1 — Variante D (crédibilité)",
        "subject": "avant d'appeler",
        "body_html": (
            "<p>Bonjour {prenom},</p>"
            "<p>Aujourd'hui, avant d'appeler un {metier}, on vérifie en ligne. Pas de site = un "
            "doute, même quand le travail est excellent.</p>"
            "<p>J'ai créé un site pour {entreprise} qui lève ce doute en quelques secondes : {lien_demo}</p>"
            "<p>Je vous montre ?</p>"
            "<p>Léo</p>"
        ),
    },
    {
        "name": "J1 — Variante E (on vous retrouve)",
        "subject": "quand on vous recommande",
        "body_html": (
            "<p>Bonjour {prenom},</p>"
            "<p>On vous recommande souvent, mais encore faut-il vous retrouver au bon moment — "
            "sinon la personne appelle le premier venu.</p>"
            "<p>Avec un site, on vous retrouve en 2 secondes. J'en ai fait un pour {entreprise} : {lien_demo}</p>"
            "<p>Ça vous parle ?</p>"
            "<p>Léo</p>"
        ),
    },
    {
        "name": "J1 — Variante F (autonomie)",
        "subject": "vous gérez tout",
        "body_html": (
            "<p>Bonjour {prenom},</p>"
            "<p>J'ai créé un site pour {entreprise} que vous modifiez vous-même, sans développeur "
            "et sans rien y connaître : {lien_demo}</p>"
            "<p>Vos horaires, vos photos, vos tarifs — vous changez ça en 2 clics.</p>"
            "<p>Je vous montre ?</p>"
            "<p>Léo</p>"
        ),
    },
    {
        "name": "Relance 1 (J+5) — avec prix",
        "subject": "vous avez pu jeter un oeil ?",
        "body_html": (
            "<p>Bonjour {prenom},</p>"
            "<p>Je reviens vite — le site pour {entreprise} est toujours là : {lien_demo}</p>"
            "<p>500€ une fois, sans abonnement. Je m'occupe de la mise en ligne sur votre nom de domaine.</p>"
            "<p>Ça vous intéresse ?</p>"
            "<p>Léo</p>"
        ),
    },
    {
        "name": "Relance 2 (J+10) — clôture",
        "subject": "je ferme le dossier",
        "body_html": (
            "<p>Bonjour {prenom},</p>"
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
        "subject": "une v2 de votre site",
        "body_html": (
            "<p>Bonjour {prenom},</p>"
            "<p>Je suis tombé sur le site de {entreprise}. Il fait le job, mais il vous dessert : "
            "lent sur mobile, et Google fait passer devant des {metier} de {ville} moins bons que vous.</p>"
            "<p>Plutôt que d'en parler, j'en ai monté une version moderne — comparez vous-même : {lien_demo}</p>"
            "<p>Vous en pensez quoi ?</p>"
            "<p>Léo</p>"
        ),
    },
    {
        "name": "Refonte — Relance (J+5, avec prix)",
        "subject": "l'ancien ou le nouveau ?",
        "body_html": (
            "<p>Bonjour {prenom},</p>"
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
    untouched so the seeder is safe to re-run.
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
            exists = db.execute(
                select(EmailTemplate).where(
                    EmailTemplate.user_id == admin.id,
                    EmailTemplate.name == tpl["name"],
                )
            ).scalar_one_or_none()
            if exists is not None:
                continue

            variables = _extract_variables(tpl["subject"], tpl["body_html"])
            db.add(EmailTemplate(
                user_id=admin.id,
                email_account_id=None,
                name=tpl["name"],
                subject=tpl["subject"],
                body_html=tpl["body_html"],
                variables=json.dumps(variables),
                is_active=True,
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
