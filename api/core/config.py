"""
Configuration settings for the Prospect Tool API.
"""
from typing import List, Optional
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
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        populate_by_name=True
    )
    
    env: str = "development"
    debug: bool = True
    api_version: str = "v1"
    api_prefix: str = "/api/v1"
    api_base_url: str = Field(
        default="http://localhost:8000",
        alias="API_BASE_URL",
        description="Base URL for the API server"
    )
    
    host: str = "0.0.0.0"
    port: int = 8000
    
    cors_origins_str: Optional[str] = Field(
        default="http://localhost:3000,http://localhost:3001,http://localhost:5173,http://localhost:1420,https://demo.dibodev.fr",
        alias="CORS_ORIGINS",
        description="Comma-separated list of allowed CORS origins"
    )
    
    # Database settings
    database_url: str = Field(
        default="mysql+pymysql://root:root@localhost:3310/devleadhunter",
        alias="DATABASE_URL",
        description="Database connection URL"
    )
    
    # JWT settings
    secret_key: str = Field(
        default="dev-secret-key-change-in-production",
        alias="SECRET_KEY",
        description="Secret key for JWT token signing"
    )
    algorithm: str = Field(
        default="HS256",
        description="Algorithm for JWT token signing"
    )
    access_token_expire_minutes: int = Field(
        default=30,
        alias="ACCESS_TOKEN_EXPIRE_MINUTES",
        description="Access token expiration time in minutes"
    )
    
    # Admin user settings
    admin_email: str = Field(
        default="contact@dibodev.fr",
        alias="ADMIN_EMAIL",
        description="Admin user email address"
    )
    admin_password: str = Field(
        default="admin123",
        alias="ADMIN_PASSWORD",
        description="Admin user password"
    )
    
    # Stripe settings
    stripe_secret_key: str = Field(
        default="",
        alias="STRIPE_SECRET_KEY",
        description="Stripe secret key for API calls"
    )
    stripe_public_key: str = Field(
        default="",
        alias="STRIPE_PUBLIC_KEY",
        description="Stripe public key for frontend"
    )
    stripe_webhook_secret: str = Field(
        default="",
        alias="STRIPE_WEBHOOK_SECRET",
        description="Stripe webhook secret for verifying webhook signatures"
    )
    frontend_url: str = Field(
        default="http://localhost:3000",
        alias="FRONTEND_URL",
        description="Frontend URL for redirects after payment"
    )

    # Demo site builder / Storyblok
    demo_host_base_url: str = Field(
        default="http://localhost:3001",
        alias="DEMO_HOST_BASE_URL",
        description="Public base URL for generated demo websites (localhost:3001 in dev, demo.dibodev.fr in prod)",
    )
    demo_site_ttl_days: int = Field(
        default=14,
        alias="DEMO_SITE_TTL_DAYS",
        description="Number of days before a demo site is auto-deleted",
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
    storyblok_management_token: Optional[str] = Field(
        default=None,
        alias="STORYBLOK_MANAGEMENT_TOKEN",
        description="Storyblok Management API personal access token",
    )
    storyblok_region: str = Field(
        default="eu",
        alias="STORYBLOK_REGION",
        description="Storyblok region (eu, us, ap, ca, cn)",
    )
    storyblok_webhook_secret: Optional[str] = Field(
        default=None,
        alias="STORYBLOK_WEBHOOK_SECRET",
        description="Shared secret used to sign Storyblok publish webhooks (optional)",
    )
    pagespeed_api_key: Optional[str] = Field(
        default=None,
        alias="PAGESPEED_API_KEY",
        description="Google PageSpeed Insights API key (optional — raises the free quota)",
    )
    vercel_token: Optional[str] = Field(
        default=None,
        alias="VERCEL_TOKEN",
        description="Vercel API token used for per-site domain attachment / deploys",
    )
    vercel_team_id: Optional[str] = Field(
        default=None,
        alias="VERCEL_TEAM_ID",
        description="Optional Vercel team id (for team-scoped API calls)",
    )
    vercel_demo_host_project_id: Optional[str] = Field(
        default=None,
        alias="VERCEL_DEMO_HOST_PROJECT_ID",
        description="Vercel project id of the demo-host prod project (domains attach here)",
    )
    vercel_deploy_hook_url: Optional[str] = Field(
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
    posthog_project_id: Optional[str] = Field(
        default=None,
        alias="POSTHOG_PROJECT_ID",
        description="PostHog project id used for the query API",
    )
    posthog_personal_api_key: Optional[str] = Field(
        default=None,
        alias="POSTHOG_PERSONAL_API_KEY",
        description="PostHog personal API key (read events for scoring/timeline)",
    )
    posthog_project_api_key: Optional[str] = Field(
        default=None,
        alias="POSTHOG_PROJECT_API_KEY",
        description="PostHog project API key (phc_) for server-side event capture (email events)",
    )
    posthog_ingestion_host: str = Field(
        default="https://eu.i.posthog.com",
        alias="POSTHOG_INGESTION_HOST",
        description="PostHog ingestion host used for server-side capture (eu/us)",
    )

    # Groq — LLM for behaviour summary and personalised follow-ups
    groq_api_key: Optional[str] = Field(
        default=None,
        alias="GROQ_API_KEY",
        description="Groq API key (OpenAI-compatible) for AI summary / personalised relance",
    )
    groq_model: str = Field(
        default="llama-3.3-70b-versatile",
        alias="GROQ_MODEL",
        description="Groq model id used for completions",
    )

    # Dev / testing — outbound email safety
    dev_email_redirect: Optional[str] = Field(
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
    scraper_chrome_executable: Optional[str] = Field(
        default=None,
        alias="SCRAPER_CHROME_EXECUTABLE",
        description="Optional path to chrome.exe when not on PATH",
    )
    scraper_user_data_dir: Optional[str] = Field(
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

    # Support / ticketing settings
    support_local_upload_dir: str = Field(
        default="uploads/support",
        alias="SUPPORT_LOCAL_UPLOAD_DIR",
        description="Local directory for storing support attachments in non-production environments"
    )
    support_max_attachment_mb: int = Field(
        default=8,
        alias="SUPPORT_MAX_ATTACHMENT_MB",
        description="Maximum support attachment size (in megabytes)"
    )
    support_ftp_host: Optional[str] = Field(
        default=None,
        alias="SUPPORT_FTP_HOST",
        description="FTP host for storing support attachments in production"
    )
    support_ftp_port: int = Field(
        default=21,
        alias="SUPPORT_FTP_PORT",
        description="FTP port for storing support attachments in production"
    )
    support_ftp_user: Optional[str] = Field(
        default=None,
        alias="SUPPORT_FTP_USER",
        description="FTP username for storing support attachments in production"
    )
    support_ftp_password: Optional[str] = Field(
        default=None,
        alias="SUPPORT_FTP_PASSWORD",
        description="FTP password for storing support attachments in production"
    )
    support_ftp_base_dir: str = Field(
        default="/support/uploads",
        alias="SUPPORT_FTP_BASE_DIR",
        description="Base directory on the FTP server for support attachments"
    )
    support_ftp_public_base_url: Optional[str] = Field(
        default=None,
        alias="SUPPORT_FTP_PUBLIC_BASE_URL",
        description="Public base URL where uploaded FTP files are accessible"
    )
    support_ftp_use_tls: bool = Field(
        default=True,
        alias="SUPPORT_FTP_USE_TLS",
        description="Whether to use explicit TLS when connecting to the FTP server"
    )
    support_attachment_allowed_mime: str = Field(
        default="image/jpeg,image/png,image/webp",
        alias="SUPPORT_ATTACHMENT_ALLOWED_MIME",
        description="Comma-separated list of allowed MIME types for support attachments"
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


    # Google OAuth settings (for Gmail)
    google_client_id: str = Field(
        default="",
        alias="GOOGLE_CLIENT_ID",
        description="Google OAuth client ID"
    )
    google_client_secret: str = Field(
        default="",
        alias="GOOGLE_CLIENT_SECRET",
        description="Google OAuth client secret"
    )
    google_redirect_uri: str = Field(
        default="http://localhost:8000/api/v1/email-accounts/gmail/callback",
        alias="GOOGLE_REDIRECT_URI",
        description="Google OAuth redirect URI"
    )
    
    # Encryption settings (for OAuth tokens)
    encryption_key: Optional[str] = Field(
        default=None,
        alias="ENCRYPTION_KEY",
        description="Encryption key for sensitive data (OAuth tokens). Generate with Fernet.generate_key()"
    )
    
    @property
    def cors_origins(self) -> List[str]:
        """
        Get CORS origins as a list from the comma-separated string.
        
        Returns:
            List of allowed CORS origins
        """
        if not self.cors_origins_str:
            return []
        return [origin.strip() for origin in self.cors_origins_str.split(",") if origin.strip()]
    
    @property
    def allowed_cors_origins(self) -> List[str]:
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


# Global settings instance
settings = Settings()

