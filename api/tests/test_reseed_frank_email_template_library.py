"""The frank library cut-over: renames in place, rewrites the kept angles, deactivates only the unused leftovers.

Runs against the in-memory SQLite of ``conftest`` holding every table, so the campaign references
the migration reads (J1, A/B, follow-ups, queue) are real foreign keys.
"""

from __future__ import annotations

from typing import NamedTuple

import pytest
from sqlalchemy import select
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session

from core.config import settings
from enums.email_template_category import EmailTemplateCategory
from enums.email_template_layout import EmailTemplateLayout
from migrations.reseed_frank_email_template_library import FrankEmailTemplateLibraryReseed
from models.campaign import Campaign, CampaignStatus
from models.campaign_follow_up import CampaignFollowUp
from models.email_signature import EmailSignature
from models.email_template import EmailTemplate
from models.user import User
from seeders.email_template_seeder import EMAIL_TEMPLATE_LIBRARY

_LIBRARY_BY_NAME: dict[str, dict[str, object]] = {
    str(template["name"]): template for template in EMAIL_TEMPLATE_LIBRARY
}
_PERSONAL_FRANK_BODY = "<p>{salutation},</p><p>J'ai construit le site de {entreprise}. C'est {prix} une seule fois.</p>"


class TemplateRow(NamedTuple):
    """The columns of an email template the migration may change, read back after a run."""

    name: str
    subject: str
    body_html: str
    is_active: bool
    is_library: bool
    sort_order: int


def _template(user_id: int, name: str, *, is_library: bool = True, is_active: bool = True) -> EmailTemplate:
    return EmailTemplate(
        user_id=user_id,
        name=name,
        subject=f"ancien objet de {name}",
        body_html=f"<p>ancien corps de {name}</p>",
        variables="[]",
        is_active=is_active,
        category=EmailTemplateCategory.FIRST_EMAIL.value,
        sort_order=0,
        is_library=is_library,
    )


@pytest.fixture
def seeded_admin(db: Session) -> dict[str, int]:
    """The admin with the previous library (used and unused angles), his own frank model and one campaign."""
    admin = User(name="Marc Dupont", email=settings.admin_email, hashed_password="x")
    db.add(admin)
    db.flush()
    rows = {
        "used_angle": _template(admin.id, "Visibilité - on vous cherche"),
        "used_follow_up": _template(admin.id, "Rappel court"),
        "unused_angle": _template(admin.id, "Bouche-à-oreille - on vous retrouve"),
        "unused_follow_up": _template(admin.id, "Urgence douce"),
        "dropped_but_used": _template(admin.id, "Autonomie - vous gardez la main"),
        "old_receptionist": _template(admin.id, "Assistant IA - réponses 24/7"),
        "already_archived": _template(admin.id, "J1 - Variante A (visibilité Google)", is_active=False),
        "personal_frank": _template(admin.id, "Franc - prix et date (France/Belgique)", is_library=False),
    }
    rows["personal_frank"].body_html = _PERSONAL_FRANK_BODY
    db.add_all(rows.values())
    db.flush()
    campaign = Campaign(
        user_id=admin.id,
        name="Vague 1",
        status=CampaignStatus.COMPLETED,
        template_id=rows["used_angle"].id,
        ab_template_id_b=rows["old_receptionist"].id,
    )
    db.add(campaign)
    db.flush()
    db.add(CampaignFollowUp(campaign_id=campaign.id, template_id=rows["used_follow_up"].id, delay_days=5, position=1))
    db.add(
        CampaignFollowUp(campaign_id=campaign.id, template_id=rows["dropped_but_used"].id, delay_days=10, position=2)
    )
    db.commit()
    return {key: row.id for key, row in rows.items()} | {"admin": admin.id}


def _run_twice(engine: Engine) -> None:
    for _ in range(2):
        with engine.connect() as connection:
            FrankEmailTemplateLibraryReseed(connection).run()
            connection.commit()


def _rows_by_id(db: Session) -> dict[int, TemplateRow]:
    db.expire_all()
    templates = db.execute(select(EmailTemplate).order_by(EmailTemplate.id)).scalars().all()
    return {
        template.id: TemplateRow(
            template.name,
            template.subject,
            template.body_html,
            template.is_active,
            template.is_library,
            template.sort_order,
        )
        for template in templates
    }


