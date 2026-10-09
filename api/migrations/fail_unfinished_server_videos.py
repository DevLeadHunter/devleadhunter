"""Mark failed the videos a server render left pending or generating: the server renders nothing any more.

The owner's PC builds every video now; a demo site or a receptionist still waiting for a server render would never get
it. Its video is marked failed with the reason the dashboard shows, and can be asked from the PC. Re-runnable.
"""

from __future__ import annotations

import sys
from pathlib import Path

from sqlalchemy import inspect, text

_ROOT = Path(__file__).resolve().parent.parent
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

from core.database import engine

_TABLES_WITH_A_VIDEO = ("demo_sites", "ai_assistants")
_SERVER_RENDER_GONE_REASON = "La génération sur le serveur n'existe plus : redemandez la vidéo, votre PC la fera."


def run_migration() -> None:
    """Turn every pending or generating video into a failed one, with its reason."""
    tables = set(inspect(engine).get_table_names())
    with engine.connect() as conn:
        for table in _TABLES_WITH_A_VIDEO:
            if table in tables:
                conn.execute(
                    text(
                        f"UPDATE {table} SET video_status = 'failed', video_error = :reason "
                        "WHERE video_status IN ('pending', 'generating')"
                    ),
                    {"reason": _SERVER_RENDER_GONE_REASON},
                )
        conn.commit()


if __name__ == "__main__":
    run_migration()
