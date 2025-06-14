from datetime import datetime
from sqlalchemy import Integer, String, DateTime, Boolean
from sqlalchemy.orm import mapped_column, Mapped
from models.base import Base


class Marketplaces(Base):
    __tablename__ = "marketplaces"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String, unique=True, nullable=False)
    base_search_url: Mapped[str] = mapped_column(String, nullable=False)
    car_selector: Mapped[str] = mapped_column(String, nullable=False)
    title_selector: Mapped[str] = mapped_column(String, nullable=False)
    price_selector: Mapped[str] = mapped_column(String, nullable=False)
    year_selector: Mapped[str] = mapped_column(String, nullable=False)
    mileage_selector: Mapped[str] = mapped_column(String, nullable=False)
    fuel_selector: Mapped[str] = mapped_column(String, nullable=False)
    transmission_selector: Mapped[str] = mapped_column(String, nullable=False)
    engine_capacity_selector: Mapped[str] = mapped_column(String, nullable=False)
    seats_selector: Mapped[str] = mapped_column(String, nullable=False)
    horse_power_selector: Mapped[str] = mapped_column(String, nullable=False)
    link_selector: Mapped[str] = mapped_column(String, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow
    )
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
