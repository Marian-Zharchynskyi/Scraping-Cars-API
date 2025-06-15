from typing import Annotated, List

from fastapi import Depends
from sqlalchemy import select, asc
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


ScrapedCarsRepositoryDependency = Annotated[ScrapedCarsRepository, Depends(ScrapedCarsRepository)]
