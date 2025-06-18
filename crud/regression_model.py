from typing import Optional, Sequence, Annotated
from sqlalchemy.future import select
from fastapi import Depends
from models.regression_model import RegressionModel as DBRegressionModel
from schemas.regression_model import RegressionModelCreate, RegressionModelUpdate
from db import SessionLocalDependency


class RegressionModelRepository:    
    def __init__(self, db: SessionLocalDependency):
        self.db = db
    
    async def get_model(self, model_id: int) -> Optional[DBRegressionModel]:
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
        query = select(DBRegressionModel)
        
        if marketplace_id is not None:
            query = query.where(DBRegressionModel.marketplace_id == marketplace_id)
        if is_active is not None:
            query = query.where(DBRegressionModel.is_active.is_(is_active))
        
        query = query.offset(skip).limit(limit)
        result = await self.db.execute(query)
        return result.scalars().all()
    
    async def create_model(self, model: RegressionModelCreate) -> DBRegressionModel:
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


RegressionModelRepositoryDependency = Annotated[RegressionModelRepository, Depends(RegressionModelRepository)]