from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Optional

from db import get_db
from schemas.export import ExportToCsvRequest
from services.export_service import ExportService
from datetime import datetime

router = APIRouter()

@router.post("/export/csv", response_class=StreamingResponse)
async def export_to_csv(
    export_request: Optional[ExportToCsvRequest] = None,
    db: AsyncSession = Depends(get_db)
):
    try:
        if export_request is None:
            export_request = ExportToCsvRequest()
            
        export_service = ExportService(db)
        csv_io = await export_service.export_to_csv(export_request)
        
        # Генеруємо ім'я файлу з поточною датою
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"cars_export_{timestamp}.csv"
        
        # Отримуємо значення з StringIO
        csv_content = csv_io.getvalue()
        
        # Повертаємо відповідь з файлом
        response = StreamingResponse(
            iter([csv_content]),
            media_type="text/csv",
            headers={
                "Content-Disposition": f"attachment; filename={filename}",
                "Content-Type": "text/csv; charset=utf-8"
            }
        )
        
        return response
        
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Помилка при експорті даних: {str(e)}")
