from typing import List, Dict, Any, Sequence, Optional
from fastapi import APIRouter, Depends, HTTPException, status, Response
from sqlalchemy.ext.asyncio import AsyncSession

from db import get_db
from schemas.regression_model import (
    RegressionModel,
    RegressionModelUpdate,
    ModelTrainingResponse,
    ModelTrainingRequest,
    ModelPredictionRequest,
)
from services.regression_service import RegressionService
from crud.regression_model import RegressionModelRepositoryDependency

router = APIRouter(
    prefix="/api/regression",
    tags=["regression"],
    responses={404: {"description": "Not found"}},
)


@router.post(
    "/train/",
    response_model=ModelTrainingResponse,
    status_code=status.HTTP_200_OK,
    summary="Train a new regression model",
    description="Train a regression model to predict target variable based on provided features",
)
async def train_model(
    request: ModelTrainingRequest,
    db: AsyncSession = Depends(get_db),
) -> Dict[str, Any]:
    try:
        service = RegressionService(db)
        result = await service.train_model(request)

        if not result.get("success", False):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST, detail=result.get("error", "Failed to train model")
            )

        response_data = {
            "success": True,
            "model_id": result["model_id"],
            "r_squared": result["r_squared"],
            "adj_r_squared": result.get("adj_r_squared"),
            "f_statistic": result.get("f_statistic"),
            "f_p_value": result.get("f_p_value"),
            "n_observations": result.get("n_observations"),
            "coefficients": result["coefficients"],
            "intercept": result["intercept"],
            "standard_errors": result.get("standard_errors", {}),
            "t_statistics": result.get("t_statistics", {}),
            "p_values": result.get("p_values", {}),
            "confidence_intervals": result.get("confidence_intervals", {}),
            "message": result.get("message", "Model trained successfully"),
        }
        return response_data
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Error training model: {str(e)}")


@router.post(
    "/predict/",
    response_model=Dict[str, Any],
    summary="Make a prediction using a trained model",
    description="Predict the target variable using a pre-trained regression model",
)
async def make_prediction(
    request: ModelPredictionRequest, repo: RegressionModelRepositoryDependency, db: AsyncSession = Depends(get_db)
) -> Dict[str, Any]:
    try:
        service = RegressionService(db)
        result = await service.predict(request)

        if not result.get("success", False):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST, detail=result.get("error", "Failed to make prediction")
            )

        return result
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Error making prediction: {str(e)}"
        )


@router.get("/models/", response_model=List[RegressionModel])
async def list_models(
    repo: RegressionModelRepositoryDependency,
    skip: int = 0,
    limit: int = 100,
    marketplace_id: Optional[int] = None,
    is_active: Optional[bool] = None,
) -> Sequence[RegressionModel]:
    try:
        models = await repo.get_models(skip=skip, limit=limit, marketplace_id=marketplace_id, is_active=is_active)
        if not models:
            raise HTTPException(status_code=404, detail="No models found")
        return models
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error retrieving models: {str(e)}")


@router.get("/models/{model_id}", response_model=RegressionModel)
async def read_model(model_id: int, repo: RegressionModelRepositoryDependency) -> RegressionModel:
    try:
        db_model = await repo.get_model(model_id=model_id)
        if db_model is None:
            raise HTTPException(status_code=404, detail=f"Model with ID {model_id} not found")
        return db_model
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error retrieving model: {str(e)}")


@router.put("/models/{model_id}", response_model=RegressionModel)
async def update_existing_model(
    model_id: int, model_update: RegressionModelUpdate, repo: RegressionModelRepositoryDependency
) -> RegressionModel:
    try:
        existing = await repo.get_model(model_id=model_id)
        if not existing:
            raise HTTPException(status_code=404, detail=f"Model with ID {model_id} not found")

        updated_model = await repo.update_model(model_id=model_id, model_update=model_update)
        if updated_model is None:
            raise HTTPException(status_code=404, detail="Updated model not found")
        return updated_model
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error updating model: {str(e)}")


@router.delete("/models/{model_id}", status_code=status.HTTP_200_OK, response_model=Dict[str, str])
async def remove_model(model_id: int, repo: RegressionModelRepositoryDependency) -> Dict[str, str]:
    try:
        existing = await repo.get_model(model_id=model_id)
        if not existing:
            raise HTTPException(status_code=404, detail=f"Model with ID {model_id} not found")

        success = await repo.delete_model(model_id=model_id)
        if not success:
            raise HTTPException(status_code=500, detail="Failed to delete model")

        return {"status": "success", "message": f"Model with ID {model_id} deleted successfully"}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error deleting model: {str(e)}")


@router.get("/models/{model_id}/importance", response_model=dict)
async def get_feature_importance(
    model_id: int, repo: RegressionModelRepositoryDependency, db: AsyncSession = Depends(get_db)
) -> Dict[str, Any]:
    try:
        existing_model = await repo.get_model(model_id=model_id)
        if not existing_model:
            raise HTTPException(status_code=404, detail=f"Model with ID {model_id} not found")

        service = RegressionService(db)
        importance = await service.get_model_importance(model_id)
        return {"success": True, "data": importance}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail=f"Failed to get feature importance: {str(e)}"
        )


@router.get("/models/{model_id}/coefficients-plot", response_class=Response)
async def get_coefficients_plot(
    model_id: int, repo: RegressionModelRepositoryDependency, db: AsyncSession = Depends(get_db)
) -> Response:
    try:
        existing_model = await repo.get_model(model_id=model_id)
        if not existing_model:
            raise HTTPException(status_code=404, detail=f"Model with ID {model_id} not found")

        service = RegressionService(db)
        img_data = await service.get_coefficients_plot(model_id)
        return Response(content=img_data, media_type="image/png")
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail=f"Failed to generate coefficients plot: {str(e)}"
        )
