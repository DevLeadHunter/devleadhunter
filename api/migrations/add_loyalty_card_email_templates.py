"""Add the loyalty-card templates to the admin's frank email library.

``refresh_frank_email_template_library`` ran once on prod. Five templates then joined
``EMAIL_TEMPLATE_LIBRARY``: the cold emails of the loyalty-card module (« Carte fidélité - … »),
three first emails and two follow-ups linking ``{lien_carte}`` and priced with ``{prix_carte}``.

Same cut-over, reused as is on the admin's library rows (``is_library = 1``): every canonical
template is upserted, the templates the admin wrote himself are never touched, and a rerun is
harmless.
"""

from __future__ import annotations

import sys
from pathlib import Path

_ROOT = Path(__file__).resolve().parent.parent
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

from core.database import engine
from migrations.reseed_frank_email_template_library import FrankEmailTemplateLibraryReseed


def run_migration() -> None:
    """Upsert the frank library, loyalty-card templates included, on the configured database."""
    with engine.connect() as connection:
        FrankEmailTemplateLibraryReseed(connection).run()
        connection.commit()


if __name__ == "__main__":
    run_migration()
