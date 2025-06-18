from typing import Annotated, List

from fastapi import Depends
from sqlalchemy import select, desc
from sqlalchemy.ext.asyncio import AsyncSession

from models.scrape_request import ScrapeRequest
from db import SessionLocalDependency

class ScrapeRequestsRepository:
    def __init__(self, context: SessionLocalDependency):
        self.context = context

    async def get_scrape_requests(self) -> List[ScrapeRequest]:
        query = select(ScrapeRequest).order_by(desc(ScrapeRequest.requested_at))
        result = await self.context.execute(query)
        return result.scalars().all()

    async def get_scrape_request(self, request_id: int) -> ScrapeRequest:
        query = select(ScrapeRequest).where(ScrapeRequest.id == request_id)
        result = await self.context.execute(query)
        return result.scalars().first()

    async def create_scrape_request(self, request: ScrapeRequest) -> ScrapeRequest:
        session: AsyncSession = self.context
        session.add(request)
        await session.commit()
        await session.refresh(request)
        return request


ScrapeRequestsRepositoryDependency = Annotated[ScrapeRequestsRepository, Depends(ScrapeRequestsRepository)]
