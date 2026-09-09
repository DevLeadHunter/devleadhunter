"""
Configuration settings for the Prospect Tool API.
"""

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """
    Application settings loaded from environment variables.

    Attributes:
        env: Current environment (development, staging, production)
        debug: Whether debug mode is enabled
        api_version: API version string
        api_prefix: API prefix for routes
        host: Server host address
        port: Server port number
        cors_origins_str: Comma-separated string of allowed CORS origins
    """

    model_config = SettingsConfigDict(
        env_file=".env", env_file_encoding="utf-8", case_sensitive=False, populate_by_name=True
    )

    env: str = "development"
    debug: bool = True
    api_version: str = "v1"
    api_prefix: str = "/api/v1"
    api_base_url: str = Field(
        default="http://localhost:8000", alias="API_BASE_URL", description="Base URL for the API server"
    )

    host: str = "0.0.0.0"
    port: int = 8000

    cors_origins_str: str | None = Field(
        default="http://localhost:3000,http://localhost:3001,http://localhost:5173,http://localhost:1420,https://demo.dibodev.fr",
        alias="CORS_ORIGINS",
        description="Comma-separated list of allowed CORS origins",
    )

    # Database settings
    database_url: str = Field(
        default="mysql+pymysql://root:root@localhost:3310/devleadhunter",
        alias="DATABASE_URL",
        description="Database connection URL",
    )

    # JWT settings
    secret_key: str = Field(
        default="dev-secret-key-change-in-production",
        alias="SECRET_KEY",
        description="Secret key for JWT token signing",
    )
    algorithm: str = Field(default="HS256", description="Algorithm for JWT token signing")
    access_token_expire_minutes: int = Field(
        default=10080,  # 7 days — no refresh token yet, so keep sessions long-lived
        alias="ACCESS_TOKEN_EXPIRE_MINUTES",
        description="Access token expiration time in minutes",
    )

    # Admin user settings
    admin_email: str = Field(default="contact@dibodev.fr", alias="ADMIN_EMAIL", description="Admin user email address")
    admin_password: str = Field(default="admin123", alias="ADMIN_PASSWORD", description="Admin user password")

    # Stripe settings
    stripe_secret_key: str = Field(default="", alias="STRIPE_SECRET_KEY", description="Stripe secret key for API calls")
    stripe_public_key: str = Field(default="", alias="STRIPE_PUBLIC_KEY", description="Stripe public key for frontend")
    stripe_webhook_secret: str = Field(
        default="", alias="STRIPE_WEBHOOK_SECRET", description="Stripe webhook secret for verifying webhook signatures"
    )
    frontend_url: str = Field(
        default="http://localhost:3000", alias="FRONTEND_URL", description="Frontend URL for redirects after payment"
    )

    # Demo site builder / Storyblok
    demo_host_base_url: str = Field(
        default="http://localhost:3001",
        alias="DEMO_HOST_BASE_URL",
        description="Public base URL for generated demo websites (localhost:3001 in dev, demo.dibodev.fr in prod)",
    )
    demo_site_ttl_days: int = Field(
        default=21,
        alias="DEMO_SITE_TTL_DAYS",
        description="Number of days a demo site stays online after its link is first emailed",
    )
    demo_dormant_retention_days: int = Field(
        default=60,
        alias="DEMO_DORMANT_RETENTION_DAYS",
        description="Days an expired demo of an SMS-reachable prospect stays dormant (revivable) before hard-deletion",
    )
    storyblok_trial_days: int = Field(
        default=45,
        alias="STORYBLOK_TRIAL_DAYS",
        description="Storyblok Growth Plus trial length per space (days from space creation)",
    )
    storyblok_preswap_lead_minutes: int = Field(
        default=30,
        alias="STORYBLOK_PRESWAP_LEAD_MINUTES",
        description="Minutes before a scheduled outreach email to pre-swap an expiring Storyblok space",
    )
    demo_site_verify_retries: int = Field(
        default=3,
        alias="DEMO_SITE_VERIFY_RETRIES",
        description="HTTP verification attempts for the public demo URL",
    )
    demo_site_verify_retry_delay_seconds: float = Field(
        default=2.0,
        alias="DEMO_SITE_VERIFY_RETRY_DELAY_SECONDS",
        description="Delay between demo URL verification attempts",
    )

    # Prospection video (webcam générique + capture du site du prospect).
    # Les fichiers vivent sur R2 ; le rendu passe par des dossiers temporaires.
    presenter_video_max_mb: int = Field(
        default=300,
        alias="PRESENTER_VIDEO_MAX_MB",
        description="Maximum upload size for the presenter clip (MB)",
    )

    # Cloudflare R2 (S3-compatible) — backend de stockage UNIQUE (local ET prod).
    # Le bucket et l'URL publique sont résolus selon `env`.
    r2_account_id: str | None = Field(default=None, alias="R2_ACCOUNT_ID")
    r2_access_key_id: str | None = Field(default=None, alias="R2_ACCESS_KEY_ID")
    r2_secret_access_key: str | None = Field(default=None, alias="R2_SECRET_ACCESS_KEY")
    r2_endpoint: str | None = Field(
        default=None,
        alias="R2_ENDPOINT",
        description="S3 API endpoint (write path) — https://<account_id>.r2.cloudflarestorage.com",
    )
    r2_bucket_dev: str | None = Field(default=None, alias="R2_BUCKET_DEV")
    r2_bucket_prod: str | None = Field(default=None, alias="R2_BUCKET_PROD")
    r2_public_base_url_dev: str | None = Field(
        default=None,
        alias="R2_PUBLIC_BASE_URL_DEV",
        description="Public read URL of the dev bucket (r2.dev or custom domain)",
    )
    r2_public_base_url_prod: str | None = Field(
        default=None,
        alias="R2_PUBLIC_BASE_URL_PROD",
        description="Public read URL of the prod bucket (r2.dev or custom domain)",
    )
    ffmpeg_path: str = Field(
        default="ffmpeg",
        alias="FFMPEG_PATH",
        description="ffmpeg executable used to compose prospection videos",
    )
    storyblok_management_token: str | None = Field(
        default=None,
        alias="STORYBLOK_MANAGEMENT_TOKEN",
        description="Storyblok Management API personal access token",
    )
    storyblok_region: str = Field(
        default="eu",
        alias="STORYBLOK_REGION",
        description="Storyblok region (eu, us, ap, ca, cn)",
    )
    storyblok_webhook_secret: str | None = Field(
        default=None,
        alias="STORYBLOK_WEBHOOK_SECRET",
        description="Shared secret used to sign Storyblok publish webhooks (optional)",
    )
    pagespeed_api_key: str | None = Field(
        default=None,
        alias="PAGESPEED_API_KEY",
        description="Google PageSpeed Insights API key (optional — raises the free quota)",
    )
    # Legacy service-account Postmaster vars — ignored since per-user OAuth; kept so existing .env files load.
    google_postmaster_credentials_file: str | None = Field(
        default=None,
        alias="GOOGLE_POSTMASTER_CREDENTIALS_FILE",
        description="Deprecated — unused",
    )
    google_postmaster_credentials_json: str | None = Field(
        default=None,
        alias="GOOGLE_POSTMASTER_CREDENTIALS_JSON",
        description="Deprecated — unused",
    )
    vercel_token: str | None = Field(
        default=None,
        alias="VERCEL_TOKEN",
        description="Vercel API token used for per-site domain attachment / deploys",
    )
    vercel_team_id: str | None = Field(
        default=None,
        alias="VERCEL_TEAM_ID",
        description="Optional Vercel team id (for team-scoped API calls)",
    )
    vercel_demo_host_project_id: str | None = Field(
        default=None,
        alias="VERCEL_DEMO_HOST_PROJECT_ID",
        description="Vercel project id of the demo-host prod project (domains attach here)",
    )
    vercel_deploy_hook_url: str | None = Field(
        default=None,
        alias="VERCEL_DEPLOY_HOOK_URL",
        description="Optional Vercel Deploy Hook URL to trigger a production rebuild",
    )

    # PostHog — behavioural tracking on demo sites (read side for scoring/timeline)
    posthog_api_host: str = Field(
        default="https://eu.posthog.com",
        alias="POSTHOG_API_HOST",
        description="PostHog app/API host used to query events (eu/us cloud or self-hosted)",
    )
    posthog_project_id: str | None = Field(
        default=None,
        alias="POSTHOG_PROJECT_ID",
        description="PostHog project id used for the query API",
    )
    posthog_personal_api_key: str | None = Field(
        default=None,
        alias="POSTHOG_PERSONAL_API_KEY",
        description="PostHog personal API key (read events for scoring/timeline)",
    )
    posthog_project_api_key: str | None = Field(
        default=None,
        alias="POSTHOG_PROJECT_API_KEY",
        description="PostHog project API key (phc_) for server-side event capture (email events)",
    )
    posthog_ingestion_host: str = Field(
        default="https://eu.i.posthog.com",
        alias="POSTHOG_INGESTION_HOST",
        description="PostHog ingestion host used for server-side capture (eu/us)",
    )

    # Pappers — structured company directors (decision-maker name cascade).
    # Optional: the strategy is a clean no-op without a key.
    pappers_api_key: str = Field(
        default="",
        alias="PAPPERS_API_KEY",
        description="Pappers API key (optional) for company directors lookup",
    )

    # Groq — LLM for behaviour summary and personalised follow-ups
    groq_api_key: str | None = Field(
        default=None,
        alias="GROQ_API_KEY",
        description="Groq API key (OpenAI-compatible) for AI summary / personalised relance",
    )
    groq_model: str = Field(
        default="openai/gpt-oss-120b",
        alias="GROQ_MODEL",
        description="Groq model id used for completions (llama-3.3-70b-versatile was decommissioned 2026-06-17)",
    )
    # Vision model (photo labelling). Only a preference: the service checks it against the account's
    # live model list and falls back to the next known vision model, so a decommission never leaves
    # the feature silently dead again.
    groq_vision_model: str = Field(
        default="qwen/qwen3.6-27b",
        alias="GROQ_VISION_MODEL",
        description="Preferred Groq vision model id for photo labelling (verified against the live model list)",
    )

    # Fallback .fr first-year price (HT, EUR) shown before purchase when the live OVH public
    # catalog is unreachable. The catalog (services/domain/ovh_catalog.py) is the source of truth.
    domain_fr_price_eur: float = Field(
        default=4.99,
        alias="DOMAIN_FR_PRICE_EUR",
        description="Fallback .fr first-year price in EUR (HT), used when the OVH catalog is unreachable",
    )
    # OVH subsidiary for the order catalog + domain purchase — drives .fr pricing/eligibility.
    ovh_subsidiary: str = Field(
        default="FR",
        alias="OVH_SUBSIDIARY",
        description="OVH subsidiary code (FR, etc.) for the order catalog and domain orders",
    )
    # OVH API credentials for buying the client's domain + writing its DNS after the sale.
    # All three empty = the registrar is inert (no purchase attempted); the manual domain flow stays.
    ovh_application_key: str | None = Field(default=None, alias="OVH_APPLICATION_KEY", description="OVH API app key")
    ovh_application_secret: str | None = Field(
        default=None, alias="OVH_APPLICATION_SECRET", description="OVH API app secret"
    )
    ovh_consumer_key: str | None = Field(default=None, alias="OVH_CONSUMER_KEY", description="OVH API consumer key")
    ovh_endpoint: str = Field(
        default="https://eu.api.ovh.com/1.0",
        alias="OVH_ENDPOINT",
        description="OVH API base URL (EU by default)",
    )
    # Vercel's apex A-record target — where a client's registered domain points to reach the demo-host.
    vercel_apex_ip: str = Field(
        default="76.76.21.21",
        alias="VERCEL_APEX_IP",
        description="Vercel apex A-record IP the client domain (apex + www) points to",
    )

    # Dev / testing — outbound email safety
    dev_email_redirect: str | None = Field(
        default=None,
        alias="DEV_EMAIL_REDIRECT",
        description=(
            "When set, ALL outbound prospect emails are rerouted to this address "
            "(dev safety — nothing reaches real clients). Leave empty in production."
        ),
    )

    # Nodriver / Chrome scraping (see scrappers.nodriver_browser)
    scraper_browser_headless: bool = Field(
        default=False,
        alias="SCRAPER_BROWSER_HEADLESS",
        description="When False, Chrome opens visibly for scraping (GoupixDex-style)",
    )
    scraper_browser_keep_open: bool = Field(
        default=False,
        alias="SCRAPER_BROWSER_KEEP_OPEN",
        description="When True, do not close Chrome after a scrape job (debug)",
    )
    scraper_browser_close_delay_sec: float = Field(
        default=2.5,
        alias="SCRAPER_BROWSER_CLOSE_DELAY_SEC",
        description="Seconds to wait before closing visible Chrome after a job",
    )
    scraper_chrome_executable: str | None = Field(
        default=None,
        alias="SCRAPER_CHROME_EXECUTABLE",
        description="Optional path to chrome.exe when not on PATH",
    )
    scraper_user_data_dir: str | None = Field(
        default=None,
        alias="SCRAPER_USER_DATA_DIR",
        description="Persistent Chrome profile directory for scraping sessions",
    )
    scraper_warmup_maps: bool = Field(
        default=False,
        alias="SCRAPER_WARMUP_MAPS",
        description="Pre-open Chrome for Google Maps autocomplete on API startup",
    )

    # BrightData HTTP API
    brightdata_api_token: str = Field(
        default="",
        alias="BRIGHTDATA_API_TOKEN",
        description="BrightData API bearer token for Web Unlocker and SERP requests",
    )
    brightdata_zone: str = Field(
        default="mcp_unlocker",
        alias="BRIGHTDATA_ZONE",
        description="BrightData zone name used for Web Unlocker requests",
    )

    # SMS (smsmode) — single platform account; the sender is per-user, injected
    # per message. Empty key = SMS channel disabled (no send).
    smsmode_api_key: str = Field(
        default="",
        alias="SMSMODE_API_KEY",
        description="smsmode REST API key (X-Api-Key header)",
    )
    smsmode_base_url: str = Field(
        default="https://rest.smsmode.com/sms/v1/messages",
        alias="SMSMODE_BASE_URL",
        description="smsmode REST v1 messages endpoint",
    )
    smsmode_credit_url: str = Field(
        default="https://api.smsmode.com/http/1.6/credit.do",
        alias="SMSMODE_CREDIT_URL",
        description="smsmode HTTP API endpoint returning the account's remaining credit balance",
    )
    smsmode_price_per_segment_eur: float = Field(
        default=0.061,
        alias="SMSMODE_PRICE_PER_SEGMENT_EUR",
        description="smsmode price per SMS segment (euros), used when the send response carries no price (real FR rate)",
    )
    sms_auto_daily_cap: int = Field(
        default=20,
        alias="SMS_AUTO_DAILY_CAP",
        description="Max automated SMS (relance + cold) sent per user per day (warm-up throttle)",
    )
    sms_auto_per_run: int = Field(
        default=3,
        alias="SMS_AUTO_PER_RUN",
        description="Max automated SMS sent per user on each background pass (spreads the daily cap)",
    )

    # Support / ticketing settings — les pièces jointes vivent sur R2 (voir
    # `support_storage_service`), identique en local et en production.
    support_max_attachment_mb: int = Field(
        default=8, alias="SUPPORT_MAX_ATTACHMENT_MB", description="Maximum support attachment size (in megabytes)"
    )
    support_attachment_allowed_mime: str = Field(
        default="image/jpeg,image/png,image/webp",
        alias="SUPPORT_ATTACHMENT_ALLOWED_MIME",
        description="Comma-separated list of allowed MIME types for support attachments",
    )

    # Resend settings (primary cold-email provider)
    resend_api_key: str = Field(
        default="",
        alias="RESEND_API_KEY",
        description="Resend API key — create at https://resend.com/api-keys",
    )
    resend_webhook_secret: str = Field(
        default="",
        alias="RESEND_WEBHOOK_SECRET",
        description="Resend webhook signing secret for verifying event payloads",
    )
    reply_capture_domain: str = Field(
        default="",
        alias="REPLY_CAPTURE_DOMAIN",
        description=(
            "Receiving-enabled Resend domain used as Reply-To on outreach "
            "(e.g. reply.dibodev.fr). Empty disables reply capture."
        ),
    )
    reply_inbox_forward_to: str = Field(
        default="",
        alias="REPLY_INBOX_FORWARD_TO",
        description=(
            "Optional override for the inbox that receives forwarded prospect replies "
            "and BCC copies of conversation answers. Empty = each user's sending "
            "identity ``from_email``."
        ),
    )

    # Web Push (VAPID) — mobile PWA notifications for the dashboard user
    vapid_public_key: str | None = Field(
        default=None,
        alias="VAPID_PUBLIC_KEY",
        description="VAPID public key (base64url) exposed to the browser to subscribe to Web Push",
    )
    vapid_private_key_b64: str | None = Field(
        default=None,
        alias="VAPID_PRIVATE_KEY_B64",
        description="VAPID private key as base64 of its PKCS8 PEM (secret — signs push messages)",
    )
    vapid_subject: str = Field(
        default="mailto:contact@dibodev.fr",
        alias="VAPID_SUBJECT",
        description="VAPID 'sub' claim — a mailto: or https: contact for the push service",
    )
    daily_recap_hour_utc: int = Field(
        default=19,
        alias="DAILY_RECAP_HOUR_UTC",
        description="UTC hour (0-23) for the daily recap push — 19 ≈ 21h Paris in summer",
    )

    # Google OAuth settings (for Gmail)
    google_client_id: str = Field(default="", alias="GOOGLE_CLIENT_ID", description="Google OAuth client ID")
    google_client_secret: str = Field(
        default="", alias="GOOGLE_CLIENT_SECRET", description="Google OAuth client secret"
    )
    google_redirect_uri: str = Field(
        default="http://localhost:8000/api/v1/email-accounts/gmail/callback",
        alias="GOOGLE_REDIRECT_URI",
        description="Google OAuth redirect URI",
    )
    google_postmaster_redirect_uri: str = Field(
        default="http://localhost:8000/api/v1/email-health/postmaster/callback",
        alias="GOOGLE_POSTMASTER_REDIRECT_URI",
        description="Google OAuth redirect URI for Postmaster Tools (Santé email)",
    )

    # Encryption settings (for OAuth tokens)
    encryption_key: str | None = Field(
        default=None,
        alias="ENCRYPTION_KEY",
        description="Encryption key for sensitive data (OAuth tokens). Generate with Fernet.generate_key()",
    )

    # Qonto payment provider (OAuth — sales invoicing for the admin's own account)
    qonto_client_id: str = Field(default="", alias="QONTO_CLIENT_ID", description="Qonto OAuth client ID")
    qonto_client_secret: str = Field(default="", alias="QONTO_CLIENT_SECRET", description="Qonto OAuth client secret")
    qonto_redirect_uri: str = Field(
        default="http://localhost:8000/api/v1/payment-accounts/qonto/callback",
        alias="QONTO_REDIRECT_URI",
        description="Qonto OAuth redirect URI (must match the Developer Portal registration)",
    )
    qonto_staging_token: str = Field(
        default="",
        alias="QONTO_STAGING_TOKEN",
        description="Sandbox-only X-Qonto-Staging-Token header, appended to every sandbox API call",
    )
    qonto_environment: str = Field(
        default="sandbox",
        alias="QONTO_ENVIRONMENT",
        description="Qonto environment ('sandbox' | 'production'). Never inferred — declared, so a "
        "missing staging token in sandbox fails loudly instead of hitting the real organization.",
    )

    @property
    def qonto_is_sandbox(self) -> bool:
        """Whether Qonto runs against its sandbox environment."""
        return self.qonto_environment == "sandbox"

    @property
    def qonto_api_base_url(self) -> str:
        """Qonto Business API host, derived from the environment (sandbox has its own host)."""
        return (
            "https://thirdparty-sandbox.staging.qonto.co" if self.qonto_is_sandbox else "https://thirdparty.qonto.com"
        )

    @property
    def qonto_oauth_base_url(self) -> str:
        """Qonto OAuth host, derived from the environment (sandbox has its own host)."""
        return "https://oauth-sandbox.staging.qonto.co" if self.qonto_is_sandbox else "https://oauth.qonto.com"

    @property
    def cors_origins(self) -> list[str]:
        """
        Get CORS origins as a list from the comma-separated string.

        Returns:
            List of allowed CORS origins
        """
        if not self.cors_origins_str:
            return []
        return [origin.strip() for origin in self.cors_origins_str.split(",") if origin.strip()]

    @property
    def allowed_cors_origins(self) -> list[str]:
        """
        Get allowed CORS origins based on environment.

        Returns:
            List of allowed origins for CORS
        """
        origins = self.cors_origins.copy()

        # Tauri desktop app origins (constant across API environments). On Windows/WebView2
        # the packaged app is served from http://tauri.localhost; macOS/Linux use tauri://localhost.
        # Without these, the desktop login preflight is blocked by CORS.
        desktop_origins = [
            "http://tauri.localhost",
            "https://tauri.localhost",
            "tauri://localhost",
        ]
        for origin in desktop_origins:
            if origin not in origins:
                origins.append(origin)

        if self.env.lower() != "production":
            development_origins = [
                "http://localhost:3000",
                "http://localhost:3001",
                "http://127.0.0.1:3001",
                "http://localhost:5173",
                "http://localhost:1420",
                "http://127.0.0.1:1420",
                "https://demo.dibodev.fr",
            ]
            for origin in development_origins:
                if origin not in origins:
                    origins.append(origin)

        # Add production frontend origins if in production
        if self.env.lower() == "production":
            production_origins = [
                "https://devleadhunter.fr",
                "https://www.devleadhunter.fr",
                "https://devleadhunter.dibodev.fr",
                "https://www.devleadhunter.dibodev.fr",
                "https://demo.dibodev.fr",
            ]
            # Only add if not already present
            for origin in production_origins:
                if origin not in origins:
                    origins.append(origin)

        return origins

    @property
    def is_production(self) -> bool:
        """
        Determine if the application is running in production.

        Returns:
            True if production environment
        """
        return self.env.lower() == "production"

    @property
    def r2_bucket(self) -> str | None:
        """
        Bucket used by this environment (dev bucket locally, prod bucket in production).

        Returns:
            Bucket name, or None when not configured.
        """
        return self.r2_bucket_prod if self.is_production else self.r2_bucket_dev

    @property
    def r2_public_base_url(self) -> str | None:
        """
        Public read base URL matching :attr:`r2_bucket` (no trailing slash).

        Returns:
            Base URL, or None when not configured.
        """
        raw = self.r2_public_base_url_prod if self.is_production else self.r2_public_base_url_dev
        return raw.rstrip("/") if raw else None


# Global settings instance
settings = Settings()
