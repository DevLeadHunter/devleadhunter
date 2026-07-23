"""Send a real campaign template to mail-tester.com and print the verdict URL.

Why not reuse ``EmailSendingService.send_email``: it would create an ``EmailLog``
row, fire a PostHog ``email_sent`` event, and — locally — reroute the message to
``DEV_EMAIL_REDIRECT`` instead of mail-tester. This script rebuilds the exact
same *message* (real template, real From, unsubscribe footer, RFC 8058 headers)
without the bookkeeping, so the score reflects production and the stats stay
clean.

A test with placeholder content is worthless: mail-tester penalises thin HTML,
and a missing ``List-Unsubscribe`` costs points Gmail requires anyway.

Usage::

    python scripts/send_mail_tester.py test-abc123@srv1.mail-tester.com
    python scripts/send_mail_tester.py test-abc123@srv1.mail-tester.com --template-id 4
    python scripts/send_mail_tester.py --list          # show available templates
    python scripts/send_mail_tester.py test-abc@srv1.mail-tester.com --base-url https://x.fr
"""
from __future__ import annotations

import argparse
import asyncio
import os
import sys
from typing import Optional

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import importlib  # noqa: E402
import pkgutil  # noqa: E402

import models  # noqa: E402
from core.config import settings  # noqa: E402
from core.database import SessionLocal  # noqa: E402
from models.email_template import EmailTemplate  # noqa: E402
from models.user import User  # noqa: E402
from services.email_sending_service import EmailSendingService  # noqa: E402
from services.resend_service import ResendService  # noqa: E402
from services.sending_identity import SendingIdentity, resolve_sending_identity  # noqa: E402
from services.unsubscribe_service import unsubscribe_service  # noqa: E402

# SQLAlchemy resolves relationships by class name: every model must be imported
# before the first query, or the mappers fail to configure.
for _module in pkgutil.iter_modules(models.__path__):
    importlib.import_module(f"models.{_module.name}")

_PRODUCTION_FRONTEND_URL: str = "https://devleadhunter.dibodev.fr"

# Realistic stand-ins: a template rendered with empty variables would score the
# emptiness, not the copy.
_SAMPLE_VARIABLES: dict[str, str] = {
    "salutation": "Bonjour Geoffrey",
    "prenom": "Geoffrey",
    "nom": "Martin",
    "entreprise": "Martin Plomberie",
    "ville": "Bordeaux",
    "metier": "plombier",
    "email": "contact@martin-plomberie.fr",
    "phone": "05 56 12 34 56",
    "lien_demo": "https://demo.dibodev.fr/martin-plomberie",
    "lien_video": "https://demo.dibodev.fr/v/martin-plomberie",
    "vignette_video": "https://demo.dibodev.fr/v/martin-plomberie/thumbnail.png",
}


def _render(content: str) -> str:
    """Replace every ``{variable}`` by its sample value.

    Args:
        content: Raw template subject or body.

    Returns:
        The rendered content.
    """
    for name, value in _SAMPLE_VARIABLES.items():
        content = content.replace("{" + name + "}", value)
    return content


def _pick_template(db, template_id: Optional[int]) -> EmailTemplate:
    """Return the requested template, or the first active one.

    Args:
        db: Database session.
        template_id: Explicit id, or ``None`` to auto-pick.

    Returns:
        The chosen template.
    @raises SystemExit - When no template matches.
    """
    query = db.query(EmailTemplate).filter(EmailTemplate.is_active.is_(True))
    template = (
        query.filter(EmailTemplate.id == template_id).first()
        if template_id
        else query.order_by(EmailTemplate.sort_order.desc(), EmailTemplate.id).first()
    )
    if template is None:
        raise SystemExit("Aucun modèle actif trouvé — précisez --template-id ou créez un modèle.")
    return template


async def _run(
    recipient: str,
    template_id: Optional[int],
    list_only: bool,
    dry_run: bool,
    base_url_override: Optional[str],
) -> int:
    """Render a real template and send it to *recipient*.

    Args:
        recipient: The mail-tester disposable address.
        template_id: Template to use, or ``None`` for the first active one.
        list_only: Only list the templates, send nothing.
        dry_run: Build the message and stop before sending.
        base_url_override: Base URL of the unsubscribe link (defaults to settings).

    Returns:
        Process exit code.
    """
    db = SessionLocal()
    try:
        user: User | None = db.query(User).order_by(User.id).first()
        if user is None:
            raise SystemExit("Aucun utilisateur en base.")

        if list_only:
            for template in db.query(EmailTemplate).order_by(EmailTemplate.id).all():
                state = "actif " if template.is_active else "inactif"
                print(f"  [{template.id:>3}] {state}  {template.name} — « {template.subject} »")
            return 0

        template = _pick_template(db, template_id)
        identity: SendingIdentity = resolve_sending_identity(db, user.id)
        if identity.provider != "resend":
            raise SystemExit(
                f"Fournisseur actif = {identity.provider}. Ce test cible le chemin Resend."
            )

        subject = _render(template.subject)
        body_html = _render(template.body_html)

        # Same footer + headers as a production send. The local FRONTEND_URL
        # would ship an ``http://localhost:3000`` unsubscribe link: strict
        # filters (iCloud rejects outright) treat that as a malformed message,
        # so the test would measure the test rig instead of the campaign.
        base_url = base_url_override or getattr(settings, "frontend_url", "http://localhost:3000")
        if "localhost" in base_url or "127.0.0.1" in base_url:
            raise SystemExit(
                "FRONTEND_URL est local : le lien de désinscription pointerait sur localhost et "
                f"fausserait le test. Relancez avec --base-url {_PRODUCTION_FRONTEND_URL}"
            )
        unsubscribe_link = unsubscribe_service.generate_unsubscribe_link(recipient, None, base_url)
        body_html = unsubscribe_service.add_unsubscribe_footer(body_html, unsubscribe_link)
        headers = EmailSendingService._unsubscribe_headers(unsubscribe_link)

        print(f"Modèle    : [{template.id}] {template.name}")
        print(f"Objet     : {subject}")
        print(f"Expéditeur: {identity.from_name} <{identity.from_email}>")
        print(f"HTML      : {len(body_html)} octets, headers RFC 8058 posés")
        print(f"Envoi vers: {recipient}\n")

        if dry_run:
            print("--dry-run : message construit, rien n'a été envoyé.")
            return 0

        result = await ResendService().send_email(
            from_email=identity.from_email,
            from_name=identity.from_name,
            to_email=recipient,
            subject=subject,
            html_body=body_html,
            api_key_override=identity.resend_api_key,
            extra_headers=headers,
        )
        print(f"Envoyé (message_id={result.get('message_id')}).")

        if "mail-tester.com" in recipient:
            print(f"Score    : https://www.mail-tester.com/{recipient.split('@')[0]}  (attendre ~30 s)")
        return 0
    finally:
        db.close()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("recipient", nargs="?", help="Adresse jetable fournie par mail-tester.com")
    parser.add_argument("--template-id", type=int, default=None, help="Modèle à envoyer")
    parser.add_argument("--list", action="store_true", help="Lister les modèles et quitter")
    parser.add_argument("--dry-run", action="store_true", help="Construire le message sans l'envoyer")
    parser.add_argument(
        "--base-url", default=None, help="Base URL du lien de désinscription (défaut : FRONTEND_URL)"
    )
    args = parser.parse_args()
    if not args.recipient and not args.list:
        parser.error("Fournissez l'adresse mail-tester, ou --list.")
    raise SystemExit(
        asyncio.run(
            _run(args.recipient or "", args.template_id, args.list, args.dry_run, args.base_url)
        )
    )
