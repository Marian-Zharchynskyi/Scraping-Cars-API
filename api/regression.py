from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List, Optional

from db import get_db
from schemas.regression_model import (
    RegressionModel, 
    RegressionModelUpdate,
    ModelTrainingRequest,
    ModelPredictionRequest
)
from services.regression_service import RegressionService
from crud.regression_model import (
    get_model, 
    get_models, 
    update_model, 
    delete_model
)

router = APIRouter()

@router.post("/train/", response_model=dict, status_code=status.HTTP_201_CREATED)
def train_model(
    request: ModelTrainingRequest,
    db: Session = Depends(get_db)
):
    
    service = RegressionService(db)
    return service.train_model(request)

@router.post("/predict/", response_model=dict)
def make_prediction(
    request: ModelPredictionRequest,
    db: Session = Depends(get_db)
):
    
    service = RegressionService(db)
    return service.predict(request)

@router.get("/models/", response_model=List[RegressionModel])
def list_models(
    skip: int = 0, 
    limit: int = 100,
    marketplace_id: Optional[int] = None,
    is_active: Optional[bool] = None,
    db: Session = Depends(get_db)
):
    
    return get_models(
        db, 
        skip=skip, 
        limit=limit, 
        marketplace_id=marketplace_id,
        is_active=is_active
    )

@router.get("/models/{model_id}", response_model=RegressionModel)
def read_model(model_id: int, db: Session = Depends(get_db)):
    
    db_model = get_model(db, model_id=model_id)
    if db_model is None:
        raise HTTPException(status_code=404, detail="Модель не знайдена")
    return db_model

@router.put("/models/{model_id}", response_model=RegressionModel)
def update_existing_model(
    model_id: int, 
    model_update: RegressionModelUpdate,
    db: Session = Depends(get_db)
):
    
    db_model = get_model(db, model_id=model_id)
    if db_model is None:
        raise HTTPException(status_code=404, detail="Модель не знайдена")
    return update_model(db, db_model=db_model, model_update=model_update)

@router.delete("/models/{model_id}", status_code=status.HTTP_204_NO_CONTENT)
def remove_model(model_id: int, db: Session = Depends(get_db)):
    
    db_model = get_model(db, model_id=model_id)
    if db_model is None:
        raise HTTPException(status_code=404, detail="Модель не знайдена")
    delete_model(db, model_id=model_id)
    return {"ok": True}

@router.get("/models/{model_id}/importance", response_model=dict)
def get_feature_importance(model_id: int, db: Session = Depends(get_db)):
    
    service = RegressionService(db)
    return service.get_model_importance(model_id)
