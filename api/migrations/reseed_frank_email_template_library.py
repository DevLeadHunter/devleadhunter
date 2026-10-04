"""Cut the admin's cold-email library over to the frank templates.

The seeder is append-only (it skips a template that already exists by name), so it cannot
rewrite the rows already seeded on prod, rename the receptionist templates, nor retire the
angles dropped from the library. This migration is the prod cut-over, in three steps on the
admin's LIBRARY rows only (``is_library = 1``):

  - rename in place the receptionist templates (« Assistant IA - … » becomes « Réceptionniste
    IA - … »), so the campaigns referencing them keep their row (same id);
  - upsert every template of ``EMAIL_TEMPLATE_LIBRARY``: a kept angle gets the frank subject,
    body, variables, category and sort order, and the admin's preferred signature when it has
    none (its layout stays as chosen); a new frank template is inserted signed and in the card
    with the offer table;
  - deactivate (``is_active = 0``) the library templates dropped from the set that NO campaign
    ever used (as J1, A/B variant, legacy or listed follow-up, or queued email). A dropped
    template still referenced somewhere stays active and is only reported: nothing is deleted,
    the history and the foreign keys stay whole.

The templates the admin created himself (``is_library = 0``, such as his own « Franc - … »
models) are never touched. On a fresh database the admin user does not exist yet (the user
seeder runs after migrations), so this no-ops and the seeder performs the initial seed instead.

Idempotent: a rerun finds the renames done, upserts identical rows and deactivates nothing more.
"""

from __future__ import annotations

import json
import sys
from datetime import UTC, datetime
from pathlib import Path
from typing import ClassVar

from sqlalchemy import bindparam, text
from sqlalchemy.engine import Connection

_ROOT = Path(__file__).resolve().parent.parent
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

from core.config import settings
from core.database import engine
from enums.email_template_layout import EmailTemplateLayout
from seeders.email_template_seeder import EMAIL_TEMPLATE_LIBRARY, _extract_variables


