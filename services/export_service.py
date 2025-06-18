import csv
import io
from typing import List, Dict, Any
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy.orm import selectinload
from sqlalchemy import Integer, cast

from models.scraped_car import ScrapedCar
from schemas.export import ExportToCsvRequest

class ExportService:
    def __init__(self, db: AsyncSession):
        self.db = db
    
    def _get_default_columns(self) -> List[Dict[str, str]]:
        
        return [
            {"name": "id", "label": "ID"},
            {"name": "marketplace_name", "label": "Майданчик"},
            {"name": "car_title", "label": "Назва"},
            {"name": "price", "label": "Ціна"},
            {"name": "currency", "label": "Валюта"},
            {"name": "year", "label": "Рік"},
            {"name": "mileage", "label": "Пробіг (км)"},
            {"name": "fuel", "label": "Паливо"},
            {"name": "transmission", "label": "Коробка передач"},
            {"name": "engine_capacity", "label": "Об'єм двигуна (л)"},
            {"name": "horse_power", "label": "Потужність (к.с.)"},
            {"name": "car_url", "label": "Посилання"},
            {"name": "scraped_at", "label": "Дата збору"},
        ]
    
    def _apply_filters(self, stmt, filters: ExportToCsvRequest):
        if filters.car_model:
            stmt = stmt.where(ScrapedCar.car_title.ilike(f'%{filters.car_model}%'))
        
        if filters.min_year:
            stmt = stmt.where(ScrapedCar.year >= filters.min_year)
        
        if filters.max_year:
            stmt = stmt.where(ScrapedCar.year <= filters.max_year)
        
        if filters.min_price is not None:
            stmt = stmt.where(cast(ScrapedCar.price, Integer) >= filters.min_price)
        
        if filters.max_price is not None:
            stmt = stmt.where(cast(ScrapedCar.price, Integer) <= filters.max_price)
        
        if filters.marketplace_ids:
            stmt = stmt.where(ScrapedCar.marketplace_id.in_(filters.marketplace_ids))
            
        return stmt
    
    def _prepare_row(self, car: ScrapedCar, columns: List[Dict[str, str]]) -> Dict[str, Any]:
        row = {
            'id': car.id,
            'marketplace_name': car.marketplace.name if car.marketplace else 'Невідомо',
            'car_title': car.car_title,
            'price': car.price,
            'currency': car.currency,
            'year': car.year,
            'mileage': car.mileage,
            'fuel': car.fuel or '',
            'transmission': car.transmission or '',
            'engine_capacity': car.engine_capacity or '',
            'horse_power': car.horse_power or '',
            'car_url': car.car_url,
            'scraped_at': car.scraped_at.isoformat() if car.scraped_at else '',
        }
        
        if columns:
            return {col['name']: row.get(col['name'], '') for col in columns}
        return row
    
    async def export_to_csv(self, export_request: ExportToCsvRequest) -> io.StringIO:
        stmt = select(ScrapedCar).options(
            selectinload(ScrapedCar.marketplace)
        )
        
        stmt = self._apply_filters(stmt, export_request)
        
        stmt = stmt.order_by(ScrapedCar.id)
        
        result = await self.db.execute(stmt)
        cars = result.scalars().all()
        
        if not cars:
            raise ValueError("Не знайдено автомобілів за вказаними критеріями")
        
        column_mapping = {
            'car_title': 'car_title',
            'year': 'year',
            'price': 'price',
            'mileage': 'mileage',
            'engine_volume': 'engine_capacity',
            'transmission': 'transmission',
            'fuel_type': 'fuel'
        }
        
        if export_request.include_columns:
            columns = []
            for col in export_request.include_columns:
                if col in column_mapping:
                    columns.append({"name": column_mapping[col], "label": col})
                else:
                    columns.append({"name": col, "label": col})
        else:
            columns = self._get_default_columns()
        
        output = io.StringIO()
        writer = csv.DictWriter(
            output, 
            fieldnames=[col['name'] for col in columns],
            quoting=csv.QUOTE_NONNUMERIC
        )
        
        writer.writerow({col['name']: col['label'] for col in columns})
        
        for car in cars:
            row = self._prepare_row(car, columns)
            writer.writerow(row)
        
        output.seek(0)
        return output
