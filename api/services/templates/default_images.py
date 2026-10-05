"""Per-template default images for the flat ``SiteContent`` path.

When a prospect has no usable photo, its generated ``SiteContent`` leaves ``heroImage`` /
``aboutImage`` / ``gallery`` empty, and the demo-host layer fills them at RENDER time from its own
fallback pool — so those default images never reach Storyblok (empty editor fields, no assets, the
client can't see or replace them). Enriched sites don't have this problem: the prospect photos are
real URLs in the content, so ``_upload_external_assets`` uploads them.

This mirrors each layer's fallback pool (the SAME URLs the layer renders) so the API can seed the
empty slots BEFORE pushing to Storyblok: the images then upload as real assets and the client sees
and edits them, while the rendered site is unchanged (identical URLs). Real prospect photos always
win — a slot that already has a value is never overwritten.

⚠️ Manual mirror of the template layers (like ``template_repos.py``): refresh when a layer bumps its
default images. Local bundled images are ABSOLUTE demo-host URLs (served from each layer's public/).
"""

from __future__ import annotations

from typing import Any

# template_id -> {"heroImage": url, "aboutImage": url, "gallery": [url, ...]}. Populated from the
# live template layers (see module docstring). Absolute URLs only (Unsplash or demo-host-hosted).
DEFAULT_IMAGES: dict[str, dict[str, Any]] = {
    "artisan-edito": {
        "heroImage": "https://images.unsplash.com/photo-1660796334912-8ce8e9c2cff0?auto=format&fit=crop&w=1600&q=80",
        "aboutImage": "https://images.unsplash.com/photo-1659930087003-2d64e33181f7?auto=format&fit=crop&w=1200&q=80",
        "gallery": [
            "https://images.unsplash.com/photo-1547609434-b732edfee020?auto=format&fit=crop&w=1200&q=80",
            "https://images.unsplash.com/photo-1679797850019-3d0d8659a695?auto=format&fit=crop&w=1200&q=80",
            "https://images.unsplash.com/photo-1426927308491-6380b6a9936f?auto=format&fit=crop&w=1200&q=80",
            "https://images.unsplash.com/photo-1499744349893-0c6de53516e6?auto=format&fit=crop&w=1200&q=80",
            "https://images.unsplash.com/photo-1453806839674-d1a9087ca1ed?auto=format&fit=crop&w=1200&q=80",
            "https://images.unsplash.com/photo-1589939705384-5185137a7f0f?auto=format&fit=crop&w=1200&q=80",
        ],
    },
    "plumber-signature": {
        "heroImage": "https://images.unsplash.com/photo-1676210134188-4c05dd172f89?auto=format&fit=crop&w=1400&q=80",
        "aboutImage": "https://images.unsplash.com/photo-1676210134190-3f2c0d5cf58d?auto=format&fit=crop&w=1200&q=80",
        "gallery": [
            "https://images.unsplash.com/photo-1584622650111-993a426fbf0a?auto=format&fit=crop&w=1200&q=80",
            "https://images.unsplash.com/photo-1682888818696-906287d759f5?auto=format&fit=crop&w=1200&q=80",
            "https://images.unsplash.com/photo-1744869524920-f0efc925b82f?auto=format&fit=crop&w=1200&q=80",
            "https://images.unsplash.com/photo-1564540579594-0930edb6de43?auto=format&fit=crop&w=1200&q=80",
            "https://images.unsplash.com/photo-1600488999585-e4364713b90a?auto=format&fit=crop&w=1200&q=80",
            "https://images.unsplash.com/photo-1638799869566-b17fa794c4de?auto=format&fit=crop&w=1200&q=80",
        ],
    },
    "plumber-atelier": {
        "heroImage": "https://images.unsplash.com/photo-1676210134188-4c05dd172f89?auto=format&fit=crop&w=1400&q=80",
        "aboutImage": "https://images.unsplash.com/photo-1676210134190-3f2c0d5cf58d?auto=format&fit=crop&w=1200&q=80",
        "gallery": [
            "https://images.unsplash.com/photo-1584622650111-993a426fbf0a?auto=format&fit=crop&w=1200&q=80",
            "https://images.unsplash.com/photo-1682888818696-906287d759f5?auto=format&fit=crop&w=1200&q=80",
            "https://images.unsplash.com/photo-1744869524920-f0efc925b82f?auto=format&fit=crop&w=1200&q=80",
            "https://images.unsplash.com/photo-1564540579594-0930edb6de43?auto=format&fit=crop&w=1200&q=80",
            "https://images.unsplash.com/photo-1600488999585-e4364713b90a?auto=format&fit=crop&w=1200&q=80",
            "https://images.unsplash.com/photo-1638799869566-b17fa794c4de?auto=format&fit=crop&w=1200&q=80",
        ],
    },
    "plumber-cuivre": {
        "heroImage": "https://images.unsplash.com/photo-1676210134188-4c05dd172f89?auto=format&fit=crop&w=1400&q=80",
        "aboutImage": "https://images.unsplash.com/photo-1676210134190-3f2c0d5cf58d?auto=format&fit=crop&w=1200&q=80",
        "gallery": [
            "https://images.unsplash.com/photo-1584622650111-993a426fbf0a?auto=format&fit=crop&w=1200&q=80",
            "https://images.unsplash.com/photo-1682888818696-906287d759f5?auto=format&fit=crop&w=1200&q=80",
            "https://images.unsplash.com/photo-1744869524920-f0efc925b82f?auto=format&fit=crop&w=1200&q=80",
            "https://images.unsplash.com/photo-1564540579594-0930edb6de43?auto=format&fit=crop&w=1200&q=80",
            "https://images.unsplash.com/photo-1600488999585-e4364713b90a?auto=format&fit=crop&w=1200&q=80",
            "https://images.unsplash.com/photo-1638799869566-b17fa794c4de?auto=format&fit=crop&w=1200&q=80",
        ],
    },
    "electrician-eclat": {
        "heroImage": "https://images.unsplash.com/photo-1767710924293-29fba5e3854b?auto=format&fit=crop&w=1400&q=80",
        "aboutImage": "https://images.unsplash.com/photo-1646640381839-02748ae8ddf0?auto=format&fit=crop&w=1200&q=80",
        "gallery": [
            "https://images.unsplash.com/photo-1732194044246-9c5f6bc6582c?auto=format&fit=crop&w=900&q=80",
            "https://images.unsplash.com/photo-1666585607888-3f6fe0b323d8?auto=format&fit=crop&w=900&q=80",
            "https://images.unsplash.com/photo-1788619371179-b3031f2cbe23?auto=format&fit=crop&w=900&q=80",
            "https://images.unsplash.com/photo-1576446470246-499c738d1c8e?auto=format&fit=crop&w=900&q=80",
            "https://images.unsplash.com/photo-1508920291026-c344bbfca1ab?auto=format&fit=crop&w=900&q=80",
            "https://images.unsplash.com/photo-1680416124510-5eae1beca412?auto=format&fit=crop&w=900&q=80",
        ],
    },
    "electrician-lumen": {
        "heroImage": "https://images.unsplash.com/photo-1758101755915-462eddc23f57?auto=format&fit=crop&w=1400&q=80",
        "aboutImage": "https://images.unsplash.com/photo-1687819280272-95f9d2a3cdab?auto=format&fit=crop&w=1200&q=80",
        "gallery": [
            "https://images.unsplash.com/photo-1635335874521-7987db781153?auto=format&fit=crop&w=1200&q=80",
            "https://images.unsplash.com/photo-1576446470246-499c738d1c8e?auto=format&fit=crop&w=1200&q=80",
            "https://images.unsplash.com/photo-1751486289947-4f5f5961b3aa?auto=format&fit=crop&w=1200&q=80",
            "https://images.unsplash.com/photo-1767514536575-82aaf8b0afc4?auto=format&fit=crop&w=1200&q=80",
            "https://images.unsplash.com/photo-1738520420715-23a83fd078f7?auto=format&fit=crop&w=1200&q=80",
            "https://images.unsplash.com/photo-1781781988912-98e2d354f2e5?auto=format&fit=crop&w=1200&q=80",
        ],
    },
    "mechanic-pitlane": {
        "heroImage": "https://images.unsplash.com/photo-1658244535411-92c887137240?auto=format&fit=crop&w=1600&q=80",
        "aboutImage": "https://images.unsplash.com/photo-1613214150132-9606e332d68e?auto=format&fit=crop&w=1200&q=80",
        "gallery": [
            "https://images.unsplash.com/photo-1486262715619-67b85e0b08d3?auto=format&fit=crop&w=1200&q=80",
            "https://images.unsplash.com/photo-1619642751034-765dfdf7c58e?auto=format&fit=crop&w=1200&q=80",
            "https://images.unsplash.com/photo-1637640125496-31852f042a60?auto=format&fit=crop&w=1200&q=80",
            "https://images.unsplash.com/photo-1723099971299-3789db53604c?auto=format&fit=crop&w=1200&q=80",
            "https://images.unsplash.com/photo-1711386689622-1cda23e10217?auto=format&fit=crop&w=1200&q=80",
            "https://images.unsplash.com/photo-1735361039382-d78a0a0cc185?auto=format&fit=crop&w=1200&q=80",
        ],
    },
    "dental": {
        "heroImage": "https://images.unsplash.com/photo-1606811841689-23dfddce3e95?auto=format&fit=crop&w=1400&q=80",
        "aboutImage": "https://images.unsplash.com/photo-1588776814546-1ffcf47267a5?auto=format&fit=crop&w=1200&q=80",
        "gallery": [
            "https://images.unsplash.com/photo-1629909613654-28e377c37b09?auto=format&fit=crop&w=800&q=80",
            "https://images.unsplash.com/photo-1609840114035-3c981b782dfe?auto=format&fit=crop&w=800&q=80",
            "https://images.unsplash.com/photo-1598256989800-fe5f95da9787?auto=format&fit=crop&w=800&q=80",
            "https://images.unsplash.com/photo-1629909615184-74f495363b67?auto=format&fit=crop&w=800&q=80",
        ],
    },
    "food": {
        # Generic food-truck / street-food establishing shots (NOT dishes) — safe for any cuisine.
        "heroImage": "https://images.unsplash.com/photo-1565123409695-7b5ef63a2efb?auto=format&fit=crop&w=1400&q=75",
        "aboutImage": "https://images.unsplash.com/photo-1414235077428-338989a2e8c0?auto=format&fit=crop&w=1200&q=70",
        # No default gallery: a typed dish (burger/wings) clashes with a Mexican / Korean / veggie truck
        # and reads as a template. An empty gallery → the layer keeps a real prospect photo or a text-only
        # menu card, never an off-cuisine stock dish. (Same choice as barber.)
        "gallery": [],
    },
    "barber": {
        "heroImage": "https://images.unsplash.com/photo-1585747860715-2ba37e788b70?auto=format&fit=crop&w=1600&q=80",
        "aboutImage": "https://images.unsplash.com/photo-1503951914875-452162b0f3f1?auto=format&fit=crop&w=1200&q=80",
        "gallery": [],
    },
    "landscaper-verdure": {
        "heroImage": "https://demo.dibodev.fr/images/verdure/image-import-27.jpg",
        "aboutImage": "https://demo.dibodev.fr/images/verdure/image-import-19.jpg",
        "gallery": [
            "https://demo.dibodev.fr/images/verdure/image-import-12.jpg",
            "https://demo.dibodev.fr/images/verdure/image-import.jpg",
        ],
    },
}


def apply_default_images(site_content: dict[str, Any], template_id: str) -> None:
    """Fill empty hero/about/gallery slots with the template's default images, in place.

    Only an EMPTY slot is filled, so real prospect photos are never replaced. No-op when the
    template has no registered defaults or ``site_content`` is not the flat shape.

    Args:
        site_content: The flat ``SiteContent`` dict (mutated in place).
        template_id: The selected template identifier.
    """
    defaults = DEFAULT_IMAGES.get(template_id)
    if not defaults or "businessName" not in site_content:
        return

    if not str(site_content.get("heroImage") or "").strip() and defaults.get("heroImage"):
        site_content["heroImage"] = defaults["heroImage"]
    if not str(site_content.get("aboutImage") or "").strip() and defaults.get("aboutImage"):
        site_content["aboutImage"] = defaults["aboutImage"]
    if not site_content.get("gallery") and defaults.get("gallery"):
        site_content["gallery"] = [{"url": url, "alt": ""} for url in defaults["gallery"]]