class FrankEmailTemplateLibraryReseed:
    """Rename, rewrite and prune the admin's library rows so they match ``EMAIL_TEMPLATE_LIBRARY``."""

    RENAMED_TEMPLATES: ClassVar[dict[str, str]] = {
        "Assistant IA - réponses 24/7": "Réceptionniste IA - le soir, personne ne répond",
        "Assistant IA - devis par photo": "Réceptionniste IA - devis par photo",
        "Assistant IA - multilingue": "Réceptionniste IA - dans leur langue",
        "Assistant IA - vidéo": "Réceptionniste IA - en vidéo",
        "Assistant IA - relance": "Réceptionniste IA - relance",
        "Assistant IA - le prix cash": "Réceptionniste IA - le prix, sans détour",
    }

    _REFERENCING_COLUMNS: ClassVar[tuple[tuple[str, str], ...]] = (
        ("campaigns", "template_id"),
        ("campaigns", "ab_template_id_b"),
        ("campaigns", "follow_up_template_id"),
        ("campaign_follow_ups", "template_id"),
        ("email_queue", "template_id"),
    )

    def __init__(self, connection: Connection) -> None:
        self._connection = connection

    def run(self) -> None:
        """Apply the cut-over for the admin user; no-op when he does not exist yet."""
        admin_id: int | None = self._connection.execute(
            text("SELECT id FROM users WHERE email = :email"), {"email": settings.admin_email}
        ).scalar()
        if admin_id is None:
            print(f"[SKIP] Admin user {settings.admin_email!r} not found, the seeder will do the initial seed")
            return

        renamed = self._rename_receptionist_templates(admin_id)
        rewritten, inserted = self._upsert_library(admin_id)
        deactivated, kept_in_use = self._deactivate_unused_dropped_templates(admin_id)
        print(
            f"[OK] Frank library for admin {admin_id}: {renamed} renamed, {rewritten} rewritten, "
            f"{inserted} inserted, {deactivated} deactivated."
        )
        for name in kept_in_use:
            print(f"[KEPT] {name!r} is dropped from the library but still used by a campaign: left active")

    def _rename_receptionist_templates(self, admin_id: int) -> int:
        """Rename the old receptionist rows in place; retire the old copy when the new name already exists."""
        renamed = 0
        for old_name, new_name in self.RENAMED_TEMPLATES.items():
            old_id = self._library_template_id(admin_id, old_name)
            if old_id is None:
                continue
            if self._library_template_id(admin_id, new_name) is not None:
                # The seeder got there first: its row carries the new name, the old copy retires.
                self._connection.execute(
                    text("UPDATE email_templates SET is_active = 0 WHERE id = :id"), {"id": old_id}
                )
                continue
            self._connection.execute(
                text("UPDATE email_templates SET name = :new_name WHERE id = :id"),
                {"new_name": new_name, "id": old_id},
            )
            renamed += 1
        return renamed

    def _upsert_library(self, admin_id: int) -> tuple[int, int]:
        """Write every canonical template on the admin account, rewriting the rows that already exist."""
        rewritten = 0
        inserted = 0
        signature_id: int | None = self._preferred_signature_id(admin_id)
        for template in EMAIL_TEMPLATE_LIBRARY:
            subject = str(template["subject"])
            body_html = str(template["body_html"])
            params = {
                "user_id": admin_id,
                "name": str(template["name"]),
                "subject": subject,
                "body_html": body_html,
                "variables": json.dumps(_extract_variables(subject, body_html)),
                "category": str(template["category"]),
                "sort_order": int(template["sort_order"]),  # type: ignore[arg-type]
                "signature_id": signature_id,
            }
            existing_id = self._library_template_id(admin_id, params["name"])
            if existing_id is not None:
                self._connection.execute(
                    text(
                        """
                        UPDATE email_templates
                        SET subject = :subject, body_html = :body_html, variables = :variables,
                            category = :category, sort_order = :sort_order, is_active = 1,
                            signature_id = COALESCE(signature_id, :signature_id)
                        WHERE id = :id
                        """
                    ),
                    {**params, "id": existing_id},
                )
                rewritten += 1
            else:
                self._connection.execute(
                    text(
                        """
                        INSERT INTO email_templates
                            (user_id, name, subject, body_html, variables, is_active, category, sort_order,
                             is_library, signature_id, layout, created_at)
                        VALUES
                            (:user_id, :name, :subject, :body_html, :variables, 1, :category, :sort_order,
                             1, :signature_id, :layout, :created_at)
                        """
                    ),
                    {
                        **params,
                        "layout": EmailTemplateLayout.CARD_TABLE.value,
                        # Naive UTC like the models: the MySQL clock is not UTC in prod.
                        "created_at": datetime.now(UTC).replace(tzinfo=None),
                    },
                )
                inserted += 1
        return rewritten, inserted

    def _preferred_signature_id(self, admin_id: int) -> int | None:
        """The admin's default signature, else his first one, or ``None`` when he has none."""
        return self._connection.execute(
            text("SELECT id FROM email_signatures WHERE user_id = :user_id ORDER BY is_default DESC, id LIMIT 1"),
            {"user_id": admin_id},
        ).scalar()

    def _deactivate_unused_dropped_templates(self, admin_id: int) -> tuple[int, list[str]]:
        """Deactivate the admin's library rows outside the canonical set that no campaign ever used."""
        canonical_names = [str(template["name"]) for template in EMAIL_TEMPLATE_LIBRARY]
        dropped_rows = self._connection.execute(
            text(
                "SELECT id, name, is_active FROM email_templates "
                "WHERE user_id = :user_id AND is_library = 1 AND name NOT IN :names"
            ).bindparams(bindparam("names", expanding=True)),
            {"user_id": admin_id, "names": canonical_names},
        ).all()
        referenced_ids = self._referenced_template_ids()
        deactivated = 0
        kept_in_use: list[str] = []
        for template_id, name, is_active in dropped_rows:
            if template_id in referenced_ids:
                if is_active:
                    kept_in_use.append(str(name))
                continue
            if is_active:
                self._connection.execute(
                    text("UPDATE email_templates SET is_active = 0 WHERE id = :id"), {"id": template_id}
                )
                deactivated += 1
        return deactivated, kept_in_use

    def _referenced_template_ids(self) -> set[int]:
        """Every template id a campaign, a follow-up or a queued email points at: in use, never deactivated."""
        referenced: set[int] = set()
        for table, column in self._REFERENCING_COLUMNS:
            rows = self._connection.execute(
                text(f"SELECT DISTINCT {column} FROM {table} WHERE {column} IS NOT NULL")
            ).all()
            referenced.update(int(row[0]) for row in rows)
        return referenced

    def _library_template_id(self, admin_id: int, name: str) -> int | None:
        """The id of the admin's library row named *name*, or ``None``."""
        return self._connection.execute(
            text("SELECT id FROM email_templates WHERE user_id = :user_id AND is_library = 1 AND name = :name"),
            {"user_id": admin_id, "name": name},
        ).scalar()


def run_migration() -> None:
    """Apply the frank library cut-over on the configured database."""
    with engine.connect() as connection:
        FrankEmailTemplateLibraryReseed(connection).run()
        connection.commit()


if __name__ == "__main__":
    run_migration()
