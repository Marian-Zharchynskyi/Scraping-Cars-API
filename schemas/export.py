from pydantic import BaseModel, Field
from typing import Optional, List
from datetime import datetime

class ExportToCsvRequest(BaseModel):
    
    car_model: Optional[str] = Field(
        None, 
        description="Фільтр за моделлю автомобіля (містить текстовий фрагмент)"
    )
    min_year: Optional[int] = Field(
        None, 
        ge=1900, 
        le=datetime.now().year + 1,
        description="Мінімальний рік випуску"
    )
    max_year: Optional[int] = Field(
        None, 
        ge=datetime.now().year -1, 
        le=datetime.now().year + 1,
        description="Максимальний рік випуску"
    )
    min_price: Optional[float] = Field(
        None, 
        ge=0,
        description="Мінімальна ціна"
    )
    max_price: Optional[float] = Field(
        None, 
        ge=0,
        description="Максимальна ціна"
    )
    marketplace_ids: Optional[List[int]] = Field(
        None,
        description="Список ID майданчиків для фільтрації"
    )
    include_columns: Optional[List[str]] = Field(
        None,
        description="Список колонок для експорту (якщо не вказано - експортуються всі)"
    )
