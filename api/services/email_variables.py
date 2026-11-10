"""Single source of truth for the personalisation variables of cold emails."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

from sqlalchemy import select
from sqlalchemy.orm import Session

from core.config import settings
from models.demo_site import DemoSite
from models.prospect_db import ProspectDB
from models.prospect_enrichment import ProspectEnrichment
from services.campaign_offers import CampaignOffers
from services.country_profiles import CountryProfile, CountryProfiles
from services.decision_maker import build_greeting
from services.french_date_formatter import FrenchDateFormatter
from services.regional_lexicon import RegionalLexicon
from services.trade_normalizer import TradeNormalizer


class EmailVariables:
    """
    Resolves the `{salutation}` / `{prenom}` / `{nom}` / `{entreprise}`… substitution map.

    Used by the campaign queue (dispatch and preview) and by the behaviour follow-up, so every
    send resolves the SAME trusted contact. `{prenom}` and `{nom}` come from the decision-maker
    resolution stored on the enrichment and stay EMPTY when unknown — never a word of the company
    name, which used to produce greetings like "Bonjour Plomberie,". The variables of the product
    modules (the receptionist's `{lien_assistant}`, the loyalty card's `{lien_carte}`…) come from their
    offers (:class:`CampaignOffers`).
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
    OLD_WEBSITE = "ancien_site"
    PRICE = "prix"
    EXPIRY_DATE = "date_expiration"

    LINK_STYLE = "color:#111;text-decoration:underline;"
    THUMBNAIL_WIDTH = 480
    THUMBNAIL_PARAGRAPH_STYLE = "margin:16px 0 6px;"
    THUMBNAIL_NOTE_STYLE = "margin:0 0 16px;font-size:13px;color:#555;"
    PREVIEW_THUMBNAIL_PATH = "/images/email-preview-video-thumbnail.jpg"

    @staticmethod
    def build_video_thumbnail_html(video_link: str, thumbnail_url: str, alt_text: str = "Votre site en vidéo") -> str:
        """
        Build the email-safe clickable thumbnail block of a video (`{vignette_video}`, or a module's own).

        Emails cannot embed a playable video, so the proven pattern is a personalised thumbnail
        (his site plus a play button) linking to the player page. Inline styles only, since email
        clients strip stylesheets. A small text link follows the image: clients that block remote
        images (Outlook, some Orange) would otherwise leave a video-only email with no way in.

        Args:
            video_link: Player page URL on the demo host (`/v/{slug}`, `/va/{slug}`).
            thumbnail_url: Absolute public URL of the personalised JPEG.
            alt_text: What the image shows, read when remote images are blocked.

        Returns:
            The HTML block, or an empty string when either URL is missing.
        """
        if not video_link or not thumbnail_url:
            return ""
        label: str = EmailVariables._demo_link_label(video_link)
        width: int = EmailVariables.THUMBNAIL_WIDTH
        return (
            f'<p style="{EmailVariables.THUMBNAIL_PARAGRAPH_STYLE}"><a href="{video_link}" target="_blank">'
            f'<img src="{thumbnail_url}" alt="{alt_text}" width="{width}" '
            f'style="display:block;width:100%;max-width:{width}px;border-radius:12px;border:0;" />'
            f"</a></p>"
            f'<p style="{EmailVariables.THUMBNAIL_NOTE_STYLE}">La vidéo : '
            f'<a href="{video_link}" target="_blank" rel="noopener noreferrer" '
            f'style="{EmailVariables.LINK_STYLE}">{label}</a></p>'
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
            f'style="{EmailVariables.LINK_STYLE}">{label}</a>'
        )

    @classmethod
    def preview_values(cls, sample_values: dict[str, str]) -> dict[str, str]:
        """
        Turn the sample values of a template preview into what a real send carries.

        The app previews a template with one example per variable, written as plain text. A send
        carries anchors for the demo links and a thumbnail block for the videos: the preview gets
        the same, so it shows the email as it leaves, layout included.

        Args:
            sample_values: The example of each variable, as the app sends them.

        Returns:
            The map with the link and thumbnail variables in their sent form.
        """
        values: dict[str, str] = {key: str(value) for key, value in sample_values.items()}
        for key in (cls.DEMO_LINK, *CampaignOffers.preview_link_variables()):
            link: str = values.get(key, "")
            if link and "<" not in link:
                values[key] = cls.build_demo_link_html(link)
        thumbnail_url: str = f"{settings.frontend_url.rstrip('/')}{cls.PREVIEW_THUMBNAIL_PATH}"
        thumbnails: list[tuple[str, str, str]] = [(cls.VIDEO_THUMBNAIL, cls.VIDEO_LINK, "Votre site en vidéo")]
        thumbnails.extend(
            (thumbnail.thumbnail_variable, thumbnail.link_variable, thumbnail.alt_text)
            for thumbnail in CampaignOffers.preview_thumbnails()
        )
        for thumbnail_key, link_key, alt_text in thumbnails:
            if thumbnail_key in values:
                values[thumbnail_key] = cls.build_video_thumbnail_html(
                    values.get(link_key, ""), thumbnail_url, alt_text
                )
        return values

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
            The date as "12 octobre".
        """
        return FrenchDateFormatter.day_month(moment)

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
    def resolve_expiry_date(cls, db: Session, prospect: ProspectDB, demo_link: str, *, user_id: int) -> str:
        """
        Resolve `{date_expiration}`: the day the linked demo — the site, or a module's — goes offline.

        A demo site is looked up by the slug of the link actually rendered in the email, so the
        announced date always matches the site the prospect will visit. Without a demo link, the
        date is the one of the sender's module demo for this prospect (its receptionist…).

        Args:
            db: Active database session.
            prospect: The prospect being emailed.
            demo_link: The `{lien_demo}` URL of this send, or "" when the prospect has none.
            user_id: The sending user.

        Returns:
            The French expiry date ("12 octobre"), or "" without a resolvable demo.
        """
        slug: str = cls._demo_slug(demo_link)
        if slug:
            site: DemoSite | None = db.execute(select(DemoSite).where(DemoSite.slug == slug)).scalar_one_or_none()
            if site is None:
                return ""
            return cls.expiry_label(site.demo_link_sent_at, site.expires_at)
        return CampaignOffers.expiry_date_without_demo_link(db, prospect, user_id=user_id)

    @classmethod
    def expiry_label(cls, demo_link_sent_at: datetime | None, expires_at: datetime | None) -> str:
        """
        The French date a demo goes offline, as an email announces it.

        Args:
            demo_link_sent_at: When the demo's link was first sent, or None.
            expires_at: When the demo expires, or None.

        Returns:
            The date (« 12 octobre »); a demo whose countdown has not started yet is announced
            ``DEMO_SITE_TTL_DAYS`` from now, since this very send starts the clock.
        """
        if demo_link_sent_at is None or expires_at is None:
            return cls.format_expiry_date(datetime.now(UTC) + timedelta(days=settings.demo_site_ttl_days))
        return cls.format_expiry_date(expires_at)

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
        *,
        user_id: int,
        include_video: bool = True,
        variant: str | None = None,
    ) -> dict[str, str]:
        """
        Build the full substitution map for a prospect's emails.

        `{salutation}` is always safe ("Bonjour" / "Bonjour Léo" / "Bonjour M. Guillaume"), while
        `{prenom}` and `{nom}` are empty when unknown. The video variables stay empty when the
        prospect has no generated clip — the queue guards prevent sending a template needing them.
        The price is written as the prospect reads it in his country, without « ≈ » (« 500 € »,
        « 470 CHF », « 800 $ CA »). The product modules add their own variables after the core's.

        Args:
            db: Active database session.
            prospect: Prospect being emailed.
            demo_link: URL of his generated demo site.
            video_link: URL of the tracked video player page.
            video_thumbnail_url: Absolute URL of the personalised thumbnail.
            sale_price_cents: The sender's website sale price in euro cents, rendered into {prix}; empty when unset.
            user_id: The sending user, whose own module demos the module variables resolve to.
            include_video: The campaign's video toggle; off, the modules' videos stay out.
            variant: The send's A/B variant, stamped on the modules' links (the caller stamps the site's).

        Returns:
            The variable name to value map, ready for template substitution.
        """
        first, last, gender = cls.resolved_contact(db, prospect.id)
        country: CountryProfile = CountryProfiles.get(prospect.country)
        values: dict[str, str] = {
            cls.SALUTATION: build_greeting(first, last, gender),
            cls.FIRST_NAME: first or "",
            cls.LAST_NAME: last or "",
            cls.COMPANY: prospect.name or "",
            cls.CITY: prospect.city or "",
            cls.EMAIL: prospect.email or "",
            cls.PHONE: prospect.phone or "",
            cls.TRADE: TradeNormalizer.normalize(prospect.category),
            cls.DEMO_LINK: cls.build_demo_link_html(demo_link),
            cls.VIDEO_LINK: video_link,
            cls.VIDEO_THUMBNAIL: cls.build_video_thumbnail_html(video_link, video_thumbnail_url),
            cls.OLD_WEBSITE: cls.display_website(prospect.website),
            cls.PRICE: country.format_price_without_approximation(sale_price_cents)
            if sale_price_cents is not None
            else "",
        }
        module_values: dict[str, str] = CampaignOffers.email_variables(
            db, prospect, user_id=user_id, include_video=include_video, variant=variant
        )
        for name, value in module_values.items():
            values.setdefault(name, value)
        values[cls.EXPIRY_DATE] = cls.resolve_expiry_date(db, prospect, demo_link, user_id=user_id)
        values[RegionalLexicon.COUNTRY_KEY] = country.code
        return values
