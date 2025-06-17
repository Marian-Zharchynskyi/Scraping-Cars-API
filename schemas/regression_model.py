from pydantic import BaseModel, Field, field_validator
from typing import Optional, Dict, List, Any, Tuple
from datetime import datetime
from typing_extensions import TypedDict

class ModelSummary(TypedDict):
    """Detailed model statistics summary."""
    dep_variable: str
    model: str
    method: str
    no_observations: int
    df_model: float
    df_resid: float
    nobs: float
    df: float
    aic: float | None
    bic: float | None

class RegressionModelBase(BaseModel):
    name: str
    target_variable: str
    feature_variables: List[str]
    marketplace_id: Optional[int] = None
    description: Optional[str] = None

class RegressionModelCreate(RegressionModelBase):
    pass

class RegressionModelUpdate(BaseModel):
    name: Optional[str] = None
    is_active: Optional[bool] = None
    description: Optional[str] = None

class RegressionModelInDBBase(RegressionModelBase):
    id: int
    coefficients: Dict[str, float]
    intercept: float
    r_squared: float
    adj_r_squared: Optional[float] = None
    f_statistic: Optional[float] = None
    f_p_value: Optional[float] = None
    n_observations: Optional[int] = None
    model_summary: Optional[ModelSummary] = None
    standard_errors: Dict[str, float] = Field(default_factory=dict)
    t_statistics: Dict[str, float] = Field(default_factory=dict)
    p_values: Dict[str, float] = Field(default_factory=dict)
    confidence_intervals: Dict[str, Tuple[float, float]] = Field(default_factory=dict)
    created_at: datetime
    updated_at: Optional[datetime] = None
    is_active: bool

    @field_validator('standard_errors', 't_statistics', 'p_values', 'confidence_intervals', mode='before')
    @classmethod
    def ensure_dict(cls, v):
        return v or {}
        

    class Config:
        from_attributes = True
        json_encoders = {
            datetime: lambda v: v.isoformat() if v else None
        }

class RegressionModel(RegressionModelInDBBase):
    pass

class ModelTrainingRequest(BaseModel):
    target_variable: str
    feature_variables: List[str]
    marketplace_id: Optional[int] = None
    car_brands: Optional[List[str]] = Field(
        None,
        description="Список марок автомобілів для аналізу. Якщо не вказано, аналізуються всі марки."
    )
    test_size: float = Field(
        0.2,
        ge=0.1,
        le=0.5,
        description="Частка даних для тестової вибірки (від 0.1 до 0.5)"
    )
    random_state: int = Field(
        42,
        description="Зерно для відтворюваності результатів"
    )

class ModelTrainingResponse(BaseModel):
    """Response model for model training endpoint."""
    success: bool
    model_id: int
    r_squared: float
    adj_r_squared: Optional[float] = None
    f_statistic: Optional[float] = None
    f_p_value: Optional[float] = None
    n_observations: int
    coefficients: Dict[str, float]
    intercept: float
    standard_errors: Dict[str, float] = Field(default_factory=dict)
    t_statistics: Dict[str, float] = Field(default_factory=dict)
    p_values: Dict[str, float] = Field(default_factory=dict)
    confidence_intervals: Dict[str, Tuple[float, float]] = Field(default_factory=dict)
    message: str


class ModelPredictionRequest(BaseModel):
    """Request model for making predictions.
    
    Attributes:
        target_variable: The target variable to predict (e.g., 'price', 'search_position')
        features: Dictionary of feature names and values for prediction
        marketplace_id: Optional marketplace ID to filter models
        model_id: Optional specific model ID to use for prediction
    """
    target_variable: str
    features: Dict[str, Any]
    marketplace_id: Optional[int] = None
    model_id: Optional[int] = Field(
        None,
        description="Specific model ID to use. If not provided, the latest model for the target variable will be used."
    )
    
    @field_validator('features')
    def validate_features(cls, v):
        if not v:
            raise ValueError("Features dictionary cannot be empty")
        return v
