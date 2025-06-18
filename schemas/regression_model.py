from pydantic import BaseModel, Field, field_validator
from typing import Optional, Dict, List, Any, Tuple
from datetime import datetime
from typing_extensions import TypedDict


class ModelSummary(TypedDict):
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
    name: str = Field(..., min_length=1, max_length=255, description="Назва регресійної моделі")
    target_variable: str = Field(
        ...,
        min_length=1,
        max_length=100,
        description="Цільова змінна для прогнозування (наприклад, 'price', 'search_position')",
    )
    feature_variables: List[str] = Field(
        ..., min_length=1, max_length=50, description="Список змінних-ознак для моделі"
    )
    marketplace_id: Optional[int] = Field(None, ge=1, description="ID майданчику (опціонально)")
    description: Optional[str] = Field(None, max_length=1000, description="Опис моделі")


class RegressionModelCreate(RegressionModelBase):
    pass


class RegressionModelUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=1, max_length=255, description="Назва регресійної моделі")
    is_active: Optional[bool] = Field(None, description="Чи активна модель")
    description: Optional[str] = Field(None, max_length=1000, description="Опис моделі")


class RegressionModelInDBBase(RegressionModelBase):
    id: int = Field(..., ge=1, description="Унікальний ідентифікатор моделі")
    coefficients: Dict[str, float] = Field(..., description="Коефіцієнти регресії для кожної ознаки")
    intercept: float = Field(..., description="Вільний член регресійного рівняння")
    r_squared: float = Field(..., ge=0, le=1, description="Коефіцієнт детермінації (R²)")
    adj_r_squared: Optional[float] = Field(None, ge=0, le=1, description="Скоригований коефіцієнт детермінації")
    f_statistic: Optional[float] = Field(None, ge=0, description="F-статистика")
    f_p_value: Optional[float] = Field(None, ge=0, le=1, description="P-значення для F-статистики")
    n_observations: Optional[int] = Field(None, ge=1, description="Кількість спостережень")
    model_summary: Optional[ModelSummary] = Field(None, description="Детальна статистика моделі")
    standard_errors: Dict[str, float] = Field(default_factory=dict, description="Стандартні помилки коефіцієнтів")
    t_statistics: Dict[str, float] = Field(default_factory=dict, description="t-статистики коефіцієнтів")
    p_values: Dict[str, float] = Field(default_factory=dict, description="P-значення коефіцієнтів")
    confidence_intervals: Dict[str, Tuple[float, float]] = Field(
        default_factory=dict, description="Довірчі інтервали коефіцієнтів"
    )
    created_at: datetime = Field(..., description="Дата створення моделі")
    updated_at: Optional[datetime] = Field(None, description="Дата останнього оновлення моделі")
    is_active: bool = Field(..., description="Чи активна модель")

    @field_validator("p_values")
    @classmethod
    def validate_p_values(cls, v):
        if v:
            for key, value in v.items():
                if not (0 <= value <= 1):
                    raise ValueError(f"P-value for {key} must be between 0 and 1")
        return v

    class Config:
        from_attributes = True
        json_encoders = {datetime: lambda v: v.isoformat() if v else None}


class RegressionModel(RegressionModelInDBBase):
    pass


class ModelTrainingRequest(BaseModel):
    target_variable: str = Field(..., min_length=1, max_length=100, description="Цільова змінна для прогнозування")
    feature_variables: List[str] = Field(
        ..., min_length=1, max_length=50, description="Список змінних-ознак для моделі"
    )
    marketplace_id: Optional[int] = Field(None, ge=1, description="ID майданчику для фільтрації даних")
    car_brands: Optional[List[str]] = Field(
        None,
        max_length=100,
        description="Список марок автомобілів для аналізу. Якщо не вказано, аналізуються всі марки.",
    )
    test_size: float = Field(0.2, ge=0.1, le=0.5, description="Частка даних для тестової вибірки (від 0.1 до 0.5)")
    random_state: int = Field(42, ge=0, description="Зерно для відтворюваності результатів")


class ModelTrainingResponse(BaseModel):
    success: bool = Field(..., description="Чи успішно навчена модель")
    model_id: int = Field(..., ge=1, description="ID створеної моделі")
    r_squared: float = Field(..., ge=0, le=1, description="Коефіцієнт детермінації (R²)")
    adj_r_squared: Optional[float] = Field(None, ge=0, le=1, description="Скоригований коефіцієнт детермінації")
    f_statistic: Optional[float] = Field(None, ge=0, description="F-статистика")
    f_p_value: Optional[float] = Field(None, ge=0, le=1, description="P-значення для F-статистики")
    n_observations: int = Field(..., ge=1, description="Кількість спостережень")
    coefficients: Dict[str, float] = Field(..., description="Коефіцієнти регресії для кожної ознаки")
    intercept: float = Field(..., description="Вільний член регресійного рівняння")
    standard_errors: Dict[str, float] = Field(default_factory=dict, description="Стандартні помилки коефіцієнтів")
    t_statistics: Dict[str, float] = Field(default_factory=dict, description="t-статистики коефіцієнтів")
    p_values: Dict[str, float] = Field(default_factory=dict, description="P-значення коефіцієнтів")
    confidence_intervals: Dict[str, Tuple[float, float]] = Field(
        default_factory=dict, description="Довірчі інтервали коефіцієнтів"
    )
    message: str = Field(..., min_length=1, description="Повідомлення про результат навчання")


class ModelPredictionRequest(BaseModel):
    target_variable: str = Field(..., min_length=1, max_length=100, description="Цільова змінна для прогнозування")
    features: Dict[str, Any] = Field(..., min_length=1, description="Словник ознак та їх значень для прогнозування")
    marketplace_id: Optional[int] = Field(None, ge=1, description="ID майданчику для фільтрації моделей")
    model_id: Optional[int] = Field(
        None,
        ge=1,
        description="Конкретний ID моделі для використання. Якщо не вказано, використовується найновіша модель для цільової змінної.",
    )

    @field_validator("features")
    @classmethod
    def validate_features(cls, v):
        if not v:
            raise ValueError("Features dictionary cannot be empty")
        return v
