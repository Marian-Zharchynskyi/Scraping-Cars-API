from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from typing import Optional, Sequence
from models.regression_model import RegressionModel as DBRegressionModel
from schemas.regression_model import RegressionModelCreate, RegressionModelUpdate

async def get_model(db: AsyncSession, model_id: int) -> Optional[DBRegressionModel]:
    result = await db.execute(
        select(DBRegressionModel).where(DBRegressionModel.id == model_id)
    )
    return result.scalars().first()

async def get_models(
    db: AsyncSession, 
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
    result = await db.execute(query)
    return result.scalars().all()

async def create_model(db: AsyncSession, model: RegressionModelCreate) -> DBRegressionModel:
    db_model = DBRegressionModel(**model.model_dump())
    db.add(db_model)
    await db.commit()
    await db.refresh(db_model)
    return db_model

async def update_model(
    db: AsyncSession, 
    db_model: DBRegressionModel, 
    model_update: RegressionModelUpdate
) -> DBRegressionModel:
    update_data = model_update.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(db_model, field, value)
    
    db.add(db_model)
    await db.commit()
    await db.refresh(db_model)
    return db_model

async def delete_model(db: AsyncSession, model_id: int) -> Optional[DBRegressionModel]:
    db_model = await get_model(db, model_id)
    if db_model:
        await db.delete(db_model)
        await db.commit()
    return db_model

async def get_active_model(
    db: AsyncSession, 
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
    
    result = await db.execute(query)
    return result.scalars().first()
