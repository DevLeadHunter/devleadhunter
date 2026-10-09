"""Presenter (webcam) takes, recorded or imported per sellable module.

A take is the generic « Léo parle à la caméra » recording reused for every
prospection video: intro full-screen, then shrunk to a picture-in-picture
bubble while the prospect's generated site (or assistant) plays behind. Each
module carries its own takes, because the speech differs (a site pitch is not
an assistant pitch) — see ``module``. A new take never replaces the previous
ones: the user compares them and picks the one the videos use (``is_active``).
"""

from datetime import datetime

from sqlalchemy import Boolean, Float, ForeignKey, Index, Integer, String, true
from sqlalchemy.orm import Mapped, mapped_column

from core.database import Base


class PresenterVideo(Base):
    """One presenter take; a user keeps several per module and exactly one of them is in use."""

    __tablename__ = "presenter_videos"
    __table_args__ = (Index("ix_presenter_user_module", "user_id", "module"),)

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False, index=True)
    # The sellable module this clip belongs to ('websites' / 'ai-assistant').
    module: Mapped[str] = mapped_column(String(32), nullable=False, default="websites", server_default="websites")
    take_number: Mapped[int] = mapped_column(Integer, nullable=False, default=1, server_default="1")
    # Exactly one take per user and module: the one every prospection video is built with.
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True, server_default=true())
    # When the take became the one in use: the videos published before were made with an older take.
    in_use_since: Mapped[datetime | None] = mapped_column(nullable=True)
    file_path: Mapped[str] = mapped_column(String(512), nullable=False)
    original_filename: Mapped[str | None] = mapped_column(String(255), nullable=True)
    duration_seconds: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    # Seconds of full-screen webcam at the start (greeting) and at the end (CTA);
    # the prospect's site scrolls in between with the webcam as a small bubble.
    intro_seconds: Mapped[float] = mapped_column(Float, nullable=False, default=4.0)
    outro_seconds: Mapped[float] = mapped_column(Float, nullable=False, default=5.0)
    # User-chosen length of the site-scroll part inside the middle segment; the
    # Storyblok editor sequence gets the remainder. NULL = automatic split.
    site_seconds: Mapped[float | None] = mapped_column(Float, nullable=True)
    # Génère automatiquement la vidéo de prospection à chaque site créé.
    auto_generate: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    # « upload » (fichier importé, découpage saisi à la main) ou « recorded »
    # (trois prises filmées dans l'app : les segments sont mesurés, pas devinés).
    source: Mapped[str] = mapped_column(String(16), nullable=False, default="upload")
    # The finished video this take gives on one of the user's demos.
    example_video_key: Mapped[str | None] = mapped_column(String(512), nullable=True)
    example_subject_id: Mapped[int | None] = mapped_column(Integer, nullable=True)
    example_subject_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    example_generated_at: Mapped[datetime | None] = mapped_column(nullable=True)
    created_at: Mapped[datetime] = mapped_column(default=datetime.utcnow, nullable=False)
    updated_at: Mapped[datetime | None] = mapped_column(onupdate=datetime.utcnow, nullable=True)

    def __repr__(self) -> str:
        return (
            f"<PresenterVideo id={self.id} user_id={self.user_id} module={self.module} "
            f"take={self.take_number} active={self.is_active}>"
        )
