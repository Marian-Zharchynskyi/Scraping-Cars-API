from datetime import datetime
from typing import List
from fastapi import APIRouter, HTTPException, Query
import logging

from services.car_scraper import CarScraper
from crud.marketplaces import MarketplacesRepositoryDependency
from crud.scrape_requests import ScrapeRequestsRepositoryDependency
from crud.scraped_cars import ScrapedCarsRepositoryDependency
from schemas.scraping import (
    ScrapeCarRequest,
    ScrapeCarResponse,
    ScrapingResult,
    ScrapedCarResponse,
)
from schemas.scrape_request import ScrapeRequestResponse
from models.scrape_request import ScrapeRequest
from models.scraped_car import ScrapedCar

router = APIRouter(
    prefix="/car-scraping",
    tags=["car-scraping"],
    responses={404: {"description": "Not found"}},
)

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


@router.post("/scrape-car", response_model=ScrapeCarResponse)
async def scrape_car(
    request: ScrapeCarRequest,
    marketplaces_repo: MarketplacesRepositoryDependency,
    scrape_requests_repo: ScrapeRequestsRepositoryDependency,
    scraped_cars_repo: ScrapedCarsRepositoryDependency,
):
    try:
        # Create search params dictionary
        search_params = {
            "brand": request.car_brand,
            "model": request.car_model,
            "year_from": str(request.min_year) if request.min_year else None,
            "year_to": str(request.max_year) if request.max_year else None,
        }
        # Remove None values
        search_params = {k: v for k, v in search_params.items() if v is not None}

        # Create scrape request
        scrape_request = ScrapeRequest(
            car_brand=request.car_brand,
            car_model=request.car_model,
            min_year=request.min_year,
            max_year=request.max_year,
            requested_at=datetime.now(),
        )
        scrape_request = await scrape_requests_repo.create_scrape_request(scrape_request)

        # Get marketplaces
        if request.marketplace_ids:
            marketplaces = []
            for marketplace_id in request.marketplace_ids:
                marketplace = await marketplaces_repo.get_marketplace(marketplace_id)
                if marketplace and marketplace.is_active:
                    marketplaces.append(marketplace)
                else:
                    logger.warning(f"Marketplace {marketplace_id} not found or inactive")
        else:
            marketplaces = await marketplaces_repo.get_marketplaces(active_only=True)

        if not marketplaces:
            raise HTTPException(status_code=400, detail="No valid marketplaces found for scraping")

        scraper = CarScraper()
        results = []
        successful_scrapes = 0
        failed_scrapes = 0

        for marketplace in marketplaces:
            try:
                scraped_cars = await scraper.scrape_car(
                    marketplace=marketplace,
                    request_id=scrape_request.id,
                    search_params=search_params,
                    limit=request.limit,
                )

                for scraped_data in scraped_cars:
                    scraped_car = ScrapedCar(
                        request_id=scrape_request.id,
                        marketplace_id=marketplace.id,
                        car_title=scraped_data.car_title,
                        price=scraped_data.price,
                        currency=scraped_data.currency,
                        year=scraped_data.year,
                        mileage=scraped_data.mileage,
                        fuel=scraped_data.fuel,
                        transmission=scraped_data.transmission,
                        engine_capacity=scraped_data.engine_capacity,
                        horse_power=scraped_data.horse_power,
                        car_url=scraped_data.car_url,
                        scraped_at=scraped_data.scraped_at,
                        status=scraped_data.status,
                        error_message=scraped_data.error_message,
                    )
                    await scraped_cars_repo.create_scraped_car(scraped_car)

                    if scraped_data.status == "success":
                        successful_scrapes += 1
                    else:
                        failed_scrapes += 1

                    results.append(
                        ScrapingResult(
                            marketplace_name=marketplace.name,
                            status=scraped_data.status,
                            car_title=scraped_data.car_title,
                            price=f"{scraped_data.price} {scraped_data.currency}"
                            if scraped_data.currency
                            else str(scraped_data.price),
                            year=scraped_data.year,
                            mileage=scraped_data.mileage,
                            fuel=scraped_data.fuel,
                            transmission=scraped_data.transmission,
                            engine_capacity=scraped_data.engine_capacity,
                            horse_power=scraped_data.horse_power,
                            url=scraped_data.car_url,
                            scraped_at=scraped_data.scraped_at,
                            error_message=scraped_data.error_message,
                        )
                    )

            except Exception as e:
                failed_scrapes += 1
                results.append(
                    ScrapingResult(
                        marketplace_name=marketplace.name,
                        status="error_scraping",
                        product_title="",
                        price="",
                        url="",
                        scraped_at=datetime.now(),
                        error_message=str(e),
                    )
                )

        return ScrapeCarResponse(
            scrape_request_id=scrape_request.id,
            car_brand=request.car_brand,
            car_model=request.car_model,
            min_year=request.min_year,
            max_year=request.max_year,
            results=results,
            summary={
                "total_marketplaces_processed": len(marketplaces),
                "successful_scrapes": successful_scrapes,
                "failed_scrapes": failed_scrapes,
            },
        )

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error during car scraping operation: {str(e)}")


@router.get("/get-all-requests", response_model=List[ScrapeRequestResponse])
async def get_scrape_requests(
    scrape_requests_repo: ScrapeRequestsRepositoryDependency,
):
    return await scrape_requests_repo.get_scrape_requests()


