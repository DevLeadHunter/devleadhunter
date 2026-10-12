"""Geocoded city — the centre of a prospected city, looked up once and shared by every coverage map."""

from datetime import datetime

from sqlalchemy import Double, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from core.clock import naive_utc_now
from core.database import UTF8MB4_TABLE_OPTIONS, Base


class GeocodedCity(Base):
    """
    Where a city of one country lies, or the answer that no geocoder knows it.

    Not scoped by user: a city's centre is public data, and sharing it is what lets every device open the map at once.

    Attributes:
        id: Unique identifier
        country: ISO alpha-2 country of the city
        city_key: City name trimmed, lowercased and without accents (« Genève » → « geneve »)
        is_found: False when no geocoder knows the city, kept so the map does not ask again every time
        latitude: Latitude of the city centre
        longitude: Longitude of the city centre
        insee_code: Code of the French commune, empty abroad
        department_code: Code of the French département, empty abroad
        region_code: Code of the French region, empty abroad
        geocoded_at: When the city was looked up (naive UTC)
    """

    __tablename__ = "geocoded_cities"
    __table_args__ = (
        UniqueConstraint("city_key", "country", name="uq_geocoded_cities_city_key_country"),
        UTF8MB4_TABLE_OPTIONS,
    )

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    country: Mapped[str] = mapped_column(String(2), nullable=False)
    city_key: Mapped[str] = mapped_column(String(191), nullable=False)
    is_found: Mapped[bool] = mapped_column(nullable=False)
    latitude: Mapped[float | None] = mapped_column(Double, nullable=True)
    longitude: Mapped[float | None] = mapped_column(Double, nullable=True)
    insee_code: Mapped[str] = mapped_column(String(10), nullable=False, default="")
    department_code: Mapped[str] = mapped_column(String(5), nullable=False, default="")
    region_code: Mapped[str] = mapped_column(String(5), nullable=False, default="")
    geocoded_at: Mapped[datetime] = mapped_column(default=naive_utc_now, nullable=False)
