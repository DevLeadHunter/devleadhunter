"""Pydantic schemas for demo site generation."""

from datetime import datetime

from pydantic import BaseModel, ConfigDict, EmailStr, Field


class DemoSiteTheme(BaseModel):
    """Customizable color palette for a demo site template."""

    primary: str = Field(default="#0284c7", pattern=r"^#[0-9A-Fa-f]{6}$")
    secondary: str = Field(default="#0f172a", pattern=r"^#[0-9A-Fa-f]{6}$")
    accent: str = Field(default="#f59e0b", pattern=r"^#[0-9A-Fa-f]{6}$")


class DemoSiteCreateRequest(BaseModel):
    """Payload to create a demo site from the stepper tunnel."""

    business_name: str = Field(..., min_length=2, max_length=255)
    template_id: str = Field(default="plumber-signature", max_length=64)
    phone: str | None = Field(default=None, max_length=64)
    email: EmailStr
    invite_client_to_cms: bool = Field(
        default=False,
        description="When true, Storyblok sends a CMS invitation email to the client immediately.",
    )
    city: str | None = Field(default=None, max_length=128)
    description: str | None = Field(default=None, max_length=2000)
    theme: DemoSiteTheme | None = None
    prospect_id: int | None = Field(
        default=None,
        description="Optional saved prospect used to pre-fill business fields on the client.",
    )


class DemoSitePreviewRequest(BaseModel):
    """Payload to render a demo site preview without provisioning."""

    business_name: str = Field(..., min_length=2, max_length=255)
    template_id: str = Field(default="plumber-signature", max_length=64)
    phone: str | None = Field(default=None, max_length=64)
    email: EmailStr | None = None
    city: str | None = Field(default=None, max_length=128)
    description: str | None = Field(default=None, max_length=2000)
    theme: DemoSiteTheme | None = None


class DemoSitePreviewResponse(BaseModel):
    """Client-side preview payload before publish."""

    template_id: str
    content_json: dict


class DemoSiteUpdateRequest(BaseModel):
    """Partial update payload for an existing demo site."""

    business_name: str | None = Field(default=None, min_length=2, max_length=255)
    template_id: str | None = Field(default=None, max_length=64)
    phone: str | None = Field(default=None, max_length=64)
    email: EmailStr | None = None
    city: str | None = Field(default=None, max_length=128)
    description: str | None = Field(default=None, max_length=2000)
    theme: DemoSiteTheme | None = None


class DemoSiteTemplateTheme(BaseModel):
    """Default theme colors for a template."""

    primary: str
    secondary: str
    accent: str


class DemoSiteTemplateResponse(BaseModel):
    """Available site template metadata."""

    id: str
    name: str
    description: str
    preview_image_url: str | None = None
    default_theme: DemoSiteTemplateTheme
    category: str = "artisan"


class DemoSiteResponse(BaseModel):
    """Demo site returned to authenticated users."""

    id: int
    slug: str
    template_id: str
    business_name: str
    phone: str | None = None
    email: str | None = None
    city: str | None = None
    description: str | None = None
    status: str
    demo_url: str | None = None
    demo_url_live: bool = False
    local_demo_url: str | None = None
    verification_message: str | None = None
    storyblok_editor_url: str | None = None
    storyblok_login_email: str | None = None
    storyblok_login_password: str | None = None
    storyblok_invite_sent: bool = False
    expires_at: datetime
    created_at: datetime
    error_message: str | None = None
    theme: DemoSiteTheme | None = None
    # Prospection video (webcam + capture du site du prospect).
    video_status: str | None = None
    video_error: str | None = None
    video_generated_at: datetime | None = None
    # Injected by the route when the video is ready (not model columns).
    video_page_url: str | None = None
    video_thumbnail_url: str | None = None

    model_config = ConfigDict(from_attributes=True)


class DemoSitePublicResponse(BaseModel):
    """Public payload consumed by demo.dibodev.fr/{slug}."""

    slug: str
    business_name: str
    template_id: str
    storyblok_space_id: int | None = None
    storyblok_public_token: str | None = None
    storyblok_preview_token: str | None = None
    storyblok_region: str | None = None
    content_json: dict | None = None
    status: str
    expires_at: datetime
    # True when a prospection video is generated for this demo (player at /v/{slug}).
    video_available: bool = False
    # Public R2 URLs consumed by the player page (empty when no video).
    video_url: str | None = None
    video_thumbnail_url: str | None = None

    model_config = ConfigDict(from_attributes=True)


class DemoSiteListResponse(BaseModel):
    """Paginated list of demo sites for the current user."""

    items: list[DemoSiteResponse]
    total: int
