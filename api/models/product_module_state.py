"""Whether an optional product module is switched on, platform-wide."""

from datetime import datetime

from sqlalchemy import Boolean, DateTime, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from core.database import Base


class ProductModuleState(Base):
    """The super admin's switch for one optional product module (the websites module has none: it is the core)."""

    __tablename__ = "product_modules"

    module_key: Mapped[str] = mapped_column(String(64), primary_key=True)
    is_enabled: Mapped[bool] = mapped_column(Boolean, nullable=False)
    updated_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True, default=None)
    # No foreign key: purging a user never trips on the switches.
    updated_by_user_id: Mapped[int | None] = mapped_column(Integer, nullable=True, default=None)

    def __repr__(self) -> str:
        """String representation of the switch."""
        return f"<ProductModuleState {self.module_key} enabled={self.is_enabled}>"
