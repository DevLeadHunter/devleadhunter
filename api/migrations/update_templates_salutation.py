"""Retrofit existing email templates: « Bonjour {prenom}, » → « {salutation}, ».

{prenom} used to be the first word of the COMPANY name (« Bonjour Plomberie, »).
It now resolves to the decision-maker's real first name and is EMPTY when
unknown — so already-seeded templates must switch their greeting line to the
new {salutation} variable (which always renders a clean « Bonjour… »).
Idempotent: the string replacement is a no-op once applied.
"""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path

from sqlalchemy import text

_ROOT = Path(__file__).resolve().parent.parent
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

from core.database import engine

_VARIABLE_RE = re.compile(r"\{([a-zA-Z_][a-zA-Z0-9_]*)\}")


def run_migration() -> None:
    with engine.connect() as conn:
        rows = conn.execute(
            text("SELECT id, subject, body_html FROM email_templates WHERE body_html LIKE :needle"),
            {"needle": "%Bonjour {prenom},%"},
        ).all()
        for row in rows:
            body = str(row.body_html).replace("Bonjour {prenom},", "{salutation},")
            variables = sorted(set(_VARIABLE_RE.findall(str(row.subject) + body)))
            conn.execute(
                text("UPDATE email_templates SET body_html = :body, variables = :variables WHERE id = :id"),
                {"body": body, "variables": json.dumps(variables), "id": row.id},
            )
        conn.commit()


if __name__ == "__main__":
    run_migration()
