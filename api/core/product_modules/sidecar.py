"""
What a product module's routes on the desktop sidecar may use: the build machinery of the site videos.

The sidecar (``scraper_sidecar.py``) is the local API the Windows app runs on the owner's PC; it films the demos and
montages the prospection videos. A module with a video of its own (the receptionist's widget answering) adds its
route there and builds through this machinery, so its builds report progress and hand their file over exactly like
the site's.
"""

from __future__ import annotations

from collections.abc import Callable, Coroutine
from pathlib import Path
from typing import Any, Protocol

from fastapi import UploadFile
from pydantic import BaseModel


class SidecarVideoBuildRequest(Protocol):
    """The fields of a desktop build request a module's capture reads."""

    slug: str
    demo_url: str
    total_seconds: float
    out_width: int
    out_height: int
    fps: int
    preview: bool


ModuleVideoCapture = Callable[[Any, Path], Coroutine[Any, Any, tuple[Path, Path]]]


class SidecarVideoBuildApi(Protocol):
    """The sidecar's video builds, lent to a product module's routes."""

    screenshot_file_name: str

    def require_token(self, x_sidecar_token: str) -> None:
        """The dependency that refuses a call without the app's sidecar token."""

    def parse_request(self, payload: str) -> BaseModel:
        """Read and check the JSON payload of a build (422 on an invalid one)."""

    async def start(
        self,
        request: BaseModel,
        presenter: UploadFile,
        presenter_photo: UploadFile | None,
        *,
        capture: ModuleVideoCapture,
        thumbnail_label: str,
        pip_corner: str,
        preparing_message: str | None = None,
    ) -> dict[str, object]:
        """Save the uploads and start the build detached: capture (request, work dir) → montage → pickup."""

    def chrome_executable(self) -> str | None:
        """The Chrome the sidecar films with."""

    def report_progress(self, slug: str, step: str, message: str | None = None) -> None:
        """Record a build step the app's progress modal shows."""
