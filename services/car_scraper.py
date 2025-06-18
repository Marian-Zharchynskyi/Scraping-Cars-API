import urllib.parse
from datetime import datetime
import logging
from typing import Optional, Dict, List
from bs4 import BeautifulSoup

from playwright.async_api import async_playwright, TimeoutError

from models.marketplaces import Marketplaces
from schemas.scraping import ScrapedCarResponse
from services.autoria_url_generator import AutoriaUrlGenerator
from services.parsers import (
    parse_price,
    parse_mileage,
    parse_year,
    parse_engine_capacity,
    parse_horse_power,
    parse_fuel_type,
)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger(__name__)

# Initialize Autoria URL generator
autoria_generator = AutoriaUrlGenerator()


def format_search_url(base_url: str, params: Dict[str, str], page: int = 1) -> str:
    """Format search URL with parameters."""
    # For RST format
    if "rst.ua" in base_url:
        brand = params.get("brand", "").lower()
        model = params.get("model", "").lower()
        year_from = params.get("year_from", "")
        year_to = params.get("year_to", "")

        url = f"{base_url}{brand}/{model}/"
        query_params = []
        if year_from:
            query_params.append(f"year[]={year_from}")
        if year_to:
            query_params.append(f"year[]={year_to}")
        if page > 1:
            query_params.append(f"page={page}")

        if query_params:
            url += "?" + "&".join(query_params)
        return url

    # For Autoria format
    if "auto.ria.com" in base_url:
        brand_name = params.get("brand", "")
        model_name = params.get("model", "")
        year_from = params.get("year_from", "")
        year_to = params.get("year_to", "")
        size = params.get("size", "20")

        brand_id = autoria_generator.get_brand_id(brand_name)
        model_id = autoria_generator.get_model_id(model_name)

        if not brand_id or not model_id:
            logger.error(f"Could not find brand ID for '{brand_name}' or model ID for '{model_name}'")
            return base_url

        search_params = {
            "categories.main.id": 1,
            "indexName": "auto,order_auto,newauto_search",
            "brand.id[0]": brand_id,
            "model.id[0]": model_id,
            "year[0].gte": year_from,
            "year[0].lte": year_to,
            "size": size,
            "page": page,
        }

        query_string = "&".join(f"{k}={v}" for k, v in search_params.items())
        return f"{base_url}?{query_string}"

    # For other marketplaces, use query parameters
    params["page"] = str(page)
    query_params = urllib.parse.urlencode(params)
    return f"{base_url}?{query_params}"


def safe_get_text(soup: BeautifulSoup, selector: str) -> Optional[str]:
    """Safely get text from element using selector."""
    if not selector:
        return None
    element = soup.select_one(selector)
    return element.get_text(strip=True) if element else None


