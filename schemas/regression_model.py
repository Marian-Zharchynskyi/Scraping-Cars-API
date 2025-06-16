from pydantic import BaseModel, Field
from typing import Optional, Dict, List, Any
from datetime import datetime

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
    created_at: datetime
    is_active: bool

    class Config:
        from_attributes = True

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

class ModelPredictionRequest(BaseModel):
    target_variable: str
    features: Dict[str, Any]
    marketplace_id: Optional[int] = None
