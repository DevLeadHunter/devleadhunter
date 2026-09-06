"""Package the scraping sidecar as the single binary Tauri bundles.

Tauri resolves `externalBin` by appending the Rust target triple to the name, so
the output must land in `web/src-tauri/binaries/devleadhunter-scraper-<triple>`.

Run from `api/`:  ``python build_scraper_sidecar.py``
"""

from __future__ import annotations

import os
import shutil
import subprocess
import sys
from pathlib import Path

API_DIR = Path(__file__).resolve().parent
BINARIES_DIR = API_DIR.parent / "web" / "src-tauri" / "binaries"
BINARY_STEM = "devleadhunter-scraper"


def target_triple() -> str:
    """Rust target triple of the host, as Tauri expects it in the file name.

    Returns:
        The triple reported by ``rustc``.

    Raises:
        RuntimeError: rustc is unavailable or printed no host triple.
    """
    try:
        output = subprocess.run(
            ["rustc", "-vV"],
            capture_output=True,
            text=True,
            check=True,
        ).stdout
    except (OSError, subprocess.CalledProcessError) as exc:
        raise RuntimeError("rustc introuvable : installez Rust pour connaître la cible.") from exc

    for line in output.splitlines():
        if line.startswith("host:"):
            return line.split("host:", 1)[1].strip()
    raise RuntimeError("Impossible de lire la cible depuis `rustc -vV`.")


def main() -> None:
    """Build the one-file binary and drop it where Tauri looks for it."""
    triple = target_triple()
    suffix = ".exe" if sys.platform == "win32" else ""
    BINARIES_DIR.mkdir(parents=True, exist_ok=True)

    command = [
        sys.executable,
        "-m",
        "PyInstaller",
        "--onefile",
        "--noconsole" if sys.platform == "win32" else "--console",
        "--name",
        BINARY_STEM,
        # nodriver et uvicorn chargent leurs modules dynamiquement : sans ces
        # imports cachés, le binaire démarre puis meurt au premier appel.
        "--hidden-import",
        "uvicorn.protocols.http.h11_impl",
        "--hidden-import",
        "uvicorn.protocols.websockets.websockets_impl",
        "--hidden-import",
        "uvicorn.lifespan.on",
        "--collect-all",
        "nodriver",
        # Playwright renders the Storyblok editor video background; its node driver
        # must be bundled (the browser itself is the sidecar's provisioned Chrome).
        "--collect-all",
        "playwright",
        # Pillow draws the greeting pill + thumbnail during the desktop montage; its
        # plugins load lazily, so collect them explicitly or the frozen build misses them.
        "--collect-all",
        "PIL",
        "--distpath",
        str(API_DIR / "dist"),
        "--workpath",
        str(API_DIR / "build"),
        "--specpath",
        str(API_DIR),
        str(API_DIR / "scraper_sidecar.py"),
    ]

    # Bundle a static ffmpeg AND ffprobe so desktop video generation is plug-and-play
    # (a user never installs them). The workflow downloads them and points the env vars
    # here; both land at the frozen root (sys._MEIPASS/), where the sidecar resolves
    # ffmpeg and the clip service derives ffprobe from it.
    separator = ";" if sys.platform == "win32" else ":"
    for env_name, label in (("FFMPEG_BUNDLE_PATH", "ffmpeg"), ("FFPROBE_BUNDLE_PATH", "ffprobe")):
        bundle = os.environ.get(env_name, "").strip()
        if bundle and Path(bundle).is_file():
            command[-1:-1] = ["--add-binary", f"{bundle}{separator}."]
            print(f"Bundling {label}: {bundle}")
        else:
            print(f"{env_name} unset/missing — sidecar relies on PATH {label} (not plug-and-play).")

    subprocess.run(command, check=True, cwd=API_DIR)

    built = API_DIR / "dist" / f"{BINARY_STEM}{suffix}"
    if not built.is_file():
        raise RuntimeError(f"Binaire absent après build : {built}")

    destination = BINARIES_DIR / f"{BINARY_STEM}-{triple}{suffix}"
    shutil.copy2(built, destination)
    print(f"Sidecar prêt : {destination}")


if __name__ == "__main__":
    main()
