from fastapi import APIRouter, Depends, Query, HTTPException
from sqlalchemy.orm import Session
from typing import Optional
try:
    from backend.database import get_db
    from backend.models.store import Store
    from backend.models.inventory import StoreInventory
except ImportError:
    from database import get_db
    from models.store import Store
    from models.inventory import StoreInventory

router = APIRouter(prefix="/api/v1/stores", tags=["Stores"])

@router.get("/{store_id}/inventory")
async def get_store_inventory(
    store_id: str,
    sku_id: Optional[str] = Query(None, description="SKU ID filter"),
    db: Session = Depends(get_db)
):
    """Retrieve store stock levels, backroom inventory, and shelf capacity."""
    store = db.query(Store).filter(Store.store_id == store_id).first()
    query = db.query(StoreInventory).filter(StoreInventory.store_id == store_id)
    if sku_id:
        query = query.filter(StoreInventory.sku_id == sku_id)
    
    inventories = query.all()
    return {
        "store_id": store_id,
        "store_name": store.store_name if store else f"Store {store_id}",
        "skus": inventories
    }
