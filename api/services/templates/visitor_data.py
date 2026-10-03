"""What a template's Nuxt layer does with a visitor's data, as the site's privacy notice must state it.

The layers live in their own repositories: each template module mirrors here the behaviour of
the layer tag that demo-host pins, so the privacy notice of a site never promises more, or
less, than what its page really loads and sends.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class TemplateVisitorData:
    """The visitor-facing data flows of one template layer.

    Attributes:
        has_contact_form: The page has a form, which only prepares an email in the visitor's own mail app.
        has_google_fonts: The page loads its fonts from Google Fonts.
        has_google_map: The page embeds a Google Maps frame.
        has_vehicle_plate_lookup: The page sends a typed licence plate to the Auto Ways service to name the vehicle.
    """

    has_contact_form: bool = False
    has_google_fonts: bool = False
    has_google_map: bool = False
    has_vehicle_plate_lookup: bool = False
