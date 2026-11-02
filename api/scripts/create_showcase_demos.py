"""
Create (or refresh) the showroom demos dibodev.fr embeds in its live workshop, one per template.

Replayable: an existing demo is kept (its content too, unless ``--rebuild-content``), a missing one is
created. Run it where the API runs, on its database::

    cd api && python scripts/create_showcase_demos.py [--owner-email contact@dibodev.fr] [--rebuild-content]

In production the manual workflow ``.github/workflows/create-showcase-demos.yml`` runs it on the VPS.
The catalogue (slugs, templates, fictitious businesses) lives in ``services/showcase_demo_service.py``
and is documented in ``docs/SHOWCASE_DEMOS.md``.
"""

from __future__ import annotations

import argparse
import importlib
import pkgutil
import sys
from pathlib import Path

_ROOT = Path(__file__).resolve().parent.parent
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

try:
    from dotenv import load_dotenv

    load_dotenv(_ROOT / ".env")
except ImportError:
    pass

from sqlalchemy.orm import Session, configure_mappers

import models

# Register every mapped class: a partial import leaves SQLAlchemy relationships unresolved.
for _module in pkgutil.iter_modules(models.__path__):
    importlib.import_module(f"models.{_module.name}")
configure_mappers()

from core.config import settings
from core.database import SessionLocal
from models.demo_site import DemoSite
from models.user import User
from services.auth_service import AuthService
from services.showcase_demo_service import SHOWCASE_DEMO_SITES, showcase_demo_service


def _owner(db: Session, email: str) -> User:
    """
    The account the showroom demos belong to.

    Args:
        db: Active database session.
        email: The owner's login email.

    Returns:
        The user.

    Raises:
        SystemExit: When no account has this email.
    """
    owner: User | None = AuthService.get_user_by_email(db, email)
    if owner is None:
        raise SystemExit(f"No account with email {email}: pass --owner-email.")
    return owner


def main() -> int:
    """Command-line entry point: ensure the showroom demos and print where each one is served."""
    parser = argparse.ArgumentParser(description="Create or refresh the showroom demos (one per template).")
    parser.add_argument("--owner-email", default=settings.admin_email, help="Account owning the demos.")
    parser.add_argument(
        "--rebuild-content",
        action="store_true",
        help="Regenerate the content of the demos that already exist (drops dashboard colour edits).",
    )
    arguments = parser.parse_args()

    db: Session = SessionLocal()
    try:
        owner: User = _owner(db, arguments.owner_email)
        results: list[tuple[DemoSite, bool]] = showcase_demo_service.ensure_all(
            db, owner, rebuild_content=arguments.rebuild_content
        )
        created_count: int = sum(1 for _site, created in results if created)
        print(f"{len(SHOWCASE_DEMO_SITES)} showroom demos ensured, {created_count} created, owner {owner.email}.")
        for site, created in results:
            print(f"  {'created ' if created else 'kept    '} {site.template_id:<20} {site.demo_url}")
    finally:
        db.close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
