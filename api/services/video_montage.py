"""Pure video-montage primitives shared by the VPS and the desktop sidecar.

This module owns the *rendering* half of the prospection video: the ffmpeg
single-pass composition and the Pillow overlays (greeting pill, circular PiP
mask, email thumbnail). It deliberately depends only on Pillow + system ffmpeg
— no DB, no R2, no models — so the frozen desktop sidecar can bundle and run the
exact same, validated pipeline as the server (each side passing its own ffmpeg
path). The capture (Playwright) and the orchestration (status, R2) live elsewhere.
"""

from __future__ import annotations

import os
import shutil
import subprocess
from pathlib import Path

# Output canvas (16:9, light enough for an email → a player page).
WIDTH = 1280
HEIGHT = 720
FPS = 30

# Webcam picture-in-picture bubble during the site segment.
PIP_SIZE = 260
PIP_MARGIN = 24

# Presenter photo bubble on the email thumbnail (bottom-left, light ring).
PHOTO_BUBBLE_SIZE = 200
PHOTO_BUBBLE_MARGIN = 36
PHOTO_BUBBLE_RING = 7
# The source portrait is moody/dark: lift it so both eyes read at inbox size.
PHOTO_BRIGHTNESS_LIFT = 1.12
# Supersampling factor for a clean circle edge on the bubble mask.
_PHOTO_MASK_SUPERSAMPLE = 4

# ffmpeg thread cap: on the small fallback VPS, letting x264 grab every core
# spikes memory and strangles the single-worker API.
FFMPEG_THREADS = "2"
# Desktop value: "0" lets ffmpeg size itself on the machine's cores, and the
# below-normal process priority keeps the PC responsive while it encodes.
FFMPEG_THREADS_AUTO = "0"


def as_background_priority_process(command: list[str]) -> tuple[list[str], dict[str, int]]:
    """
    Make an ffmpeg command run as a polite background task (Steam-shader style):
    it uses every idle core but yields instantly to whatever the user is doing.

    Args:
        command: The ffmpeg command line.

    Returns:
        The (possibly prefixed) command and the extra ``subprocess.run`` kwargs.
    """
    if os.name == "nt":
        return command, {"creationflags": subprocess.BELOW_NORMAL_PRIORITY_CLASS}
    if shutil.which("nice"):
        return ["nice", "-n", "10", *command], {}
    return command, {}


_FONT_CANDIDATES: tuple[str, ...] = (
    "C:/Windows/Fonts/seguisb.ttf",  # Segoe UI Semibold
    "C:/Windows/Fonts/segoeui.ttf",
    "C:/Windows/Fonts/arialbd.ttf",
    "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
)


class VideoMontageError(Exception):
    """Raised when an ffmpeg/Pillow montage step fails (message shown in-app)."""


def _load_font(size: int):
    """Load a bold-ish system font, falling back to Pillow's default."""
    from PIL import ImageFont

    for candidate in _FONT_CANDIDATES:
        try:
            return ImageFont.truetype(candidate, size)
        except OSError:
            continue
    return ImageFont.load_default(size=size)


def build_greeting_overlay(first_name: str | None, work_dir: Path) -> Path:
    """
    Render the transparent intro overlay: « Bonjour {Prénom} » in a pill.

    Text, not cloned voice — the personal touch is visual (same rule as the
    {salutation} email variable: a safe greeting, never a wrong name).

    Args:
        first_name: The prospect's first name, or None for a neutral greeting.
        work_dir: Directory the PNG is written to.

    Returns:
        Path to the greeting PNG.
    """
    from PIL import Image, ImageDraw

    text = f"Bonjour {first_name} !" if first_name else "Bonjour !"
    font = _load_font(54)

    image = Image.new("RGBA", (WIDTH, HEIGHT), (0, 0, 0, 0))
    draw = ImageDraw.Draw(image)
    text_box = draw.textbbox((0, 0), text, font=font)
    text_w = text_box[2] - text_box[0]
    text_h = text_box[3] - text_box[1]

    pad_x, pad_y = 44, 24
    pill_w = text_w + pad_x * 2
    pill_h = text_h + pad_y * 2
    x0 = (WIDTH - pill_w) // 2
    y0 = HEIGHT - pill_h - 64
    draw.rounded_rectangle(
        (x0, y0, x0 + pill_w, y0 + pill_h),
        radius=pill_h // 2,
        fill=(255, 255, 255, 235),
    )
    draw.text(
        (x0 + pad_x - text_box[0], y0 + pad_y - text_box[1]),
        text,
        font=font,
        fill=(17, 17, 17, 255),
    )

    path = work_dir / "greeting.png"
    image.save(path)
    return path


