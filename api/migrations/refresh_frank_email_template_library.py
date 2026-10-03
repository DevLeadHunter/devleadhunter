"""Rewrite the admin's frank email library after its first review.

``reseed_frank_email_template_library`` ran once on prod. The library was then reviewed: the
follow-ups no longer promise to be the last message nor ask for « un non merci », the reminder
before withdrawal drops « Je range mes démos », the receptionist templates agree with the gender of
the first name (``{receptionniste}``, ``{assistant_virtuel}``) and no longer say « pas une
personne », and three templates join the library (« Rappel court - vidéo », « Réceptionniste IA -
franc », « Réceptionniste IA - en bref »).

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
    """Upsert the reviewed frank library on the configured database."""
    with engine.connect() as connection:
        FrankEmailTemplateLibraryReseed(connection).run()
        connection.commit()


if __name__ == "__main__":
    run_migration()