@router.get("/get-request-by-id/{request_id}", response_model=ScrapeRequestResponse)
async def get_scrape_request(
    request_id: int,
    scrape_requests_repo: ScrapeRequestsRepositoryDependency,
):
    request = await scrape_requests_repo.get_scrape_request(request_id)
    if not request:
        raise HTTPException(status_code=404, detail="Scrape request not found")
    return request


@router.get("/get-all-cars", response_model=List[ScrapedCarResponse])
async def get_scraped_cars(
    scraped_cars_repo: ScrapedCarsRepositoryDependency,
):
    return await scraped_cars_repo.get_scraped_cars()


@router.get("/get-car-by-id/{car_id}", response_model=ScrapedCarResponse)
async def get_scraped_car(
    car_id: int,
    scraped_cars_repo: ScrapedCarsRepositoryDependency,
):
    car = await scraped_cars_repo.get_scraped_car(car_id)
    if not car:
        raise HTTPException(status_code=404, detail="Scraped car not found")
    return car


@router.get(
    "/get-cars-by-request-id/{request_id}",
    response_model=List[ScrapedCarResponse],
)
async def get_scraped_cars_by_request(
    request_id: int,
    scraped_cars_repo: ScrapedCarsRepositoryDependency,
):
    return await scraped_cars_repo.get_scraped_cars_by_request_id(request_id)


@router.get("/get-cars-by-marketplace/{marketplace_id}", response_model=List[ScrapedCarResponse])
async def get_cars_by_marketplace(
    marketplace_id: int,
    scraped_cars_repo: ScrapedCarsRepositoryDependency,
    marketplaces_repo: MarketplacesRepositoryDependency,
):
    """
    Get all cars scraped from a specific marketplace.
    """
    # Verify marketplace exists
    marketplace = await marketplaces_repo.get_marketplace(marketplace_id)
    if not marketplace:
        raise HTTPException(status_code=404, detail="Marketplace not found")
    return await scraped_cars_repo.get_cars_by_marketplace(marketplace_id)


@router.get("/search-cars", response_model=List[ScrapedCarResponse])
async def search_cars_by_title(
    scraped_cars_repo: ScrapedCarsRepositoryDependency,
    title: str = Query(..., description="Car title to search for"),
):
    """
    Search cars by title (case-insensitive partial match).
    Example: search for "Audi A4" will return all cars with "Audi A4" in their title.
    """
    return await scraped_cars_repo.search_cars_by_title(title)


@router.get("/filter-cars/price", response_model=List[ScrapedCarResponse])
async def filter_cars_by_price(
    scraped_cars_repo: ScrapedCarsRepositoryDependency,
    min_price: float = Query(..., description="Minimum price"),
    max_price: float = Query(..., description="Maximum price"),
):
    """
    Filter cars by price range.
    Example: filter cars between $10,000 and $20,000.
    """
    return await scraped_cars_repo.filter_cars_by_price_range(min_price, max_price)


@router.get("/filter-cars/date", response_model=List[ScrapedCarResponse])
async def filter_cars_by_date(
    scraped_cars_repo: ScrapedCarsRepositoryDependency,
    start_date: datetime = Query(..., description="Start date"),
    end_date: datetime = Query(..., description="End date"),
):
    """
    Filter cars by scrape date range.
    Example: filter cars scraped between January 1, 2024 and January 31, 2024.
    """
    return await scraped_cars_repo.filter_cars_by_scrape_date(start_date, end_date)


@router.delete("/delete-request/{request_id}")
async def delete_scrape_request(
    request_id: int,
    scrape_requests_repo: ScrapeRequestsRepositoryDependency,
    scraped_cars_repo: ScrapedCarsRepositoryDependency,
):
    """
    Delete a scrape request and all associated scraped cars.
    """
    try:
        # First delete all associated cars
        await scraped_cars_repo.delete_cars_by_request_id(request_id)
        # Then delete the request
        await scrape_requests_repo.delete_scrape_request(request_id)
        return {
            "status": "success",
            "message": f"Scrape request {request_id} and associated cars deleted successfully",
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error deleting scrape request: {str(e)}")


@router.delete("/delete-car/{car_id}")
async def delete_scraped_car(
    car_id: int,
    scraped_cars_repo: ScrapedCarsRepositoryDependency,
):
    """
    Delete a specific scraped car.
    """
    try:
        await scraped_cars_repo.delete_scraped_car(car_id)
        return {
            "status": "success",
            "message": f"Scraped car {car_id} deleted successfully",
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error deleting scraped car: {str(e)}")


@router.delete("/delete-cars-by-marketplace/{marketplace_id}")
async def delete_cars_by_marketplace(
    marketplace_id: int,
    scraped_cars_repo: ScrapedCarsRepositoryDependency,
    marketplaces_repo: MarketplacesRepositoryDependency,
):
    """
    Delete all cars scraped from a specific marketplace.
    """
    try:
        # Verify marketplace exists
        marketplace = await marketplaces_repo.get_marketplace(marketplace_id)
        if not marketplace:
            raise HTTPException(status_code=404, detail="Marketplace not found")

        await scraped_cars_repo.delete_cars_by_marketplace(marketplace_id)
        return {
            "status": "success",
            "message": f"All cars from marketplace {marketplace_id} deleted successfully",
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error deleting cars: {str(e)}")
