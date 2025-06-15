from datetime import datetime
from typing import Optional
from pydantic import BaseModel


class ScrapeRequestBase(BaseModel):
    car_brand: str
    car_model: str
    min_year: Optional[int] = None
    max_year: Optional[int] = None


class ScrapeRequestResponse(ScrapeRequestBase):
    id: int
    requested_at: datetime

    class Config:
        from_attributes = True
