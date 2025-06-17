from datetime import datetime
from sqlalchemy import Integer, String, DateTime, ForeignKey, JSON, Float, Text, Boolean
from sqlalchemy.orm import mapped_column, Mapped
from models.base import Base
from typing import Dict, Any, Optional

class RegressionModel(Base):
    __tablename__ = "regression_models"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String, nullable=False)
    target_variable: Mapped[str] = mapped_column(String, nullable=False)
    feature_variables: Mapped[dict] = mapped_column(JSON, nullable=False)
    coefficients: Mapped[dict] = mapped_column(JSON, nullable=False)
    intercept: Mapped[float] = mapped_column(Float, nullable=False)
    
    # Model quality metrics
    r_squared: Mapped[float] = mapped_column(Float, nullable=False)
    adj_r_squared: Mapped[float] = mapped_column(Float, nullable=True)
    f_statistic: Mapped[float] = mapped_column(Float, nullable=True)
    f_p_value: Mapped[float] = mapped_column(Float, nullable=True)
    n_observations: Mapped[int] = mapped_column(Integer, nullable=True)
    
    # Detailed model statistics
    model_summary: Mapped[Dict[str, Any]] = mapped_column(JSON, nullable=True)
    
    # Standard errors and confidence intervals
    standard_errors: Mapped[Dict[str, float]] = mapped_column(JSON, nullable=True)
    t_statistics: Mapped[Dict[str, float]] = mapped_column(JSON, nullable=True)
    p_values: Mapped[Dict[str, float]] = mapped_column(JSON, nullable=True)
    confidence_intervals: Mapped[Dict[str, tuple[float, float]]] = mapped_column(JSON, nullable=True)
    
    # Metadata
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    marketplace_id: Mapped[Optional[int]] = mapped_column(Integer, ForeignKey("marketplaces.id"), nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    