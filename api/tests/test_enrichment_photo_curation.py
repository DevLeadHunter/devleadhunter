"""
The gallery keeps photos that can illustrate a site — measured on the first enrichment round (7 Oct 2026),
where a garage's gallery held its logo four times and a blank Facebook cover beside one real photo.
"""

import asyncio
import base64
import io
import random

from PIL import Image, ImageDraw

from scrappers.enrichment_scraper import GalleryCuration


def _jpeg(image: Image.Image) -> bytes:
    """The image as JPEG bytes."""
    buffer = io.BytesIO()
    image.save(buffer, format="JPEG", quality=90)
    return buffer.getvalue()


def _data_uri(image: Image.Image) -> str:
    """The image as the ``data:`` URI a Facebook capture stores."""
    return "data:image/jpeg;base64," + base64.b64encode(_jpeg(image)).decode("ascii")


def _photo(seed: int, size: tuple[int, int] = (1200, 900)) -> Image.Image:
    """A photo-like image: many colours, no flat area."""
    generator = random.Random(seed)
    small = Image.new("RGB", (48, 36))
    small.putdata(
        [(generator.randrange(256), generator.randrange(256), generator.randrange(256)) for _ in range(48 * 36)]
    )
    return small.resize(size, Image.Resampling.BICUBIC)


def _logo(size: tuple[int, int] = (800, 800), colour: str = "darkgreen") -> Image.Image:
    """A logo-like image: a word on a plain white background."""
    image = Image.new("RGB", size, "white")
    ImageDraw.Draw(image).rectangle([size[0] // 4, size[1] // 3, 3 * size[0] // 4, size[1] // 2], fill=colour)
    return image


def test_a_real_photo_is_fit_for_the_gallery() -> None:
    """Many colours, no flat area, a decent size: a photo."""
    traits = GalleryCuration.traits_of(_jpeg(_photo(1)))

    assert traits is not None and GalleryCuration.unfit_reason(traits) is None


def test_a_logo_on_a_plain_background_is_a_graphic() -> None:
    """One flat colour over most of the image, in few colours: a logo or a flyer."""
    traits = GalleryCuration.traits_of(_jpeg(_logo()))

    assert traits is not None and GalleryCuration.unfit_reason(traits) == "graphic"


def test_a_cover_kept_at_320_pixels_is_too_small() -> None:
    """The Facebook cover read at its 320-pixel size is a blur on a site."""
    traits = GalleryCuration.traits_of(_jpeg(_photo(2, size=(320, 119))))

    assert traits is not None and GalleryCuration.unfit_reason(traits) == "too small"


def test_a_near_uniform_banner_is_blank() -> None:
    """An almost uniform dark banner shows nothing."""
    banner = Image.new("RGB", (960, 360), (30, 30, 34))
    ImageDraw.Draw(banner).rectangle([0, 0, 480, 360], fill=(36, 36, 40))
    traits = GalleryCuration.traits_of(_jpeg(banner))

    assert traits is not None and GalleryCuration.unfit_reason(traits) == "blank"


def test_curation_keeps_photos_and_drops_logo_cover_and_duplicates() -> None:
    """The garage case: the logo re-uploaded, a blank cover, a duplicate, and two real photos."""
    first, second = _data_uri(_photo(3)), _data_uri(_photo(4))
    logo = _data_uri(_logo())
    gallery = [_data_uri(_logo(size=(900, 900))), first, _data_uri(_photo(5, size=(320, 122))), second, first]

    kept = asyncio.run(GalleryCuration.curate(gallery, logo_url=logo))

    assert kept == [first, second]


def test_curation_keeps_what_it_cannot_read() -> None:
    """A photo that does not load is kept: never lose a real photo on a network hiccup."""
    unreadable = "data:image/jpeg;base64,bm90IGFuIGltYWdl"

    assert asyncio.run(GalleryCuration.curate([unreadable])) == [unreadable]
