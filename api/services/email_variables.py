"""Single source of truth for the personalisation variables of cold emails."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

from sqlalchemy import select
from sqlalchemy.orm import Session

from core.config import settings
from enums.ai_assistant_status import AiAssistantStatus
from models.ai_assistant import AiAssistant
from models.demo_site import DemoSite
from models.prospect_db import ProspectDB
from models.prospect_enrichment import ProspectEnrichment
from services.decision_maker import build_greeting
from services.pricing_service import PricingService
from services.trade_normalizer import TradeNormalizer


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
    ASSISTANT_LINK = "lien_assistant"
    VIDEO_LINK = "lien_video"
    VIDEO_THUMBNAIL = "vignette_video"
    ASSISTANT_VIDEO_LINK = "lien_video_assistant"
    ASSISTANT_VIDEO_THUMBNAIL = "vignette_video_assistant"
    OLD_WEBSITE = "ancien_site"
    PRICE = "prix"
    PRICE_ASSISTANT = "prix_assistant"
    EXPIRY_DATE = "date_expiration"

    _FRENCH_MONTHS: tuple[str, ...] = (
        "janvier",
        "février",
        "mars",
        "avril",
        "mai",
        "juin",
        "juillet",
        "août",
        "septembre",
        "octobre",
        "novembre",
        "décembre",
    )

    @staticmethod
    def build_video_thumbnail_html(video_link: str, thumbnail_url: str) -> str:
        """
        Build the email-safe clickable thumbnail block for `{vignette_video}`.

        Emails cannot embed a playable video, so the proven pattern is a personalised thumbnail
        (his site plus a play button) linking to the player page. Inline styles only, since email
        clients strip stylesheets. A small text link follows the image: clients that block remote
        images (Outlook, some Orange) would otherwise leave a video-only email with no way in.

        Args:
            video_link: Player page URL on the demo host (`/v/{slug}`).
            thumbnail_url: Absolute public URL of the personalised JPEG.

        Returns:
            The HTML block, or an empty string when either URL is missing.
        """
        if not video_link or not thumbnail_url:
            return ""
        label: str = EmailVariables._demo_link_label(video_link)
        return (
            f'<p style="margin:16px 0 6px;"><a href="{video_link}" target="_blank">'
            f'<img src="{thumbnail_url}" alt="Votre site en vidéo" width="480" '
            f'style="display:block;width:100%;max-width:480px;border-radius:12px;border:0;" />'
            f"</a></p>"
            f'<p style="margin:0 0 16px;font-size:13px;color:#555;">La vidéo : '
            f'<a href="{video_link}" target="_blank" rel="noopener noreferrer" '
            f'style="color:#111;text-decoration:underline;">{label}</a></p>'
        )

    @staticmethod
    def build_demo_link_html(demo_link: str, text: str | None = None) -> str:
        """
        Render `{lien_demo}` as a real ``<a>`` anchor so the click is trackable.

        Resend's click tracking only rewrites ``href`` attributes: a bare URL sitting
        as plain text in the body is never wrapped, so every demo-link click went
        untracked (no ``email.clicked`` webhook → no ``clicked_at`` → no PostHog
        ``email_clicked`` → no push). Wrapping the URL in an anchor closes that gap.
        By default the visible text is the demo URL itself, trimmed to ``host/slug``
        (no scheme, no ``?v=`` variant): the prospect recognises their own name in the
        link, which reads far more trustworthy than a worded "voir votre site" CTA.

        Args:
            demo_link: The prospect's demo URL, already carrying the ``?v=A/B`` variant.
            text: Explicit visible label. When ``None`` (the default), the trimmed demo
                  URL is shown instead.

        Returns:
            The inline anchor HTML, or "" when there is no demo link — unchanged from the
            previous empty-string behaviour (the queue guard skips demo-less prospects).
        """
        if not demo_link:
            return ""
        label: str = text if text is not None else EmailVariables._demo_link_label(demo_link)
        return (
            f'<a href="{demo_link}" target="_blank" rel="noopener noreferrer" '
            f'style="color:#111;text-decoration:underline;">{label}</a>'
        )

    @staticmethod
    def _demo_link_label(demo_link: str) -> str:
        """Trim a demo URL to the recognisable ``host/slug`` shown to the prospect.

        Drops the scheme and the ``?v=A/B`` tracking query so the link reads as the
        prospect's own site, while the anchor ``href`` keeps the full URL for A/B tracking.
        """
        cleaned: str = demo_link.strip()
        for scheme in ("https://", "http://"):
            if cleaned.startswith(scheme):
                cleaned = cleaned[len(scheme) :]
                break
        cleaned = cleaned.split("?", 1)[0].split("#", 1)[0]
        return cleaned.rstrip("/")

    @staticmethod
    def format_expiry_date(moment: datetime) -> str:
        """
        Format a datetime as the French day-month date shown to the prospect.

        Args:
            moment: The demo expiry instant.

        Returns:
            The date as "12 octobre" — month names are hardcoded because the
            server locale is not French.
        """
        return f"{moment.day} {EmailVariables._FRENCH_MONTHS[moment.month - 1]}"

    @staticmethod
    def _demo_slug(demo_link: str) -> str:
        """
        Extract the demo site slug (first path segment) from a demo URL.

        Args:
            demo_link: The prospect's demo URL, possibly carrying tracking queries.

        Returns:
            The slug, or "" when the URL has no path.
        """
        label: str = EmailVariables._demo_link_label(demo_link)
        if "/" not in label:
            return ""
        return label.split("/", 1)[1].split("/", 1)[0]

    @classmethod
    def resolve_expiry_date(cls, db: Session, demo_link: str) -> str:
        """
        Resolve `{date_expiration}`: the day the linked demo goes offline.

        The demo is looked up by the slug of the link actually rendered in the email, so the
        announced date always matches the site the prospect will visit.

        Args:
            db: Active database session.
            demo_link: The `{lien_demo}` URL of this send, or "" when the prospect has none.

        Returns:
            The French expiry date ("12 octobre"), or "" without a resolvable demo.
        """
        slug: str = cls._demo_slug(demo_link)
        if not slug:
            return ""
        site: DemoSite | None = db.execute(select(DemoSite).where(DemoSite.slug == slug)).scalar_one_or_none()
        if site is None:
            return ""
        # TTL not started: expires_at still holds the 2099 sentinel — this very send starts the clock.
        if site.demo_link_sent_at is None or site.expires_at is None:
            return cls.format_expiry_date(datetime.now(UTC) + timedelta(days=settings.demo_site_ttl_days))
        return cls.format_expiry_date(site.expires_at)

    @classmethod
    def resolve_assistant_url(cls, db: Session, prospect_id: int) -> str:
        """
        The public URL of the prospect's active AI assistant demo, or "" when he has none.

        Single source of truth shared by `{lien_assistant}` in email (wrapped in a tracked
        anchor) and in SMS (rendered as a bare link): both link to the same assistant.

        Args:
            db: Active database session.
            prospect_id: Prospect the assistant belongs to.

        Returns:
            The full `<demo-host>/a/<slug>` URL, or "" when the prospect has no active assistant.
        """
        assistant: AiAssistant | None = (
            db.execute(
                select(AiAssistant)
                .where(AiAssistant.prospect_id == prospect_id, AiAssistant.status == AiAssistantStatus.ACTIVE.value)
                .order_by(AiAssistant.created_at.desc())
            )
            .scalars()
            .first()
        )
        if assistant is None:
            return ""
        base: str = settings.demo_host_base_url.rstrip("/")
        return f"{base}/ia/{assistant.slug}"

    @classmethod
    def resolve_assistant_link(cls, db: Session, prospect_id: int) -> str:
        """
        Resolve `{lien_assistant}`: a trackable link to the prospect's AI assistant demo.

        Rendered as a real anchor (like `{lien_demo}`) so the click is tracked; empty when the
        prospect has no active assistant, so a template using it simply renders nothing there.

        Args:
            db: Active database session.
            prospect_id: Prospect the assistant belongs to.

        Returns:
            The inline anchor HTML, or "" when the prospect has no active assistant.
        """
        url: str = cls.resolve_assistant_url(db, prospect_id)
        return cls.build_demo_link_html(url) if url else ""

    @classmethod
    def resolve_assistant_video(cls, db: Session, prospect_id: int) -> tuple[str, str]:
        """
        Resolve the prospect's assistant prospection video: (player page URL, thumbnail URL).

        Empty strings when the prospect has no active assistant or its video is not ready — a
        template using ``{lien_video_assistant}`` / ``{vignette_video_assistant}`` then renders
        nothing there and degrades to the live ``{lien_assistant}`` CTA (the assistant video is a
        bonus, never a send blocker — same graceful degradation as ``{lien_assistant}`` in email).

        Args:
            db: Active database session.
            prospect_id: Prospect the assistant belongs to.

        Returns:
            The (video page URL, thumbnail URL) pair, or ("", "").
        """
        from enums.demo_video_status import DemoVideoStatus
        from services.assistant_video_service import public_thumbnail_url, video_page_url

        assistant: AiAssistant | None = (
            db.execute(
                select(AiAssistant)
                .where(AiAssistant.prospect_id == prospect_id, AiAssistant.status == AiAssistantStatus.ACTIVE.value)
                .order_by(AiAssistant.created_at.desc())
            )
            .scalars()
            .first()
        )
        if assistant is None or assistant.video_status != DemoVideoStatus.READY.value:
            return "", ""
        return video_page_url(assistant.slug), public_thumbnail_url(assistant.slug, assistant.video_generated_at)

    @staticmethod
    def display_website(url: str | None) -> str:
        """
        Format a website URL for the body of an email.

        `{ancien_site}` names the prospect's dead website in the "votre site ne
        répond plus" pitch — a bare domain reads better than a full URL there.

        Args:
            url: Stored website URL, or None.

        Returns:
            The URL without scheme or trailing slash, empty when unknown.
        """
        if not url:
            return ""
        cleaned = url.strip()
        for scheme in ("https://", "http://"):
            if cleaned.startswith(scheme):
                cleaned = cleaned[len(scheme) :]
                break
        return cleaned.rstrip("/")

    @staticmethod
    def resolved_contact(db: Session, prospect_id: int) -> tuple[str | None, str | None, str | None]:
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
        enrichment: ProspectEnrichment | None = db.execute(
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
        sale_price_cents: int | None = None,
        assistant_monthly_price_cents: int | None = None,
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
            sale_price_cents: The sender's website sale price, rendered into {prix}; empty when unset.

        Returns:
            The variable name to value map, ready for template substitution.
        """
        first, last, gender = cls.resolved_contact(db, prospect.id)
        assistant_video_link, assistant_video_thumbnail = cls.resolve_assistant_video(db, prospect.id)
        return {
            cls.SALUTATION: build_greeting(first, last, gender),
            cls.FIRST_NAME: first or "",
            cls.LAST_NAME: last or "",
            cls.COMPANY: prospect.name or "",
            cls.CITY: prospect.city or "",
            cls.EMAIL: prospect.email or "",
            cls.PHONE: prospect.phone or "",
            cls.TRADE: TradeNormalizer.normalize(prospect.category),
            cls.DEMO_LINK: cls.build_demo_link_html(demo_link),
            cls.ASSISTANT_LINK: cls.resolve_assistant_link(db, prospect.id),
            cls.VIDEO_LINK: video_link,
            cls.VIDEO_THUMBNAIL: cls.build_video_thumbnail_html(video_link, video_thumbnail_url),
            cls.ASSISTANT_VIDEO_LINK: assistant_video_link,
            cls.ASSISTANT_VIDEO_THUMBNAIL: cls.build_video_thumbnail_html(
                assistant_video_link, assistant_video_thumbnail
            ),
            cls.OLD_WEBSITE: cls.display_website(prospect.website),
            cls.PRICE: PricingService.format_price(sale_price_cents) if sale_price_cents is not None else "",
            cls.PRICE_ASSISTANT: (
                PricingService.format_price(assistant_monthly_price_cents)
                if assistant_monthly_price_cents is not None
                else ""
            ),
            cls.EXPIRY_DATE: cls.resolve_expiry_date(db, demo_link),
        }
