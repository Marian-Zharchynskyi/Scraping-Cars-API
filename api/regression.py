from fastapi import APIRouter, Depends, HTTPException, status, Response
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List, Dict, Any

from db import get_db
from schemas.regression_model import (
    RegressionModel, 
    RegressionModelUpdate,
    ModelTrainingResponse,
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

router = APIRouter(
    prefix="/api/regression",
    tags=["regression"],
    responses={404: {"description": "Not found"}},
)

@router.post(
    "/train/", 
    response_model=ModelTrainingResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Train a new regression model",
    description="Train a regression model to predict target variable based on provided features"
)
async def train_model(
    request: ModelTrainingRequest,
    db: AsyncSession = Depends(get_db)
) -> Dict[str, Any]:
    """
    Train a new regression model with the provided parameters.
    
    - **target_variable**: The variable to predict (e.g., 'price')
    - **feature_variables**: List of features to use for prediction (e.g., ['year', 'mileage', 'engine_volume'])
    - **marketplace_id**: Marketplace ID to filter data
    - **car_brands**: Optional list of car brands to include
    - **test_size**: Size of the test set (default: 0.2)
    - **random_state**: Random seed for reproducibility (default: 42)
    """
    try:
        service = RegressionService(db)
        result = await service.train_model(request)
        
        if not result.get('success', False):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=result.get('error', 'Failed to train model')
            )
            
        # Include all fields from ModelTrainingResponse
        response_data = {
            'success': True,
            'model_id': result['model_id'],
            'r_squared': result['r_squared'],
            'adj_r_squared': result.get('adj_r_squared'),
            'f_statistic': result.get('f_statistic'),
            'f_p_value': result.get('f_p_value'),
            'n_observations': result.get('n_observations'),
            'coefficients': result['coefficients'],
            'intercept': result['intercept'],
            'standard_errors': result.get('standard_errors', {}),
            't_statistics': result.get('t_statistics', {}),
            'p_values': result.get('p_values', {}),
            'confidence_intervals': result.get('confidence_intervals', {}),
            'message': result.get('message', 'Model trained successfully')
        }
        return response_data
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error training model: {str(e)}"
        )

@router.post(
    "/predict/", 
    response_model=Dict[str, Any],
    summary="Make a prediction using a trained model",
    description="Predict the target variable using a pre-trained regression model"
)
async def make_prediction(
    request: ModelPredictionRequest,
    db: AsyncSession = Depends(get_db)
) -> Dict[str, Any]:
    """
    Make a prediction using a pre-trained regression model.
    
    - **target_variable**: The target variable to predict (e.g., 'price')
    - **features**: Dictionary of feature values (e.g., {'year': 2020, 'mileage': 50000, 'engine_volume': 1.8})
    - **marketplace_id**: Marketplace ID to select the model
    """
    try:
        service = RegressionService(db)
        result = await service.predict(request)
        
        if not result.get('success', False):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=result.get('error', 'Failed to make prediction')
            )
            
        return result
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error making prediction: {str(e)}"
        )

@router.get("/models/", response_model=List[RegressionModel])
async def list_models(
    skip: int = 0, 
    limit: int = 100,
    marketplace_id: int | None = None,
    is_active: bool | None = None,
    db: AsyncSession = Depends(get_db)
):
    
    return await get_models(
        db=db,
        skip=skip,
        limit=limit,
        marketplace_id=marketplace_id,
        is_active=is_active
    )

@router.get("/models/{model_id}", response_model=RegressionModel)
async def read_model(model_id: int, db: AsyncSession = Depends(get_db)):
    db_model = await get_model(db, model_id=model_id)
    if db_model is None:
        raise HTTPException(status_code=404, detail="Model not found")
    return db_model

@router.put("/models/{model_id}", response_model=RegressionModel)
async def update_existing_model(
    model_id: int, 
    model_update: RegressionModelUpdate,
    db: AsyncSession = Depends(get_db)
):
    db_model = await get_model(db, model_id=model_id)
    if db_model is None:
        raise HTTPException(status_code=404, detail="Model not found")
    return await update_model(db, db_model=db_model, model_update=model_update)

@router.delete("/models/{model_id}", status_code=status.HTTP_204_NO_CONTENT)
async def remove_model(model_id: int, db: AsyncSession = Depends(get_db)):
    db_model = await get_model(db, model_id=model_id)
    if db_model is None:
        raise HTTPException(status_code=404, detail="Model not found")
    await delete_model(db, model_id=model_id)
    return {"ok": True}

@router.get("/models/{model_id}/importance", response_model=dict)
async def get_feature_importance(model_id: int, db: AsyncSession = Depends(get_db)):
    """
    Get feature importance metrics for a trained model.
    
    - **model_id**: ID of the model to get importance for
    """
    service = RegressionService(db)
    return await service.get_model_importance(model_id)

@router.get("/models/{model_id}/coefficients-plot", response_class=Response)
async def get_coefficients_plot(
    model_id: int, 
    db: AsyncSession = Depends(get_db)
):
    """
    Generate and return a visualization of model coefficients and feature importance.
    
    - **model_id**: ID of the model to visualize
    
    Returns:
        PNG image of the coefficients plot
    """
    service = RegressionService(db)
    try:
        img_data = await service.get_coefficients_plot(model_id)
        return Response(content=img_data, media_type="image/png")
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Failed to generate coefficients plot: {str(e)}"
        )