def build_circle_mask(work_dir: Path) -> Path:
    """White circle on black, used to round the webcam PiP bubble."""
    from PIL import Image, ImageDraw

    mask = Image.new("L", (PIP_SIZE, PIP_SIZE), 0)
    draw = ImageDraw.Draw(mask)
    draw.ellipse((0, 0, PIP_SIZE - 1, PIP_SIZE - 1), fill=255)
    path = work_dir / "pip-mask.png"
    mask.save(path)
    return path


def _paste_presenter_photo_bubble(overlay, draw, photo_path: Path, thumb_h: int) -> None:
    """
    Draw the presenter photo as a round bubble with a light ring, bottom-left.

    A human face is the strongest trust cue in the inbox; the bubble mirrors the
    webcam PiP the prospect will see in the video itself. An unreadable photo is
    skipped silently — it must never fail a whole video generation.

    Args:
        overlay: RGBA overlay layer of the thumbnail (mutated in place).
        draw: Draw handle bound to that overlay.
        photo_path: Normalised square portrait (see presenter photo upload).
        thumb_h: Thumbnail height, to anchor the bubble at the bottom.
    """
    from PIL import Image, ImageDraw, ImageEnhance, ImageOps

    try:
        photo = ImageOps.exif_transpose(Image.open(photo_path)).convert("RGB")
    except OSError:
        return

    side = min(photo.size)
    left = (photo.width - side) // 2
    top = (photo.height - side) // 2
    photo = photo.crop((left, top, left + side, top + side))

    supersampled = PHOTO_BUBBLE_SIZE * _PHOTO_MASK_SUPERSAMPLE
    photo = photo.resize((supersampled, supersampled), Image.LANCZOS)
    photo = ImageEnhance.Brightness(photo).enhance(PHOTO_BRIGHTNESS_LIFT)
    mask = Image.new("L", (supersampled, supersampled), 0)
    ImageDraw.Draw(mask).ellipse((0, 0, supersampled, supersampled), fill=255)
    bubble = Image.new("RGBA", (supersampled, supersampled), (0, 0, 0, 0))
    bubble.paste(photo, (0, 0), mask)
    bubble = bubble.resize((PHOTO_BUBBLE_SIZE, PHOTO_BUBBLE_SIZE), Image.LANCZOS)

    x0 = PHOTO_BUBBLE_MARGIN
    y0 = thumb_h - PHOTO_BUBBLE_MARGIN - PHOTO_BUBBLE_SIZE
    ring = PHOTO_BUBBLE_RING
    draw.ellipse(
        (x0 - ring, y0 - ring, x0 + PHOTO_BUBBLE_SIZE + ring, y0 + PHOTO_BUBBLE_SIZE + ring),
        fill=(255, 255, 255, 235),
    )
    overlay.paste(bubble, (x0, y0), bubble)


