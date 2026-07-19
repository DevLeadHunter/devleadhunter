"""Retrofit existing email templates: remove big-brand names from the subject.

Apple rejects at SMTP level (hard bounce — the message never reaches the inbox,
not even the junk folder) any message whose SUBJECT names a large brand it has
no reason to see there. « votre fiche Google » is the signature of the massive
fake-Google-My-Business scam in France, and Apple learned it.

Proven by bisection on a real iCloud mailbox (2026-07-19): identical body, only
the subject changed — « votre fiche » delivered, « votre fiche google » bounced,
« votre visibilité sur Google » bounced. The brand in the BODY is harmless.

A hard bounce is worse than spam-foldering: it degrades sender reputation
globally, not only at Apple.

Idempotent: rows are only touched when their subject still names a brand.
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

from core.database import engine  # noqa: E402

_VARIABLE_RE = re.compile(r"\{([a-zA-Z_][a-zA-Z0-9_]*)\}")

# Known subjects → their brand-free replacement. Kept explicit rather than
# regex-stripped: a subject is copy, it deserves a human rewrite, not a
# mechanical amputation that could leave « votre fiche  » or « votre  ».
_REWRITES: dict[str, str] = {
    "votre fiche google": "votre fiche",
}


def run_migration() -> None:
    """Rewrite the subject of every template still naming a brand."""
    with engine.connect() as conn:
        rows = conn.execute(text("SELECT id, subject, body_html FROM email_templates")).all()
        updated = 0
        for row in rows:
            subject = str(row.subject or "")
            replacement = _REWRITES.get(subject.strip().lower())
            if replacement is None:
                continue
            variables = sorted(set(_VARIABLE_RE.findall(replacement + str(row.body_html or ""))))
            conn.execute(
                text(
                    "UPDATE email_templates SET subject = :subject, variables = :variables "
                    "WHERE id = :id"
                ),
                {"subject": replacement, "variables": json.dumps(variables), "id": row.id},
            )
            updated += 1
            print(f"[OK] Template {row.id} : « {subject} » → « {replacement} »")
        conn.commit()
        print(f"[OK] {updated} objet(s) réécrit(s).")


if __name__ == "__main__":
    run_migration()