def test_the_kept_angles_are_rewritten_in_place_and_the_frank_templates_are_added(
    engine: Engine, db: Session, seeded_admin: dict[str, int]
) -> None:
    _run_twice(engine)

    rows = _rows_by_id(db)
    used_angle = rows[seeded_admin["used_angle"]]
    assert used_angle.name == "Visibilité - on vous cherche"
    assert used_angle.body_html == _LIBRARY_BY_NAME["Visibilité - on vous cherche"]["body_html"]
    assert used_angle.is_active is True

    first_contact = next(row for row in rows.values() if row.name == "Franc - premier contact")
    assert first_contact.is_library is True and first_contact.sort_order == 100

    active_library_names = {row.name for row in rows.values() if row.is_library and row.is_active}
    assert active_library_names >= set(_LIBRARY_BY_NAME)


def test_the_receptionist_templates_are_renamed_on_their_own_row(
    engine: Engine, db: Session, seeded_admin: dict[str, int]
) -> None:
    _run_twice(engine)

    rows = _rows_by_id(db)
    renamed = rows[seeded_admin["old_receptionist"]]
    assert renamed.name == "Réceptionniste IA - le soir, personne ne répond"
    assert renamed.body_html == _LIBRARY_BY_NAME[renamed.name]["body_html"]
    assert renamed.is_active is True
    assert db.execute(select(Campaign.ab_template_id_b)).scalar_one() == seeded_admin["old_receptionist"]
    assert not any(row.name.startswith("Assistant IA") for row in rows.values())


def test_only_the_never_used_leftovers_are_deactivated(
    engine: Engine, db: Session, seeded_admin: dict[str, int]
) -> None:
    _run_twice(engine)

    rows = _rows_by_id(db)
    assert rows[seeded_admin["unused_angle"]].is_active is False
    assert rows[seeded_admin["unused_follow_up"]].is_active is False
    assert rows[seeded_admin["already_archived"]].is_active is False
    assert rows[seeded_admin["dropped_but_used"]].is_active is True
    assert rows[seeded_admin["used_follow_up"]].is_active is True


def test_the_admin_own_models_are_never_touched(engine: Engine, db: Session, seeded_admin: dict[str, int]) -> None:
    _run_twice(engine)

    assert _rows_by_id(db)[seeded_admin["personal_frank"]] == TemplateRow(
        name="Franc - prix et date (France/Belgique)",
        subject="ancien objet de Franc - prix et date (France/Belgique)",
        body_html=_PERSONAL_FRANK_BODY,
        is_active=True,
        is_library=False,
        sort_order=0,
    )


def test_library_rows_leave_signed_and_new_ones_dressed(
    engine: Engine, db: Session, seeded_admin: dict[str, int]
) -> None:
    signature = EmailSignature(
        user_id=seeded_admin["admin"], name="Signature Dibodev", content_html="<p>Léo</p>", is_default=True
    )
    db.add(signature)
    used_angle = db.get(EmailTemplate, seeded_admin["used_angle"])
    used_angle.layout = EmailTemplateLayout.PLAIN.value
    db.commit()

    _run_twice(engine)

    db.expire_all()
    inserted = db.execute(select(EmailTemplate).where(EmailTemplate.name == "Franc - premier contact")).scalar_one()
    assert (inserted.signature_id, inserted.layout) == (signature.id, EmailTemplateLayout.CARD_TABLE.value)
    rewritten = db.get(EmailTemplate, seeded_admin["used_angle"])
    assert (rewritten.signature_id, rewritten.layout) == (signature.id, EmailTemplateLayout.PLAIN.value)
    assert db.get(EmailTemplate, seeded_admin["personal_frank"]).signature_id is None


def test_a_rerun_changes_nothing(engine: Engine, db: Session, seeded_admin: dict[str, int]) -> None:
    with engine.connect() as connection:
        FrankEmailTemplateLibraryReseed(connection).run()
        connection.commit()
    after_first_run = _rows_by_id(db)

    _run_twice(engine)

    assert _rows_by_id(db) == after_first_run


def test_without_an_admin_the_migration_is_a_no_op(engine: Engine, db: Session) -> None:
    db.add(User(name="Quelqu'un", email="autre@example.com", hashed_password="x"))
    db.commit()

    _run_twice(engine)

    assert _rows_by_id(db) == {}
