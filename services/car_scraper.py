import re
import urllib.parse
from datetime import datetime
import logging
from typing import Optional, Dict
from bs4 import BeautifulSoup

from playwright.async_api import async_playwright, TimeoutError

from models.marketplaces import Marketplaces
from schemas.scraping import ScrapedCarResponse

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger(__name__)


def parse_price(price_str: str) -> tuple[str, Optional[str]]:
    """Parse price string to extract formatted price and currency."""
    if not price_str:
        return "0", None

    # Remove any extra spaces and special characters
    price_str = price_str.strip()

    # Extract currency (looking for $, грн, etc.)
    currency_match = re.search(r"(\$|грн|€)", price_str)
    currency = currency_match.group(0) if currency_match else None

    # Extract numeric price (including dots and commas)
    price_match = re.search(r"[\d\s\.,]+", price_str)
    if not price_match:
        return "0", currency

    # Clean up the price string
    clean_price = price_match.group(0).replace(" ", "").replace(",", ".")
    # Remove any non-numeric characters except dot
    clean_price = re.sub(r"[^\d.]", "", clean_price)

    return clean_price, currency


def parse_mileage(mileage_str: str) -> Optional[int]:
    """Parse mileage string to extract numeric value."""
    if not mileage_str:
        return None
    # Remove all non-digit characters
    mileage = re.sub(r"[^\d]", "", mileage_str)
    return int(mileage) if mileage else None


def parse_year(year_str: str) -> Optional[int]:
    """Parse year string to extract numeric value."""
    if not year_str:
        return None
    # Extract 4-digit year
    year_match = re.search(r"\b(19|20)\d{2}\b", year_str)
    return int(year_match.group(0)) if year_match else None


def parse_engine_capacity(capacity_str: str) -> Optional[str]:
    """Parse engine capacity string."""
    if not capacity_str:
        return None
    # Extract engine capacity (e.g., "2.0", "1.6")
    capacity_match = re.search(r"\d+\.\d+", capacity_str)
    return capacity_match.group(0) if capacity_match else None


def parse_horse_power(power_str: str) -> Optional[str]:
    """Parse horse power string."""
    if not power_str:
        return None
    # Extract horse power (e.g., "150", "200")
    power_match = re.search(r"\d+", power_str)
    return power_match.group(0) if power_match else None


def format_search_url(base_url: str, params: Dict[str, str]) -> str:
    """Format search URL with parameters."""
    # For RST format
    if "rst.ua" in base_url:
        brand = params.get("brand", "").lower()
        model = params.get("model", "").lower()
        year_from = params.get("year_from", "")
        year_to = params.get("year_to", "")

        url = f"{base_url}{brand}/{model}/"
        if year_from or year_to:
            url += "?"
            if year_from:
                url += f"year[]={year_from}"
            if year_to:
                url += f"&year[]={year_to}"
        return url

    # For other marketplaces, use query parameters
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
        self, marketplace: Marketplaces, request_id: int, search_params: Dict[str, str]
    ) -> ScrapedCarResponse:
        logger.info(f"Starting car scraping for '{search_params}' on {marketplace.name} (ID: {request_id})")

        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=False)
            context = await browser.new_context(
                user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
            )

            try:
                page = await context.new_page()
                search_url = format_search_url(marketplace.base_search_url, search_params)
                logger.info(f"Navigating to: {search_url}")

                page.set_default_timeout(30000)

                try:
                    await page.goto(search_url, wait_until="domcontentloaded", timeout=30000)

                    logger.info(f"Searching for cars with selector: {marketplace.car_selector}")
                    await page.wait_for_selector(marketplace.car_selector, timeout=30000, state="visible")

                    # Get the page content and parse it with BeautifulSoup
                    content = await page.content()
                    soup = BeautifulSoup(content, "html.parser")

                    # Find the first car card
                    car_element = soup.select_one(marketplace.car_selector)

                    if not car_element:
                        logger.warning(f"No cars found for '{search_params}'")
                        return ScrapedCarResponse(
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
                            seats=None,
                            horse_power=None,
                            car_url="",
                            status="not_found",
                            error_message=f"No cars found for search params: {search_params}",
                            scraped_at=datetime.now(),
                        )

                    # Step 1: Get car link and title from the list using BeautifulSoup
                    link_element = car_element.select_one(marketplace.link_selector)
                    title_element = car_element.select_one(marketplace.title_selector)

                    if not link_element:
                        logger.error(f"Failed to extract car link using selector: {marketplace.link_selector}")
                        raise ValueError(f"Could not find car link element for marketplace {marketplace.name}")

                    if not title_element:
                        logger.error(f"Failed to extract car title using selector: {marketplace.title_selector}")
                        raise ValueError(f"Could not find car title element for marketplace {marketplace.name}")

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

                    # Log raw values before parsing
                    logger.info(f"Raw values from page:")
                    logger.info(f"Price text: '{price_text}'")
                    logger.info(f"Year text: '{year_text}'")
                    logger.info(f"Mileage text: '{mileage_text}'")
                    logger.info(f"Fuel text: '{fuel}'")
                    logger.info(f"Transmission text: '{transmission}'")
                    logger.info(f"Engine capacity text: '{engine_capacity_text}'")
                    logger.info(f"Horse power text: '{horse_power_text}'")

                    # Extract and parse all values
                    price_str, currency = parse_price(price_text) if price_text else ("0", None)
                    year = parse_year(year_text) if year_text else None
                    mileage = parse_mileage(mileage_text) if mileage_text else None
                    engine_capacity = parse_engine_capacity(engine_capacity_text) if engine_capacity_text else None
                    horse_power = parse_horse_power(horse_power_text) if horse_power_text else None

                    # Log parsed values
                    logger.info(f"Parsed values:")
                    logger.info(f"Price: {price_str} {currency}")
                    logger.info(f"Year: {year}")
                    logger.info(f"Mileage: {mileage}")
                    logger.info(f"Fuel: {fuel}")
                    logger.info(f"Transmission: {transmission}")
                    logger.info(f"Engine capacity: {engine_capacity}")
                    logger.info(f"Horse power: {horse_power}")

                    logger.info(f"Successfully scraped: {car_title} - {price_str} {currency}")
                    return ScrapedCarResponse(
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

                except TimeoutError:
                    logger.error(f"Timeout error on {marketplace.name}")
                    return ScrapedCarResponse(
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
                        error_message="Timeout waiting for car details",
                        scraped_at=datetime.now(),
                    )

            except Exception as e:
                logger.error(f"Scraping error on {marketplace.name}: {str(e)}")
                return ScrapedCarResponse(
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
                    error_message=f"Scraping error: {str(e)}",
                    scraped_at=datetime.now(),
                )
            finally:
                await browser.close()
