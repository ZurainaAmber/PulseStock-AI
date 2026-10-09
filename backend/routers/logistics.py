from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from typing import Optional
from datetime import datetime

try:
    from backend.database import get_db
    from backend.models.truck import TruckSchedule
    from backend.models.rider import RiderAvailability
    from backend.models.inventory import StoreInventory
    from backend.models.store import Store
except ImportError:
    from database import get_db
    from models.truck import TruckSchedule
    from models.rider import RiderAvailability
    from models.inventory import StoreInventory
    from models.store import Store

router = APIRouter(prefix="/api/v1/logistics", tags=["Logistics"])

@router.get("/trucks")
async def get_truck_schedules(
    store_id: str = Query(..., description="Target store ID"),
    db: Session = Depends(get_db)
):
    """Fetch scheduled truck deliveries & expedited option for store."""
    trucks = db.query(TruckSchedule).filter(TruckSchedule.store_id == store_id).all()
    
    scheduled_deliveries = []
    expedited_option = {
        "is_available": False,
        "truck_id": None,
        "transit_duration_minutes": 0,
        "additional_expedited_cost_inr": 0.0
    }
    
    for t in trucks:
        if "EXPRESS" in t.truck_id or "EXPRESS" in t.route_id:
            expedited_option = {
                "is_available": True,
                "truck_id": t.truck_id,
                "earliest_departure_time": t.scheduled_departure_time.isoformat() if t.scheduled_departure_time else None,
                "expedited_arrival_time": t.scheduled_arrival_time.isoformat() if t.scheduled_arrival_time else None,
                "transit_duration_minutes": 25,
                "additional_expedited_cost_inr": 350.0
            }
        else:
            scheduled_deliveries.append({
                "truck_id": t.truck_id,
                "route_id": t.route_id,
                "driver_name": t.driver_name,
                "status": t.status,
                "scheduled_departure_time": t.scheduled_departure_time.isoformat() if t.scheduled_departure_time else None,
                "estimated_arrival_time": t.scheduled_arrival_time.isoformat() if t.scheduled_arrival_time else None,
                "manifest": [
                    {
                        "sku_id": t.sku_id,
                        "allocated_quantity_units": t.allocated_quantity_units
                    }
                ]
            })

    return {
        "store_id": store_id,
        "scheduled_deliveries": scheduled_deliveries,
        "expedited_option": expedited_option
    }

@router.get("/donors")
async def get_donor_stores(
    store_id: str = Query(..., description="Receiver store ID"),
    sku_id: str = Query(..., description="Required SKU ID"),
    required_units: Optional[int] = Query(50, description="Desired quantity"),
    db: Session = Depends(get_db)
):
    """Find nearby stores with surplus stock."""
    # Find candidate donor stores with available inventory for sku_id
    candidates = db.query(StoreInventory, Store)\
                   .join(Store, StoreInventory.store_id == Store.store_id)\
                   .filter(
                       StoreInventory.store_id != store_id,
                       StoreInventory.sku_id == sku_id,
                       StoreInventory.total_stock_units > StoreInventory.safety_stock_threshold_units
                   ).all()
                   
    donor_stores = []
    for inv, store in candidates:
        surplus = inv.total_stock_units - inv.safety_stock_threshold_units
        dist = store.stadium_proximity_km if store.stadium_proximity_km else 3.5
        eta = int(15 + dist * 3)
        cost = round(100.0 + dist * 15.0, 2)
        score = round(max(0.1, 1.0 - (dist / 20.0)), 2)
        
        donor_stores.append({
            "donor_store_id": store.store_id,
            "donor_store_name": store.store_name,
            "distance_km": dist,
            "current_stock_units": inv.total_stock_units,
            "surplus_units": surplus,
            "transfer_eta_minutes": eta,
            "estimated_transfer_cost_inr": cost,
            "feasibility_score": score
        })

    return {
        "target_store_id": store_id,
        "sku_id": sku_id,
        "donor_stores": donor_stores
    }

@router.get("/riders")
async def get_rider_availability(
    store_id: str = Query(..., description="Target store ID"),
    db: Session = Depends(get_db)
):
    """Get hyper-local rider fleet availability and shortage status."""
    # Query active rider availability record for store_id (prioritizing active shortage periods)
    rider_rec = db.query(RiderAvailability)\
                  .filter(RiderAvailability.store_id == store_id, RiderAvailability.rider_shortage_count > 0)\
                  .order_by(RiderAvailability.timestamp.desc())\
                  .first()

    if not rider_rec:
        rider_rec = db.query(RiderAvailability)\
                      .filter(RiderAvailability.store_id == store_id)\
                      .order_by(RiderAvailability.timestamp.desc())\
                      .first()
                  
    if not rider_rec:
        return {
            "store_id": store_id,
            "active_riders": 6,
            "required_riders_for_demand": 4,
            "rider_shortage_count": 0,
            "shortage_severity": "NONE",
            "rider_surge_multiplier": 1.0,
            "transfer_rider_available": True,
            "assigned_rider_id": "RIDER_DEV_01"
        }

    return {
        "store_id": store_id,
        "active_riders": rider_rec.available_riders,
        "required_riders_for_demand": rider_rec.required_riders,
        "rider_shortage_count": rider_rec.rider_shortage_count,
        "shortage_severity": rider_rec.shortage_severity,
        "rider_surge_multiplier": 1.35 if rider_rec.rider_shortage_count > 0 else 1.0,
        "transfer_rider_available": rider_rec.available_riders > 0,
        "assigned_rider_id": f"RIDER_{store_id}_01" if rider_rec.available_riders > 0 else None
    }

