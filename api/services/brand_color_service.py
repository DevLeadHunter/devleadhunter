"""Extract a prospect's brand colour from its logo, to personalise a generated site's action colour.

A logo often carries the business's signature colour (the red of a garage, the green of a florist…).
We download it, find its dominant *vivid* colour and, only if it clearly passes a saturation/brightness
guard, return it as a hex string. A logo that is mostly black/white/grey (very common) yields ``None`` so
the template keeps its designed palette — the feature never degrades the DA with a muddy colour.
"""

from __future__ import annotations

import colorsys
import logging
from io import BytesIO

import httpx

from services.public_url_guard import PublicOnlyTransport

logger = logging.getLogger(__name__)

# A colour must be this saturated, and neither too dark nor too bright, to read as a real brand colour.
_MIN_SATURATION = 0.35
_MIN_VALUE = 0.20
_MAX_VALUE = 0.92
# White text on a button of this colour must reach the WCAG AA contrast for normal text.
_MIN_CONTRAST_WITH_WHITE = 4.5
_DARKENING_STEP = 0.02


class BrandColorService:
    """Turn a logo image URL into a usable brand hex colour, or None."""

    def extract_brand_color(self, image_url: str | None) -> str | None:
        """Return the logo's dominant vivid colour as ``#RRGGBB``, or None when none is usable.

        Args:
            image_url: The prospect's logo URL (may be None/blank).

        Returns:
            A hex colour string, or None to keep the template palette.
        """
        cleaned = (image_url or "").strip()
        if not cleaned:
            return None
        try:
            from PIL import Image

            with httpx.Client(timeout=8.0, follow_redirects=True, transport=PublicOnlyTransport()) as client:
                response = client.get(cleaned)
            response.raise_for_status()
            image = Image.open(BytesIO(response.content)).convert("RGBA").resize((80, 80))
        except Exception:
            logger.info("Brand colour: could not load logo %s", cleaned, exc_info=True)
            return None
        return self._dominant_vivid_hex(image)

    @classmethod
    def readable_behind_white_text(cls, hex_color: str) -> str:
        """
        The brand colour darkened, hue kept, until white text on it reads well (a lime logo gave an
        unreadable « Demander un devis gratuit » button, 8 Oct 2026); a dark enough colour is kept as is.

        Args:
            hex_color: The brand colour, ``#RRGGBB``.

        Returns:
            The colour, darkened only as much as the contrast with white asks.
        """
        red, green, blue = (int(hex_color[index : index + 2], 16) / 255 for index in (1, 3, 5))
        hue, lightness, saturation = colorsys.rgb_to_hls(red, green, blue)
        while cls.contrast_with_white(red, green, blue) < _MIN_CONTRAST_WITH_WHITE and lightness > 0:
            lightness = max(0.0, lightness - _DARKENING_STEP)
            red, green, blue = colorsys.hls_to_rgb(hue, lightness, saturation)
        return "#" + "".join(f"{round(channel * 255):02X}" for channel in (red, green, blue))

    @staticmethod
    def contrast_with_white(red: float, green: float, blue: float) -> float:
        """The WCAG contrast ratio between white and a colour given as 0-1 channels."""

        def linear(channel: float) -> float:
            """One sRGB channel as linear light."""
            return channel / 12.92 if channel <= 0.04045 else ((channel + 0.055) / 1.055) ** 2.4

        luminance = 0.2126 * linear(red) + 0.7152 * linear(green) + 0.0722 * linear(blue)
        return 1.05 / (luminance + 0.05)

    @staticmethod
    def _dominant_vivid_hex(image: object) -> str | None:
        """Return the most frequent vivid colour of an image, or None when it has none."""
        opaque = [(r, g, b) for (r, g, b, a) in image.getdata() if a > 200]  # type: ignore[attr-defined]
        if not opaque:
            return None
        # Bucket similar colours together, then rank vivid buckets by how many pixels they hold.
        buckets: dict[tuple[int, int, int], list] = {}
        for r, g, b in opaque:
            key = (r // 24, g // 24, b // 24)
            entry = buckets.setdefault(key, [0, 0, 0, 0])
            entry[0] += 1
            entry[1] += r
            entry[2] += g
            entry[3] += b

        best_hex: str | None = None
        best_count = 0
        for count, sum_r, sum_g, sum_b in buckets.values():
            red, green, blue = sum_r // count, sum_g // count, sum_b // count
            _, saturation, value = colorsys.rgb_to_hsv(red / 255, green / 255, blue / 255)
            if saturation < _MIN_SATURATION or not (_MIN_VALUE <= value <= _MAX_VALUE):
                continue
            if count > best_count:
                best_count = count
                best_hex = f"#{red:02X}{green:02X}{blue:02X}"
        return best_hex


brand_color_service = BrandColorService()
