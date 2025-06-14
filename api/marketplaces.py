from typing import List, Optional
from fastapi import APIRouter, HTTPException

from crud.marketplaces import MarketplacesRepositoryDependency
from schemas.marketplaces import MarketplaceBase, MarketplaceResponse, MarketplaceUpdate
from models.marketplaces import Marketplaces

router = APIRouter(
    prefix="/marketplaces",
    tags=["marketplaces"],
    responses={404: {"description": "Not found"}},
)


@router.get("/get-all", response_model=List[MarketplaceResponse])
async def get_marketplaces(repo: MarketplacesRepositoryDependency, active_only: Optional[bool] = True):
    """
    Get all marketplaces.
    """
    try:
        marketplaces = await repo.get_marketplaces(active_only)
        if not marketplaces:
            raise HTTPException(status_code=404, detail="No marketplaces found")
        return marketplaces
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error retrieving marketplaces: {str(e)}")


@router.get("/get-by-id/{marketplace_id}", response_model=MarketplaceResponse)
async def get_marketplace(marketplace_id: int, repo: MarketplacesRepositoryDependency):
    try:
        marketplace = await repo.get_marketplace(marketplace_id)
        if not marketplace:
            raise HTTPException(
                status_code=404,
                detail=f"Marketplace with ID {marketplace_id} not found",
            )
        return marketplace
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error retrieving marketplace: {str(e)}")


@router.post("/create", response_model=MarketplaceResponse)
async def create_marketplace(marketplace: MarketplaceBase, repo: MarketplacesRepositoryDependency):
    try:
        existing = await repo.get_marketplace_by_name(marketplace.name)
        if existing:
            raise HTTPException(
                status_code=400,
                detail=f"Marketplace with name '{marketplace.name}' already exists",
            )

        new_marketplace = Marketplaces(**marketplace.model_dump())
        created_marketplace = await repo.create_marketplace(new_marketplace)

        return created_marketplace
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error creating marketplace: {str(e)}")


@router.patch("/update/{marketplace_id}", response_model=MarketplaceResponse)
async def update_marketplace(
    marketplace_id: int,
    marketplace_update: MarketplaceUpdate,
    repo: MarketplacesRepositoryDependency,
):
    try:
        existing = await repo.get_marketplace(marketplace_id)
        if not existing:
            raise HTTPException(
                status_code=404,
                detail=f"Marketplace with ID {marketplace_id} not found",
            )

        if marketplace_update.name and marketplace_update.name != existing.name:
            name_exists = await repo.get_marketplace_by_name(marketplace_update.name)
            if name_exists:
                raise HTTPException(
                    status_code=400,
                    detail=f"Marketplace with name '{marketplace_update.name}' already exists",
                )

        update_data = marketplace_update.model_dump(exclude_unset=True)
        for field, value in update_data.items():
            setattr(existing, field, value)

        updated_marketplace = await repo.update_marketplace(existing)

        refreshed_marketplace = await repo.get_marketplace(marketplace_id)
        if not refreshed_marketplace:
            raise HTTPException(
                status_code=404,
                detail="Updated marketplace not found",
            )

        return refreshed_marketplace
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error updating marketplace: {str(e)}")


@router.delete("/delete/{marketplace_id}")
async def delete_marketplace(marketplace_id: int, repo: MarketplacesRepositoryDependency):
    try:
        existing = await repo.get_marketplace(marketplace_id)
        if not existing:
            raise HTTPException(
                status_code=404,
                detail=f"Marketplace with ID {marketplace_id} not found",
            )

        await repo.delete_marketplace(marketplace_id)
        return {
            "status": "success",
            "message": f"Marketplace '{existing.name}' deleted successfully",
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error deleting marketplace: {str(e)}")
