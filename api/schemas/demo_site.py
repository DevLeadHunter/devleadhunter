"""Pydantic schemas for demo site generation."""

from datetime import datetime
from typing import Literal

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


class DemoSiteServiceCard(BaseModel):
    """One card of the editable section (a dish of the food menu): title, blurb, photo of the pool."""

    title: str = Field(..., min_length=1, max_length=80)
    description: str = Field(default="", max_length=240)
    # A photo URL of the site's pool, or "" (the site then falls back to a real gallery photo).
    image: str = Field(default="", max_length=2000)


class DemoSiteUpdateRequest(BaseModel):
    """Partial update payload for an existing demo site."""

    business_name: str | None = Field(default=None, min_length=2, max_length=255)
    template_id: str | None = Field(default=None, max_length=64)
    phone: str | None = Field(default=None, max_length=64)
    email: EmailStr | None = None
    city: str | None = Field(default=None, max_length=128)
    description: str | None = Field(default=None, max_length=2000)
    theme: DemoSiteTheme | None = None
    # Logo ⟷ Template choice for the action colour (applied on regeneration).
    use_brand_color: bool | None = None
    # Curated photo placement ([0]→hero, [1]→about, [2:]→gallery), saved with the other
    # pending edits so one PATCH regenerates the site once.
    image_order: list[str] | None = None
    # Curated section cards (food « Nos spécialités »): replaces the generated cards and survives
    # regenerations. ``[]`` clears the curation (back to the generated cards); omitted = untouched.
    services: list[DemoSiteServiceCard] | None = Field(default=None, max_length=12)
    # Where the saved cards come from (display only): manual edits, or an AI suggestion kept as-is.
    services_source: Literal["manual", "ai"] | None = None


class DemoSiteServiceCardsConfig(BaseModel):
    """Section constraints declared by the template (``TEMPLATE_META['service_cards']``)."""

    enabled: bool = False
    heading: str = "Prestations"
    subject: str = "prestations"
    min_cards: int = 4
    max_cards: int = 6
    with_images: bool = True


class DemoSitePhotoLabel(BaseModel):
    """A pool photo with what the vision pass saw on it (``kind`` is ``unknown`` until analysed)."""

    url: str
    kind: str = "unknown"
    description: str = ""
    dishes: list[str] = Field(default_factory=list)
    appeal: int = 0
    # Whether the photo may illustrate a card (a dish or a drink).
    card_worthy: bool = False


class DemoSiteServiceCardsResponse(BaseModel):
    """The section's current cards, the curation state, the photo pool and the AI availability."""

    cards: list[DemoSiteServiceCard]
    # True when the published cards come from a saved curation (survives regenerations).
    override_active: bool = False
    # manual / ai / ai_auto when a curation is active.
    override_source: str | None = None
    pool: list[DemoSitePhotoLabel]
    ai_available: bool = False
    # Pool photos not analysed yet (labelled on the next suggestion).
    labels_pending: int = 0
    config: DemoSiteServiceCardsConfig


class DemoSiteServiceCardSuggestion(DemoSiteServiceCard):
    """A suggested card, with the AI's justification and the 1-based pool index of its photo."""

    reason: str = ""
    photo_index: int | None = None


class DemoSiteServiceCardsAnalysis(BaseModel):
    """What the suggestion had to work with (shown under the AI button)."""

    photos_total: int = 0
    photos_labelled: int = 0
    dish_photos: int = 0
    menu_boards: int = 0
    menu_dishes: int = 0
    reviews_used: int = 0
    model: str = ""


class DemoSiteServiceCardsSuggestionResponse(BaseModel):
    """AI-composed cards for the section, plus the refreshed photo pool (labels included)."""

    cards: list[DemoSiteServiceCardSuggestion]
    pool: list[DemoSitePhotoLabel]
    analysis: DemoSiteServiceCardsAnalysis


class DemoSiteImagesResponse(BaseModel):
    """The site's photo pool and its current placement (hero/about/gallery by order)."""

    pool: list[str]
    order: list[str]


class DemoSiteImagesUpdateRequest(BaseModel):
    """New photo placement order: ``[0]`` hero, ``[1]`` about, ``[2:]`` gallery; omitted photos are unused."""

    order: list[str] = Field(default_factory=list, max_length=60)


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
    trades: list[str] = []
    # Canonical colour role → palette key, for the role-based editor (only listed roles are editable).
    color_roles: dict[str, str] = {}
    # Palette key driving the action colour (== color_roles["action"]).
    brand_color_key: str = "primary"
    # Editable-cards section (food « Nos spécialités »); None/disabled hides the cards editor.
    service_cards: DemoSiteServiceCardsConfig | None = None


class DemoSiteResponse(BaseModel):
    """Demo site returned to authenticated users."""

    id: int
    slug: str
    prospect_id: int | None = None
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
    # CMS handover state: not_invited / pending / joined (NULL until first observed).
    storyblok_collaborator_status: str | None = None
    storyblok_joined_at: datetime | None = None
    demo_link_sent_at: datetime | None = None
    # Operator's manual "good to send" sign-off from the campaign forecast (NULL until reviewed).
    site_reviewed_at: datetime | None = None
    expires_at: datetime
    created_at: datetime
    error_message: str | None = None
    theme: DemoSiteTheme | None = None
    # Logo ⟷ Template choice for the action colour.
    use_brand_color: bool = True
    # The colour extracted from the prospect logo (for the "Logo" pill); None when no usable one exists.
    brand_color: str | None = None
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
    # Owner identity for the video-page signature (« Site réalisé par … »).
    owner_name: str | None = None
    owner_company_name: str | None = None
    owner_company_website_url: str | None = None

    model_config = ConfigDict(from_attributes=True)


class DemoSiteListResponse(BaseModel):
    """Paginated list of demo sites for the current user."""

    items: list[DemoSiteResponse]
    total: int
