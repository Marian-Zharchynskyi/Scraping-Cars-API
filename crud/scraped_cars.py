from typing import Annotated, List
from datetime import datetime

from fastapi import Depends
from sqlalchemy import select, asc, and_, between, cast, Float
from sqlalchemy.ext.asyncio import AsyncSession

from models.scraped_car import ScrapedCar
from db import SessionLocalDependency


class ScrapedCarsRepository:
    def __init__(self, context: SessionLocalDependency):
        self.context = context

    async def get_scraped_cars(self) -> List[ScrapedCar]:
        query = select(ScrapedCar)
        result = await self.context.execute(query)
        return result.scalars().all()

    async def get_scraped_cars_by_request_id(self, request_id: int) -> List[ScrapedCar]:
        query = select(ScrapedCar).where(ScrapedCar.request_id == request_id).order_by(asc(ScrapedCar.scraped_at))
        result = await self.context.execute(query)
        return result.scalars().all()

    async def get_scraped_car(self, car_id: int) -> ScrapedCar:
        query = select(ScrapedCar).where(ScrapedCar.id == car_id)
        result = await self.context.execute(query)
        return result.scalars().first()

    async def create_scraped_car(self, car: ScrapedCar) -> ScrapedCar:
        session: AsyncSession = self.context
        session.add(car)
        await session.commit()
        await session.refresh(car)
        return car

    async def get_cars_by_marketplace(self, marketplace_id: int) -> List[ScrapedCar]:
        """Get all cars scraped from a specific marketplace."""
        query = (
            select(ScrapedCar).where(ScrapedCar.marketplace_id == marketplace_id).order_by(asc(ScrapedCar.scraped_at))
        )
        result = await self.context.execute(query)
        return result.scalars().all()

    async def search_cars_by_title(self, title: str) -> List[ScrapedCar]:
        """Search cars by title (case-insensitive partial match)."""
        query = select(ScrapedCar).where(ScrapedCar.car_title.ilike(f"%{title}%")).order_by(asc(ScrapedCar.scraped_at))
        result = await self.context.execute(query)
        return result.scalars().all()

    async def filter_cars_by_price_range(self, min_price: float, max_price: float) -> List[ScrapedCar]:
        """Filter cars by price range."""
        query = (
            select(ScrapedCar)
            .where(and_(cast(ScrapedCar.price, Float) >= min_price, cast(ScrapedCar.price, Float) <= max_price))
            .order_by(asc(ScrapedCar.scraped_at))
        )
        result = await self.context.execute(query)
        return result.scalars().all()

    async def filter_cars_by_scrape_date(self, start_date: datetime, end_date: datetime) -> List[ScrapedCar]:
        """Filter cars by scrape date range."""
        query = (
            select(ScrapedCar)
            .where(between(ScrapedCar.scraped_at, start_date, end_date))
            .order_by(asc(ScrapedCar.scraped_at))
        )
        result = await self.context.execute(query)
        return result.scalars().all()

    async def filter_cars_by_multiple_criteria(
        self,
        marketplace_id: int | None = None,
        title: str | None = None,
        min_price: float | None = None,
        max_price: float | None = None,
        start_date: datetime | None = None,
        end_date: datetime | None = None,
    ) -> List[ScrapedCar]:
        """Filter cars by multiple criteria."""
        conditions = []

        if marketplace_id:
            conditions.append(ScrapedCar.marketplace_id == marketplace_id)
        if title:
            conditions.append(ScrapedCar.car_title.ilike(f"%{title}%"))
        if min_price is not None:
            conditions.append(cast(ScrapedCar.price, Float) >= min_price)
        if max_price is not None:
            conditions.append(cast(ScrapedCar.price, Float) <= max_price)
        if start_date:
            conditions.append(ScrapedCar.scraped_at >= start_date)
        if end_date:
            conditions.append(ScrapedCar.scraped_at <= end_date)

        query = select(ScrapedCar).where(and_(*conditions)).order_by(asc(ScrapedCar.scraped_at))
        result = await self.context.execute(query)
        return result.scalars().all()


ScrapedCarsRepositoryDependency = Annotated[ScrapedCarsRepository, Depends(ScrapedCarsRepository)]
