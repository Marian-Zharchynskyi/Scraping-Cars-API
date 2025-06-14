from datetime import datetime
from sqlalchemy import Integer, String, DateTime
from sqlalchemy.orm import mapped_column, Mapped
from models.base import Base


class ScrapeRequest(Base):
    __tablename__ = "scrape_requests"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    car_brand: Mapped[str] = mapped_column(String, nullable=False)
    car_model: Mapped[str] = mapped_column(String, nullable=False)
    min_year: Mapped[int] = mapped_column(Integer, nullable=True)
    max_year: Mapped[int] = mapped_column(Integer, nullable=True)
    requested_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=datetime.utcnow)
