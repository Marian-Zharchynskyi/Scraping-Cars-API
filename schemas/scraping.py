from datetime import datetime
from typing import List, Optional, Dict
from pydantic import BaseModel


class ScrapeCarRequest(BaseModel):
    """Request model for car scraping"""

    car_brand: str
    car_model: str
    min_year: Optional[int] = None
    max_year: Optional[int] = None
    marketplace_ids: Optional[List[int]] = None


class ScrapingResult(BaseModel):
    """Individual marketplace scraping result"""

    marketplace_name: str
    status: str
    car_title: str = ""
    price: str = ""
    year: Optional[int] = None
    mileage: Optional[int] = None
    fuel: Optional[str] = None
    transmission: Optional[str] = None
    engine_capacity: Optional[str] = None
    seats: Optional[str] = None
    horse_power: Optional[str] = None
    url: str = ""
    scraped_at: datetime
    error_message: Optional[str] = None


class ScrapeCarResponse(BaseModel):
    """Response model for car scraping"""

    scrape_request_id: int
    car_brand: str
    car_model: str
    results: List[ScrapingResult]
    summary: Dict[str, int]


class ScrapedCarResponse(BaseModel):
    """Response model for scraped car"""

    id: int
    request_id: int
    marketplace_id: int
    car_title: str
    price: str
    currency: Optional[str]
    year: Optional[int]
    mileage: Optional[int]
    fuel: Optional[str]
    transmission: Optional[str]
    engine_capacity: Optional[str]
    seats: Optional[str]
    horse_power: Optional[str]
    car_url: str
    scraped_at: datetime
    status: str
    error_message: Optional[str]

    class Config:
        from_attributes = True
