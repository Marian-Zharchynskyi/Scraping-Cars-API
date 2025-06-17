import re
import logging

logger = logging.getLogger(__name__)


def parse_price(price_str: str) -> tuple[str, str | None]:
    """Parse price string to extract formatted price and currency."""
    if not price_str:
        return "0", None

    price_str = price_str.strip()

    if "=" in price_str:
        price_str = price_str.split("=")[0].strip()

    currency_match = re.search(r"(\$|грн|€)", price_str)
    currency = currency_match.group(0) if currency_match else None

    price_match = re.search(r"[\d\s\.,']+", price_str)
    if not price_match:
        return "0", currency

    clean_price = price_match.group(0).replace(" ", "").replace(",", ".").replace("'", "")
    clean_price = re.sub(r"[^\d.]", "", clean_price)

    return clean_price, currency


def parse_mileage(mileage_str: str) -> int | None:
    """Parse mileage string to extract numeric value."""
    if not mileage_str:
        return None
    mileage = re.sub(r"[^\d]", "", mileage_str)
    return int(mileage) if mileage else None


def parse_year(year_str: str) -> int | None:
    """Parse year string to extract numeric value."""
    if not year_str:
        return None
    year_match = re.search(r"\b(19|20)\d{2}\b", year_str)
    return int(year_match.group(0)) if year_match else None


def parse_engine_capacity(capacity_str: str) -> str | None:
    """Parse engine capacity string."""
    if not capacity_str:
        return None
    capacity_match = re.search(r"\d+\.\d+", capacity_str)
    return capacity_match.group(0) if capacity_match else None


def parse_horse_power(power_str: str) -> str | None:
    """Parse horse power string."""
    if not power_str:
        return None

    logger.info(f"Parsing horse power from string: '{power_str}'")

    power_match = re.search(r"(\d+)\s*к\.с\.", power_str)
    if power_match:
        power = power_match.group(1)
        logger.info(f"Found horse power: {power} к.с.")
        return power

    power_match = re.search(r"(\d+)\s*к\.?с", power_str)
    if power_match:
        power = power_match.group(1)
        logger.info(f"Found horse power (alternative format): {power} к.с.")
        return power

    logger.warning(f"No horse power found in string: '{power_str}'")
    return None


def parse_fuel_type(fuel_str: str) -> str | None:
    """Parse fuel type string."""
    if not fuel_str:
        return None

    logger.info(f"Parsing fuel type from string: '{fuel_str}'")

    fuel_types = {"бензин": "Бензин", "дизель": "Дизель", "газ": "Газ", "електро": "Електро", "гібрид": "Гібрид"}

    fuel_str_lower = fuel_str.lower()

    for fuel_key, fuel_value in fuel_types.items():
        if fuel_key in fuel_str_lower:
            logger.info(f"Found fuel type: {fuel_value}")
            return fuel_value

    logger.warning(f"No fuel type found in string: '{fuel_str}'")
    return None
