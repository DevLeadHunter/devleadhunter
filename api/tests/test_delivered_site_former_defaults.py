"""
A template update never changes a site a client bought: wherever its own content stays empty, a delivered site keeps
the texts its template wrote by default when it was sold (the landscaper's « À propos » ticks, its contact title and
the sentence under its steps), while a demo still on offer shows the template's current wording.
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from typing import Any

from sqlalchemy.orm import Session

from enums.demo_site_status import DemoSiteStatus
from models.demo_site import DemoSite
from services.demo_site_service import demo_site_service
from services.templates.landscaper_verdure import DELIVERED_SITE_FORMER_DEFAULTS
from services.templates.site_content import keep_former_defaults

_FORMER_TICKS: list[str] = [
    "Devis gratuit et sans engagement",
    "Entreprise assurée, travail garanti",
    "Pratiques durables et éco-responsables",
]


def _landscaper_site(db: Session, status: DemoSiteStatus, content: dict[str, Any]) -> DemoSite:
    site = DemoSite(
        user_id=1,
        slug=f"mayer-paysagiste-{status.value}",
        business_name="Mayer Paysagiste",
        template_id="landscaper-verdure",
        city="Angers",
        status=status.value,
        content_json={"businessName": "Mayer Paysagiste", **content},
        expires_at=datetime.now(UTC) + timedelta(days=10),
    )
    db.add(site)
    db.commit()
    return site


def test_a_delivered_site_keeps_the_texts_its_template_wrote_when_it_was_sold(db: Session) -> None:
    site = _landscaper_site(db, DemoSiteStatus.DELIVERED, {"strengths": [], "contactHeading": ""})

    content = demo_site_service.content_json_for_public(db, site)

    assert [tick["title"] for tick in content["strengths"]] == _FORMER_TICKS
    assert content["contactHeading"] == "Demandez votre devis gratuit"
    assert content["stepsLead"].startswith("Un déroulé simple et sans stress")


def test_the_texts_written_for_a_delivered_site_win_over_the_former_defaults(db: Session) -> None:
    site = _landscaper_site(
        db,
        DemoSiteStatus.DELIVERED,
        {"contactHeading": "Parlons de vos arbres", "strengths": [{"title": "Élagage en sécurité", "description": ""}]},
    )

    content = demo_site_service.content_json_for_public(db, site)

    assert content["contactHeading"] == "Parlons de vos arbres"
    assert [tick["title"] for tick in content["strengths"]] == ["Élagage en sécurité"]


def test_a_demo_still_on_offer_shows_the_current_wording_of_its_template(db: Session) -> None:
    site = _landscaper_site(db, DemoSiteStatus.ACTIVE, {})

    content = demo_site_service.content_json_for_public(db, site)

    assert not content.get("strengths")
    assert "contactHeading" not in content
    assert "stepsLead" not in content


def test_the_former_defaults_take_the_regional_words_of_the_business() -> None:
    content = keep_former_defaults({}, DELIVERED_SITE_FORMER_DEFAULTS, "CA")

    assert content["strengths"][0]["title"] == "Soumission gratuite et sans engagement"
    assert content["contactHeading"] == "Demandez votre soumission gratuite"
    assert DELIVERED_SITE_FORMER_DEFAULTS["contactHeading"] == "Demandez votre devis gratuit"
