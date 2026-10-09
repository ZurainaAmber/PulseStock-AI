from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from typing import Optional
from datetime import datetime
try:
    from backend.database import get_db
except ImportError:
    from database import get_db

router = APIRouter(prefix="/api/v1/forecast", tags=["Forecast"])

@router.get("/hourly")
async def get_hourly_forecast(
    store_id: str = Query(..., description="Store ID (e.g. STORE_007)"),
    sku_id: str = Query(..., description="SKU ID (e.g. SKU_COLD_DRINK_750ML)"),
    hours: Optional[int] = Query(12, description="Forecast horizon in hours"),
    db: Session = Depends(get_db)
):
    """Fetch hourly baseline vs uplifted demand curve for a store and SKU."""
    return {
        "store_id": store_id,
        "sku_id": sku_id,
        "generated_at": datetime.utcnow().isoformat() + "Z",
        "forecast_intervals": []
    }
