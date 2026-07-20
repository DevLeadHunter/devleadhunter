"""Presenter (webcam) source clip uploaded once per user.

This is the generic « Léo parle à la caméra » recording reused for every
prospection video: intro full-screen, then shrunk to a picture-in-picture
bubble while the prospect's generated site scrolls behind.
"""
from datetime import datetime
from typing import Optional

from sqlalchemy import Boolean, Float, ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.sql import func

from core.database import Base


class PresenterVideo(Base):
    """One presenter clip per user (upload replaces the previous one)."""

    __tablename__ = "presenter_videos"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id"), nullable=False, unique=True, index=True
    )
    file_path: Mapped[str] = mapped_column(String(512), nullable=False)
    original_filename: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    duration_seconds: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    # Seconds of full-screen webcam at the start (greeting) and at the end (CTA);
    # the prospect's site scrolls in between with the webcam as a small bubble.
    intro_seconds: Mapped[float] = mapped_column(Float, nullable=False, default=4.0)
    outro_seconds: Mapped[float] = mapped_column(Float, nullable=False, default=5.0)
    # Génère automatiquement la vidéo de prospection à chaque site créé.
    auto_generate: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    # « upload » (fichier importé, découpage saisi à la main) ou « recorded »
    # (trois prises filmées dans l'app : les segments sont mesurés, pas devinés).
    source: Mapped[str] = mapped_column(String(16), nullable=False, default="upload")
    created_at: Mapped[datetime] = mapped_column(server_default=func.now(), nullable=False)
    updated_at: Mapped[Optional[datetime]] = mapped_column(onupdate=func.now(), nullable=True)

    def __repr__(self) -> str:
        return f"<PresenterVideo id={self.id} user_id={self.user_id} duration={self.duration_seconds}s>"
