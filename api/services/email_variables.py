"""Single source of truth for the personalisation variables of cold emails."""
from __future__ import annotations

from typing import Optional

from sqlalchemy import select
from sqlalchemy.orm import Session

from models.prospect_db import ProspectDB
from models.prospect_enrichment import ProspectEnrichment
from services.decision_maker import build_greeting


class EmailVariables:
    """
    Resolves the `{salutation}` / `{prenom}` / `{nom}` / `{entreprise}`… substitution map.

    Used by the campaign queue (dispatch and preview) and by the behaviour follow-up, so every
    send resolves the SAME trusted contact. `{prenom}` and `{nom}` come from the decision-maker
    resolution stored on the enrichment and stay EMPTY when unknown — never a word of the company
    name, which used to produce greetings like "Bonjour Plomberie,".
    """

    SALUTATION = "salutation"
    FIRST_NAME = "prenom"
    LAST_NAME = "nom"
    COMPANY = "entreprise"
    CITY = "ville"
    EMAIL = "email"
    PHONE = "phone"
    TRADE = "metier"
    DEMO_LINK = "lien_demo"
    VIDEO_LINK = "lien_video"
    VIDEO_THUMBNAIL = "vignette_video"

    @staticmethod
    def build_video_thumbnail_html(video_link: str, thumbnail_url: str) -> str:
        """
        Build the email-safe clickable thumbnail block for `{vignette_video}`.

        Emails cannot embed a playable video, so the proven pattern is a personalised thumbnail
        (his site plus a play button) linking to the player page. Inline styles only, since email
        clients strip stylesheets.

        Args:
            video_link: Player page URL on the demo host (`/v/{slug}`).
            thumbnail_url: Absolute public URL of the personalised JPEG.

        Returns:
            The HTML block, or an empty string when either URL is missing.
        """
        if not video_link or not thumbnail_url:
            return ""
        return (
            f'<p style="margin:16px 0;"><a href="{video_link}" target="_blank">'
            f'<img src="{thumbnail_url}" alt="Votre site en vidéo" width="480" '
            f'style="display:block;width:100%;max-width:480px;border-radius:12px;border:0;" />'
            f"</a></p>"
        )

    @staticmethod
    def resolved_contact(
        db: Session, prospect_id: int
    ) -> tuple[Optional[str], Optional[str], Optional[str]]:
        """
        Read the trusted decision-maker identity stored on the enrichment.

        Only names written by the resolver or a manual edit are returned — the confidence
        threshold was already applied at write time.

        Args:
            db: Active database session.
            prospect_id: Prospect the enrichment belongs to.

        Returns:
            The (first name, last name, gender) triple, each None when unknown.
        """
        enrichment: Optional[ProspectEnrichment] = db.execute(
            select(ProspectEnrichment).where(ProspectEnrichment.prospect_id == prospect_id)
        ).scalar_one_or_none()
        if enrichment is None:
            return None, None, None
        return (
            enrichment.contact_first_name,
            enrichment.contact_last_name,
            enrichment.contact_gender,
        )

    @classmethod
    def build_for_prospect(
        cls,
        db: Session,
        prospect: ProspectDB,
        demo_link: str = "",
        video_link: str = "",
        video_thumbnail_url: str = "",
    ) -> dict[str, str]:
        """
        Build the full substitution map for a prospect's emails.

        `{salutation}` is always safe ("Bonjour" / "Bonjour Léo" / "Bonjour M. Guillaume"), while
        `{prenom}` and `{nom}` are empty when unknown. The video variables stay empty when the
        prospect has no generated clip — the queue guards prevent sending a template needing them.

        Args:
            db: Active database session.
            prospect: Prospect being emailed.
            demo_link: URL of his generated demo site.
            video_link: URL of the tracked video player page.
            video_thumbnail_url: Absolute URL of the personalised thumbnail.

        Returns:
            The variable name to value map, ready for template substitution.
        """
        first, last, gender = cls.resolved_contact(db, prospect.id)
        return {
            cls.SALUTATION: build_greeting(first, last, gender),
            cls.FIRST_NAME: first or "",
            cls.LAST_NAME: last or "",
            cls.COMPANY: prospect.name or "",
            cls.CITY: prospect.city or "",
            cls.EMAIL: prospect.email or "",
            cls.PHONE: prospect.phone or "",
            cls.TRADE: prospect.category or "",
            cls.DEMO_LINK: demo_link,
            cls.VIDEO_LINK: video_link,
            cls.VIDEO_THUMBNAIL: cls.build_video_thumbnail_html(video_link, video_thumbnail_url),
        }
