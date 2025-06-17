from datetime import datetime
from typing import TYPE_CHECKING
from sqlalchemy import Integer, String, DateTime, ForeignKey
from sqlalchemy.orm import mapped_column, Mapped, relationship
from models.base import Base

if TYPE_CHECKING:
    from models.marketplaces import Marketplaces


class ScrapedCar(Base):
    __tablename__ = "scraped_cars"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    request_id: Mapped[int] = mapped_column(Integer, ForeignKey("scrape_requests.id"), nullable=False)
    marketplace_id: Mapped[int] = mapped_column(Integer, ForeignKey("marketplaces.id"), nullable=False)
    car_title: Mapped[str] = mapped_column(String, nullable=False)
    price: Mapped[str] = mapped_column(String, nullable=False)
    currency: Mapped[str] = mapped_column(String, nullable=True)
    year: Mapped[int] = mapped_column(Integer, nullable=True)
    mileage: Mapped[int] = mapped_column(Integer, nullable=True)
    fuel: Mapped[str] = mapped_column(String, nullable=True)
    transmission: Mapped[str] = mapped_column(String, nullable=True)
    engine_capacity: Mapped[str] = mapped_column(String, nullable=True)
    horse_power: Mapped[str] = mapped_column(String, nullable=True)
    car_url: Mapped[str] = mapped_column(String, nullable=False)
    scraped_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=datetime.utcnow)
    status: Mapped[str] = mapped_column(String, nullable=False)
    error_message: Mapped[str] = mapped_column(String, nullable=True)
    
    marketplace: Mapped["Marketplaces"] = relationship("Marketplaces", back_populates="scraped_cars")
