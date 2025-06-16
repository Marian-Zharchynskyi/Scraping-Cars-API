from datetime import datetime
from sqlalchemy import Integer, String, DateTime, ForeignKey, JSON, Float
from sqlalchemy.orm import mapped_column, Mapped
from models.base import Base


class RegressionModel(Base):
    __tablename__ = "regression_models"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String, nullable=False)
    target_variable: Mapped[str] = mapped_column(String, nullable=False)
    feature_variables: Mapped[dict] = mapped_column(JSON, nullable=False)
    coefficients: Mapped[dict] = mapped_column(JSON, nullable=False)
    intercept: Mapped[float] = mapped_column(Float, nullable=False)
    r_squared: Mapped[float] = mapped_column(Float, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    marketplace_id: Mapped[int] = mapped_column(Integer, ForeignKey("marketplaces.id"), nullable=True)
    is_active: Mapped[bool] = mapped_column(default=True)
    description: Mapped[str] = mapped_column(String, nullable=True)