def build_thumbnail(
    screenshot_path: Path,
    first_name: str | None,
    output_path: Path,
    presenter_photo_path: Path | None = None,
) -> None:
    """
    Build the personalised email thumbnail: site screenshot, slight darkening,
    centered play button, « Bonjour {Prénom} » pill, presenter photo bubble.

    The thumbnail is THE click lever in the inbox — it must read as a video
    (play button), as personal (his site + his first name) and as human (the
    presenter's face).

    Args:
        screenshot_path: Top-of-site screenshot used as the poster.
        first_name: The prospect's first name, or None.
        output_path: JPEG destination.
        presenter_photo_path: Optional square portrait for the bubble.
    """
    from PIL import Image, ImageDraw, ImageEnhance

    # 1280x720 (= the video canvas) so the poster stays sharp full-screen on the player.
    thumb_w, thumb_h = WIDTH, HEIGHT
    image = Image.open(screenshot_path).convert("RGB").resize((thumb_w, thumb_h))
    image = ImageEnhance.Brightness(image).enhance(0.82)

    overlay = Image.new("RGBA", (thumb_w, thumb_h), (0, 0, 0, 0))
    draw = ImageDraw.Draw(overlay)

    # Centered play button (white circle, dark triangle).
    radius = 92
    cx, cy = thumb_w // 2, thumb_h // 2
    draw.ellipse(
        (cx - radius, cy - radius, cx + radius, cy + radius),
        fill=(255, 255, 255, 235),
    )
    tri = 40
    draw.polygon(
        [(cx - tri // 2 + 6, cy - tri), (cx - tri // 2 + 6, cy + tri), (cx + tri + 6 - tri // 2, cy)],
        fill=(17, 17, 17, 255),
    )

    # Greeting pill, top-left.
    text = f"Bonjour {first_name} — votre site en vidéo" if first_name else "Votre site en vidéo"
    font = _load_font(44)
    text_box = draw.textbbox((0, 0), text, font=font)
    text_w = text_box[2] - text_box[0]
    text_h = text_box[3] - text_box[1]
    pad_x, pad_y = 32, 20
    x0, y0 = 32, 32
    draw.rounded_rectangle(
        (x0, y0, x0 + text_w + pad_x * 2, y0 + text_h + pad_y * 2),
        radius=(text_h + pad_y * 2) // 2,
        fill=(255, 255, 255, 235),
    )
    draw.text(
        (x0 + pad_x - text_box[0], y0 + pad_y - text_box[1]),
        text,
        font=font,
        fill=(17, 17, 17, 255),
    )

    if presenter_photo_path is not None and presenter_photo_path.is_file():
        _paste_presenter_photo_bubble(overlay, draw, presenter_photo_path, thumb_h)

    composed = Image.alpha_composite(image.convert("RGBA"), overlay).convert("RGB")
    output_path.parent.mkdir(parents=True, exist_ok=True)
    composed.save(output_path, format="JPEG", quality=85)


def extract_first_frame(ffmpeg_path: str, video_path: Path, output_path: Path, threads: str = FFMPEG_THREADS) -> None:
    """Grab the first frame of a video (top of the site) for the email thumbnail poster."""
    command, run_kwargs = as_background_priority_process(
        [
            ffmpeg_path,
            "-y",
            "-hide_banner",
            "-loglevel",
            "error",
            "-threads",
            threads,
            "-i",
            str(video_path),
            "-frames:v",
            "1",
            str(output_path),
        ]
    )
    subprocess.run(
        command,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        timeout=60,
        check=False,
        **run_kwargs,
    )


def compose(
    *,
    ffmpeg_path: str,
    presenter_path: Path,
    capture_path: Path,
    scroll_offset: float,
    scroll_seconds: float,
    duration: float,
    intro: float,
    outro: float,
    greeting_path: Path,
    mask_path: Path,
    output_path: Path,
    threads: str = FFMPEG_THREADS,
) -> None:
    """
    Single-pass ffmpeg composition.

    Base = presenter clip (full canvas, carries the audio). The site capture
    covers it between intro and D-outro, with the webcam shrunk to a circular PiP
    bubble; the greeting pill fades in/out during the intro. ``threads`` keeps the
    VPS cap by default; the desktop passes ``FFMPEG_THREADS_AUTO``.

    Raises:
        VideoMontageError: when ffmpeg is missing, times out, or fails.
    """
    site_end = duration - outro
    fade_out_start = max(intro - 0.5, 0.4)

    # NB filtergraph: inside single quotes, NO escaping — the commas of between()/min()
    # are literal and valid there.
    filter_complex = (
        f"[0:v]scale={WIDTH}:{HEIGHT}:force_original_aspect_ratio=increase,"
        f"crop={WIDTH}:{HEIGHT},setsar=1,fps={FPS},split=2[pres_full][pip_src];"
        f"[1:v]scale={WIDTH}:{HEIGHT}:force_original_aspect_ratio=increase,"
        f"crop={WIDTH}:{HEIGHT},setsar=1,fps={FPS},setpts=PTS+{intro:.3f}/TB[site];"
        f"[pip_src]crop='min(iw,ih)':'min(iw,ih)',scale={PIP_SIZE}:{PIP_SIZE},format=rgba[pip_sq];"
        f"[3:v]format=gray[pip_mask];"
        f"[pip_sq][pip_mask]alphamerge[pip];"
        f"[pres_full][site]overlay=0:0:eof_action=pass:"
        f"enable='between(t,{intro:.3f},{site_end:.3f})'[with_site];"
        f"[with_site][pip]overlay={PIP_MARGIN}:H-h-{PIP_MARGIN}:eof_action=pass:"
        f"enable='between(t,{intro:.3f},{site_end:.3f})'[with_pip];"
        f"[2:v]format=rgba,fade=in:st=0.3:d=0.4:alpha=1,"
        f"fade=out:st={fade_out_start:.3f}:d=0.5:alpha=1[greeting];"
        f"[with_pip][greeting]overlay=0:0:eof_action=pass:"
        f"enable='between(t,0,{intro:.3f})'[vout]"
    )

    command = [
        ffmpeg_path,
        "-y",
        "-hide_banner",
        "-loglevel",
        "error",
        "-threads",
        threads,
        "-i",
        str(presenter_path),
        "-ss",
        f"{max(scroll_offset, 0):.3f}",
        "-t",
        f"{scroll_seconds + 0.5:.3f}",
        "-i",
        str(capture_path),
        "-loop",
        "1",
        "-t",
        f"{intro + 1:.3f}",
        "-i",
        str(greeting_path),
        "-loop",
        "1",
        "-t",
        f"{duration:.3f}",
        "-i",
        str(mask_path),
        "-filter_complex",
        filter_complex,
        "-map",
        "[vout]",
        "-map",
        "0:a?",
        "-t",
        f"{duration:.3f}",
        "-c:v",
        "libx264",
        "-preset",
        "veryfast",
        "-crf",
        "22",
        "-pix_fmt",
        "yuv420p",
        "-c:a",
        "aac",
        "-b:a",
        "128k",
        "-ar",
        "44100",
        "-movflags",
        "+faststart",
        str(output_path),
    ]

    command, run_kwargs = as_background_priority_process(command)
    try:
        result = subprocess.run(command, stdout=subprocess.DEVNULL, stderr=subprocess.PIPE, timeout=600, **run_kwargs)
    except FileNotFoundError as exc:
        raise VideoMontageError(f"ffmpeg introuvable ({ffmpeg_path}). Installez-le ou configurez FFMPEG_PATH.") from exc
    except subprocess.TimeoutExpired as exc:
        raise VideoMontageError("Montage ffmpeg trop long (timeout 10 min).") from exc

    if result.returncode != 0:
        detail = result.stderr.decode("utf-8", errors="replace").strip()[-500:]
        raise VideoMontageError(f"Échec du montage ffmpeg : {detail}")
    if not output_path.is_file() or output_path.stat().st_size == 0:
        raise VideoMontageError("Le montage ffmpeg n'a produit aucun fichier.")


def compose_final(
    *,
    ffmpeg_path: str,
    presenter_duration: float,
    presenter_intro: float,
    presenter_outro: float,
    presenter_path: Path,
    capture_path: Path,
    scroll_offset: float,
    scroll_seconds: float,
    first_name: str | None,
    screenshot_path: Path,
    output_video: Path,
    output_thumbnail: Path,
    presenter_photo_path: Path | None = None,
    threads: str = FFMPEG_THREADS,
) -> None:
    """
    Full montage from primitives: greeting + mask, ffmpeg compose, thumbnail.

    Blocking (ffmpeg + Pillow) — callers run it in a worker thread. Reused by the
    VPS and the desktop sidecar, which passes its own bundled ``ffmpeg_path``.

    Raises:
        VideoMontageError: when a step fails.
    """
    work_dir = output_video.parent
    greeting_path = build_greeting_overlay(first_name, work_dir)
    mask_path = build_circle_mask(work_dir)
    compose(
        ffmpeg_path=ffmpeg_path,
        presenter_path=presenter_path,
        capture_path=capture_path,
        scroll_offset=scroll_offset,
        scroll_seconds=scroll_seconds,
        duration=presenter_duration,
        intro=presenter_intro,
        outro=presenter_outro,
        greeting_path=greeting_path,
        mask_path=mask_path,
        output_path=output_video,
        threads=threads,
    )
    build_thumbnail(screenshot_path, first_name, output_thumbnail, presenter_photo_path)
