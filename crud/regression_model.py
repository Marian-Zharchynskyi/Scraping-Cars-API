from sqlalchemy.orm import Session
from typing import List, Optional
from models.regression_model import RegressionModel as DBRegressionModel
from schemas.regression_model import RegressionModelCreate, RegressionModelUpdate

def get_model(db: Session, model_id: int) -> Optional[DBRegressionModel]:
    
    return db.query(DBRegressionModel).filter(DBRegressionModel.id == model_id).first()

def get_models(
    db: Session, 
    skip: int = 0, 
    limit: int = 100,
    marketplace_id: Optional[int] = None,
    is_active: Optional[bool] = None
) -> List[DBRegressionModel]:
    
    query = db.query(DBRegressionModel)
    
    if marketplace_id is not None:
        query = query.filter(DBRegressionModel.marketplace_id == marketplace_id)
    if is_active is not None:
        query = query.filter(DBRegressionModel.is_active == is_active)
        
    return query.offset(skip).limit(limit).all()

def create_model(db: Session, model: RegressionModelCreate) -> DBRegressionModel:
    
    db_model = DBRegressionModel(**model.model_dump())
    db.add(db_model)
    db.commit()
    db.refresh(db_model)
    return db_model

def update_model(
    db: Session, 
    db_model: DBRegressionModel, 
    model_update: RegressionModelUpdate
) -> DBRegressionModel:
    
    update_data = model_update.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(db_model, field, value)
    
    db.add(db_model)
    db.commit()
    db.refresh(db_model)
    return db_model

def delete_model(db: Session, model_id: int) -> Optional[DBRegressionModel]:
    
    db_model = get_model(db, model_id)
    if db_model:
        db.delete(db_model)
        db.commit()
    return db_model

def get_active_model(
    db: Session, 
    target_variable: str, 
    marketplace_id: Optional[int] = None
) -> Optional[DBRegressionModel]:
    
    query = db.query(DBRegressionModel).filter(
        DBRegressionModel.target_variable == target_variable,
        DBRegressionModel.is_active == True
    )
    
    if marketplace_id is not None:
        query = query.filter(DBRegressionModel.marketplace_id == marketplace_id)
    else:
        query = query.filter(DBRegressionModel.marketplace_id.is_(None))
        
    return query.first()
