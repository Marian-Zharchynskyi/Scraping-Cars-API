from typing import Optional, Sequence
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from fastapi import Depends
from models.regression_model import RegressionModel as DBRegressionModel
from schemas.regression_model import RegressionModelCreate, RegressionModelUpdate
from db import get_db


class RegressionModelRepository:
    """Repository for handling database operations for RegressionModel."""
    
    def __init__(self, db: AsyncSession):
        self.db = db
    
    async def get_model(self, model_id: int) -> Optional[DBRegressionModel]:
        """Get a single regression model by ID."""
        result = await self.db.execute(
            select(DBRegressionModel).where(DBRegressionModel.id == model_id)
        )
        return result.scalars().first()
    
    async def get_models(
        self,
        skip: int = 0,
        limit: int = 100,
        marketplace_id: Optional[int] = None,
        is_active: Optional[bool] = None
    ) -> Sequence[DBRegressionModel]:
        """Get multiple regression models with optional filtering."""
        query = select(DBRegressionModel)
        
        if marketplace_id is not None:
            query = query.where(DBRegressionModel.marketplace_id == marketplace_id)
        if is_active is not None:
            query = query.where(DBRegressionModel.is_active.is_(is_active))
        
        query = query.offset(skip).limit(limit)
        result = await self.db.execute(query)
        return result.scalars().all()
    
    async def create_model(self, model: RegressionModelCreate) -> DBRegressionModel:
        """Create a new regression model."""
        db_model = DBRegressionModel(**model.model_dump())
        self.db.add(db_model)
        await self.db.commit()
        await self.db.refresh(db_model)
        return db_model
    
    async def update_model(
        self,
        model_id: int,
        model_update: RegressionModelUpdate
    ) -> Optional[DBRegressionModel]:
        """Update an existing regression model."""
        db_model = await self.get_model(model_id)
        if not db_model:
            return None
            
        update_data = model_update.model_dump(exclude_unset=True)
        for field, value in update_data.items():
            setattr(db_model, field, value)
        
        self.db.add(db_model)
        await self.db.commit()
        await self.db.refresh(db_model)
        return db_model
    
    async def delete_model(self, model_id: int) -> bool:
        """Delete a regression model."""
        db_model = await self.get_model(model_id)
        if db_model:
            await self.db.delete(db_model)
            await self.db.commit()
            return True
        return False
    
    async def get_active_model(
        self,
        target_variable: str,
        marketplace_id: Optional[int] = None
    ) -> Optional[DBRegressionModel]:
        """Get the active model for a target variable and optional marketplace."""
        query = select(DBRegressionModel).where(
            DBRegressionModel.target_variable == target_variable,
            DBRegressionModel.is_active.is_(True)
        )
        
        if marketplace_id is not None:
            query = query.where(DBRegressionModel.marketplace_id == marketplace_id)
        else:
            query = query.where(DBRegressionModel.marketplace_id.is_(None))
        
        result = await self.db.execute(query)
        return result.scalars().first()


# Dependency function to get a repository instance
async def get_regression_model_repo(
    db: AsyncSession = Depends(get_db)
) -> RegressionModelRepository:
    """Dependency that returns a new RegressionModelRepository instance."""
    return RegressionModelRepository(db)

# Type alias for the dependency
RegressionModelRepositoryDependency = Depends(get_regression_model_repo)
