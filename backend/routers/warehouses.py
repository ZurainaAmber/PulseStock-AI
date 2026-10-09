from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from datetime import datetime
try:
    from backend.database import get_db
    from backend.models.warehouse import WarehouseStock
except ImportError:
    from database import get_db
    from models.warehouse import WarehouseStock

router = APIRouter(prefix="/api/v1/warehouses", tags=["Warehouses"])

@router.get("/availability")
async def get_warehouse_availability(
    sku_id: str = Query(..., description="SKU ID to check availability"),
    db: Session = Depends(get_db)
):
    """Fetch central warehouse stock availability and next dispatch slot."""
    wh_record = db.query(WarehouseStock).filter(WarehouseStock.sku_id == sku_id).first()
    
    if not wh_record:
        return {
            "warehouse_id": "WH_CENTRAL_01",
            "warehouse_name": "Central Distribution Hub West",
            "sku_id": sku_id,
            "available_stock_units": 0,
            "reserved_stock_units": 0,
            "free_stock_units": 0,
            "next_dispatch_window": datetime.utcnow().isoformat() + "Z",
            "standard_transit_time_minutes": 60
        }
        
    return {
        "warehouse_id": wh_record.warehouse_id,
        "warehouse_name": "Central Distribution Hub West",
        "sku_id": wh_record.sku_id,
        "available_stock_units": wh_record.available_stock_units,
        "reserved_stock_units": wh_record.reserved_stock_units,
        "free_stock_units": wh_record.free_stock_units,
        "next_dispatch_window": datetime.utcnow().isoformat() + "Z",
        "standard_transit_time_minutes": 60
    }
