from datetime import datetime
from pydantic import BaseModel


class MarketplaceBase(BaseModel):
    name: str
    base_search_url: str
    car_selector: str
    title_selector: str
    price_selector: str
    year_selector: str
    mileage_selector: str
    fuel_selector: str
    transmission_selector: str
    engine_capacity_selector: str
    seats_selector: str
    horse_power_selector: str
    link_selector: str
    is_active: bool = True


class MarketplaceUpdate(BaseModel):
    name: str | None = None
    base_search_url: str | None = None
    car_selector: str | None = None
    title_selector: str | None = None
    price_selector: str | None = None
    year_selector: str | None = None
    mileage_selector: str | None = None
    fuel_selector: str | None = None
    transmission_selector: str | None = None
    engine_capacity_selector: str | None = None
    seats_selector: str | None = None
    horse_power_selector: str | None = None
    link_selector: str | None = None
    is_active: bool | None = None


class MarketplaceResponse(MarketplaceBase):
    id: int
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True
