from typing import Annotated, List

from fastapi import Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from models.marketplaces import Marketplaces
from db import SessionLocalDependency


class MarketplacesRepository:
    def __init__(self, context: SessionLocalDependency):
        self.context = context

    async def get_marketplaces(self, active_only: bool = True) -> List[Marketplaces]:
        query = select(Marketplaces)
        if active_only is not None:
            query = query.where(Marketplaces.is_active == active_only)
        result = await self.context.execute(query)
        return result.scalars().all()

    async def get_marketplace(self, marketplace_id: int) -> Marketplaces:
        query = select(Marketplaces).where(Marketplaces.id == marketplace_id)
        result = await self.context.execute(query)
        return result.scalars().first()

    async def get_marketplace_by_name(self, name: str) -> Marketplaces:
        query = select(Marketplaces).where(Marketplaces.name == name)
        result = await self.context.execute(query)
        return result.scalars().first()

    async def create_marketplace(self, marketplace: Marketplaces) -> Marketplaces:
        session: AsyncSession = self.context
        session.add(marketplace)
        await session.commit()
        await session.refresh(marketplace)
        return marketplace

    async def update_marketplace(self, marketplace: Marketplaces) -> Marketplaces:
        session: AsyncSession = self.context
        await session.merge(marketplace)
        await session.commit()
        return marketplace

    async def delete_marketplace(self, marketplace_id: int) -> None:
        session: AsyncSession = self.context
        marketplace = await self.get_marketplace(marketplace_id)
        await session.delete(marketplace)
        await session.commit()


MarketplacesRepositoryDependency = Annotated[MarketplacesRepository, Depends(MarketplacesRepository)]