class CarScraper:
    def __init__(self):
        pass

    async def scrape_car(
        self, marketplace: Marketplaces, request_id: int, search_params: Dict[str, str], limit: int = 1
    ) -> List[ScrapedCarResponse]:
        logger.info(f"Starting car scraping for '{search_params}' on {marketplace.name} (ID: {request_id})")

        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=False)
            context = await browser.new_context(
                user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
            )

            try:
                page = await context.new_page()
                page.set_default_timeout(30000)

                results = []
                current_page = 1
                cars_scraped = 0

                while cars_scraped < limit:
                    search_url = format_search_url(marketplace.base_search_url, search_params, current_page)
                    logger.info(f"Navigating to page {current_page}: {search_url}")

                    try:
                        await page.goto(search_url, wait_until="domcontentloaded", timeout=30000)
                        await page.wait_for_selector(marketplace.car_selector, timeout=30000, state="visible")

                        # Get the page content and parse it with BeautifulSoup
                        content = await page.content()
                        soup = BeautifulSoup(content, "html.parser")

                        # Find all car cards on current page
                        car_elements = soup.select(marketplace.car_selector)
                        logger.info(f"Found {len(car_elements)} car cards on page {current_page}")

                        if not car_elements:
                            logger.warning(f"No more cars found on page {current_page}")
                            break

                        # Calculate how many cars we need to scrape from this page
                        remaining_cars = limit - cars_scraped
                        cars_to_scrape = min(len(car_elements), remaining_cars)

                        for car_element in car_elements[:cars_to_scrape]:
                            try:
                                # Step 1: Get car link and title from the list using BeautifulSoup
                                link_element = car_element.select_one(marketplace.link_selector)
                                title_element = car_element.select_one(marketplace.title_selector)

                                if not link_element:
                                    logger.error(
                                        f"Failed to extract car link using selector: {marketplace.link_selector}"
                                    )
                                    continue

                                if not title_element:
                                    logger.error(
                                        f"Failed to extract car title using selector: {marketplace.title_selector}"
                                    )
                                    continue

                                car_url = link_element.get("href")
                                car_title = title_element.get_text(strip=True)

                                if car_url and not car_url.startswith(("http://", "https://")):
                                    base_url = urllib.parse.urlparse(marketplace.base_search_url)
                                    car_url = f"{base_url.scheme}://{base_url.netloc}{car_url}"

                                # Step 2: Navigate to car details page
                                logger.info(f"Navigating to car details: {car_url}")
                                await page.goto(car_url, wait_until="domcontentloaded", timeout=30000)

                                # Get the page content and parse it with BeautifulSoup
                                content = await page.content()
                                soup = BeautifulSoup(content, "html.parser")

                                # Extract detailed information using BeautifulSoup
                                price_text = safe_get_text(soup, marketplace.price_selector)
                                year_text = safe_get_text(soup, marketplace.year_selector)
                                mileage_text = safe_get_text(soup, marketplace.mileage_selector)
                                fuel = safe_get_text(soup, marketplace.fuel_selector)
                                transmission = safe_get_text(soup, marketplace.transmission_selector)
                                engine_capacity_text = safe_get_text(soup, marketplace.engine_capacity_selector)
                                horse_power_text = safe_get_text(soup, marketplace.horse_power_selector)

                                # Extract and parse all values
                                price_str, currency = parse_price(price_text) if price_text else ("0", None)
                                year = parse_year(year_text) if year_text else None
                                mileage = parse_mileage(mileage_text) if mileage_text else None
                                engine_capacity = (
                                    parse_engine_capacity(engine_capacity_text) if engine_capacity_text else None
                                )
                                horse_power = parse_horse_power(horse_power_text) if horse_power_text else None
                                fuel = parse_fuel_type(fuel) if fuel else None

                                logger.info(f"Successfully scraped: {car_title} - {price_str} {currency}")
                                results.append(
                                    ScrapedCarResponse(
                                        id=0,
                                        request_id=request_id,
                                        marketplace_id=marketplace.id,
                                        car_title=car_title,
                                        price=price_str,
                                        currency=currency,
                                        year=year,
                                        mileage=mileage,
                                        fuel=fuel,
                                        transmission=transmission,
                                        engine_capacity=engine_capacity,
                                        horse_power=horse_power,
                                        car_url=car_url,
                                        status="success",
                                        error_message=None,
                                        scraped_at=datetime.now(),
                                    )
                                )
                                cars_scraped += 1

                            except Exception as e:
                                logger.error(f"Error scraping car: {str(e)}")
                                results.append(
                                    ScrapedCarResponse(
                                        id=0,
                                        request_id=request_id,
                                        marketplace_id=marketplace.id,
                                        car_title="",
                                        price="0",
                                        currency=None,
                                        year=None,
                                        mileage=None,
                                        fuel=None,
                                        transmission=None,
                                        engine_capacity=None,
                                        horse_power=None,
                                        car_url="",
                                        status="error_scraping",
                                        error_message=str(e),
                                        scraped_at=datetime.now(),
                                    )
                                )
                                cars_scraped += 1

                        # If we haven't reached the limit and there are more cars on this page,
                        # move to the next page
                        if cars_scraped < limit and len(car_elements) == int(search_params.get("size", "20")):
                            current_page += 1
                        else:
                            break

                    except TimeoutError as e:
                        logger.error(f"Timeout error while scraping page {current_page}: {str(e)}")
                        break

                if not results:
                    return [
                        ScrapedCarResponse(
                            id=0,
                            request_id=request_id,
                            marketplace_id=marketplace.id,
                            car_title="",
                            price="0",
                            currency=None,
                            year=None,
                            mileage=None,
                            fuel=None,
                            transmission=None,
                            engine_capacity=None,
                            horse_power=None,
                            car_url="",
                            status="not_found",
                            error_message=f"No cars found for search params: {search_params}",
                            scraped_at=datetime.now(),
                        )
                    ]

                return results

            except Exception as e:
                logger.error(f"Error during scraping: {str(e)}")
                return [
                    ScrapedCarResponse(
                        id=0,
                        request_id=request_id,
                        marketplace_id=marketplace.id,
                        car_title="",
                        price="0",
                        currency=None,
                        year=None,
                        mileage=None,
                        fuel=None,
                        transmission=None,
                        engine_capacity=None,
                        horse_power=None,
                        car_url="",
                        status="error",
                        error_message=str(e),
                        scraped_at=datetime.now(),
                    )
                ]
            finally:
                await browser.close()
