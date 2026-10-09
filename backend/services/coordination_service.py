import uuid
import math
from datetime import datetime, timedelta
from typing import Optional, Dict, Any, List
from sqlalchemy.orm import Session
from sqlalchemy import or_, and_
from fastapi import HTTPException, status

try:
    from backend.models.manager import Manager
    from backend.models.store import Store
    from backend.models.sku import SKU
    from backend.models.inventory import StoreInventory
    from backend.models.rider import RiderAvailability
    from backend.models.cost_config import OperationalCostConfig
    from backend.models.notification import ManagerNotification
    from backend.models.coordination import (
        InterStoreRequest,
        RiderTransferReservation,
        StockTransferReservation,
        RequestApproval,
    )
except ImportError:
    from models.manager import Manager
    from models.store import Store
    from models.sku import SKU
    from models.inventory import StoreInventory
    from models.rider import RiderAvailability
    from models.cost_config import OperationalCostConfig
    from models.notification import ManagerNotification
    from models.coordination import (
        InterStoreRequest,
        RiderTransferReservation,
        StockTransferReservation,
        RequestApproval,
    )

def get_cost_config(db: Session) -> OperationalCostConfig:
    config = db.query(OperationalCostConfig).first()
    if not config:
        config = OperationalCostConfig()
        db.add(config)
        db.commit()
        db.refresh(config)
    return config

def calculate_store_distance(db: Session, store_a_id: str, store_b_id: str) -> float:
    store_a = db.query(Store).filter(Store.store_id == store_a_id).first()
    store_b = db.query(Store).filter(Store.store_id == store_b_id).first()
    if not store_a or not store_b:
        return 3.5
    dist = abs((store_a.stadium_proximity_km or 0.0) - (store_b.stadium_proximity_km or 0.0)) + 2.0
    return round(max(1.5, dist), 2)

def calculate_request_cost(
    db: Session,
    request_type: str,
    requesting_store_id: str,
    donor_store_id: str,
    requested_quantity: Optional[int] = None,
    requested_riders_count: Optional[int] = None,
    start_time: Optional[datetime] = None,
    end_time: Optional[datetime] = None,
) -> Dict[str, Any]:
    config = get_cost_config(db)
    
    if request_type == "STOCK_TRANSFER":
        dist_km = calculate_store_distance(db, requesting_store_id, donor_store_id)
        var_transport = round(dist_km * config.var_transport_cost_per_km, 2)
        total = round(config.base_transport_cost_per_trip + var_transport + config.loading_unloading_cost, 2)
        breakdown = {
            "base_transport_cost": config.base_transport_cost_per_trip,
            "variable_distance_cost": var_transport,
            "loading_unloading_cost": config.loading_unloading_cost,
            "distance_km": dist_km,
            "total_cost": total,
        }
        return {"total_cost": total, "breakdown": breakdown}
    
    elif request_type == "RIDER_TRANSFER":
        riders = requested_riders_count or 1
        if start_time and end_time and end_time > start_time:
            duration_hours = (end_time - start_time).total_seconds() / 3600.0
        else:
            duration_hours = 2.0
        duration_hours = max(1.0, duration_hours)
        
        hourly_cost = round(riders * duration_hours * config.additional_rider_cost_per_hour, 2)
        relocation_cost = round(riders * config.rider_relocation_cost, 2)
        total = round(hourly_cost + relocation_cost, 2)
        breakdown = {
            "rider_hourly_labor": hourly_cost,
            "relocation_cost": relocation_cost,
            "requested_riders": riders,
            "duration_hours": round(duration_hours, 2),
            "total_cost": total,
        }
        return {"total_cost": total, "breakdown": breakdown}
    else:
        return {"total_cost": 0.0, "breakdown": {"total_cost": 0.0}}

def check_stock_availability(
    db: Session,
    donor_store_id: str,
    sku_id: str,
    requested_quantity: int = 1
) -> Dict[str, Any]:
    inv = db.query(StoreInventory).filter(
        StoreInventory.store_id == donor_store_id,
        StoreInventory.sku_id == sku_id
    ).first()
    
    sku = db.query(SKU).filter(SKU.sku_id == sku_id).first()
    sku_name = sku.sku_name if sku else sku_id
    
    if not inv:
        return {
            "store_id": donor_store_id,
            "sku_id": sku_id,
            "sku_name": sku_name,
            "shelf_stock_units": 0,
            "backroom_stock_units": 0,
            "current_total_stock": 0,
            "reserved_stock": 0,
            "available_unreserved_stock": 0,
            "safety_stock_threshold": 0,
            "donor_surplus": 0,
            "can_fulfill": False,
            "is_safe_surplus": False,
        }
    
    total_stock = (inv.shelf_stock_units or 0) + (inv.backroom_stock_units or 0)
    
    # Active stock reservations for donor store
    active_res = db.query(StockTransferReservation).filter(
        StockTransferReservation.donor_store_id == donor_store_id,
        StockTransferReservation.sku_id == sku_id,
        StockTransferReservation.status.in_(["RESERVED", "IN_TRANSIT"])
    ).all()
    
    reserved_stock = sum(r.quantity for r in active_res)
    available_unreserved = max(0, total_stock - reserved_stock)
    
    projected_demand = max(10, int((inv.reorder_point_units or 50) / 2))
    safety_threshold = inv.safety_stock_threshold_units or 25
    donor_surplus = max(0, available_unreserved - safety_threshold - projected_demand)
    
    can_fulfill = available_unreserved >= requested_quantity
    is_safe_surplus = donor_surplus >= requested_quantity
    
    return {
        "store_id": donor_store_id,
        "sku_id": sku_id,
        "sku_name": sku_name,
        "shelf_stock_units": inv.shelf_stock_units or 0,
        "backroom_stock_units": inv.backroom_stock_units or 0,
        "current_total_stock": total_stock,
        "reserved_stock": reserved_stock,
        "available_unreserved_stock": available_unreserved,
        "safety_stock_threshold": safety_threshold,
        "donor_surplus": donor_surplus,
        "can_fulfill": can_fulfill,
        "is_safe_surplus": is_safe_surplus,
    }

def check_rider_availability(
    db: Session,
    donor_store_id: str,
    start_time: datetime,
    end_time: datetime,
    requested_riders_count: int = 1
) -> Dict[str, Any]:
    from datetime import timezone
    if start_time and hasattr(start_time, 'tzinfo') and start_time.tzinfo:
        start_time = start_time.astimezone(timezone.utc).replace(tzinfo=None)
    if end_time and hasattr(end_time, 'tzinfo') and end_time.tzinfo:
        end_time = end_time.astimezone(timezone.utc).replace(tzinfo=None)

    latest_rider = db.query(RiderAvailability).filter(
        RiderAvailability.store_id == donor_store_id
    ).order_by(RiderAvailability.timestamp.desc()).first()
    
    total_riders = latest_rider.available_riders if latest_rider else 5
    required_riders = latest_rider.required_riders if latest_rider else 2
    
    # Check overlapping active reservations
    overlapping_res = db.query(RiderTransferReservation).filter(
        RiderTransferReservation.donor_store_id == donor_store_id,
        RiderTransferReservation.status.in_(["RESERVED", "ACTIVE"]),
        and_(
            RiderTransferReservation.start_time < end_time,
            RiderTransferReservation.end_time > start_time
        )
    ).all()
    
    reserved_riders = sum(r.riders_count for r in overlapping_res)
    net_available = max(0, total_riders - reserved_riders)
    safe_surplus = max(0, net_available - required_riders)
    
    can_fulfill = net_available >= requested_riders_count
    is_safe_surplus = safe_surplus >= requested_riders_count
    
    return {
        "store_id": donor_store_id,
        "start_time": start_time,
        "end_time": end_time,
        "total_riders": total_riders,
        "required_riders": required_riders,
        "reserved_riders": reserved_riders,
        "net_available_riders": net_available,
        "safe_surplus_riders": safe_surplus,
        "can_fulfill": can_fulfill,
        "is_safe_surplus": is_safe_surplus,
    }

def create_notification(
    db: Session,
    manager_id: str,
    title: str,
    message: str,
    notif_type: str,
    request_id: Optional[str] = None
) -> ManagerNotification:
    notif = ManagerNotification(
        notification_id=f"NOTIF_{uuid.uuid4().hex[:10].upper()}",
        manager_id=manager_id,
        title=title,
        message=message,
        type=notif_type,
        request_id=request_id,
        is_read=0,
        created_at=datetime.utcnow()
    )
    db.add(notif)
    return notif

def log_approval_action(
    db: Session,
    request_id: str,
    actor_manager: Manager,
    action: str,
    from_status: str,
    to_status: str,
    reason: Optional[str] = None
) -> RequestApproval:
    approval = RequestApproval(
        approval_id=f"APP_{uuid.uuid4().hex[:10].upper()}",
        request_id=request_id,
        actor_manager_id=actor_manager.manager_id,
        actor_role=actor_manager.role,
        action=action,
        from_status=from_status,
        to_status=to_status,
        reason=reason,
        timestamp=datetime.utcnow()
    )
    db.add(approval)
    return approval

def populate_request_names(db: Session, req: InterStoreRequest) -> Dict[str, Any]:
    req_dict = {
        "request_id": req.request_id,
        "request_type": req.request_type,
        "requesting_store_id": req.requesting_store_id,
        "donor_store_id": req.donor_store_id,
        "sku_id": req.sku_id,
        "requested_quantity": req.requested_quantity,
        "requested_riders_count": req.requested_riders_count,
        "start_time": req.start_time,
        "end_time": req.end_time,
        "status": req.status,
        "created_by_manager_id": req.created_by_manager_id,
        "reason": req.reason,
        "estimated_cost_inr": req.estimated_cost_inr,
        "estimated_net_benefit_inr": req.estimated_net_benefit_inr,
        "financial_benefit_status": "UNAVAILABLE_AWAITING_ENGINE",
        "created_at": req.created_at,
        "updated_at": req.updated_at,
    }
    
    st_req = db.query(Store).filter(Store.store_id == req.requesting_store_id).first()
    st_dn = db.query(Store).filter(Store.store_id == req.donor_store_id).first()
    req_dict["requesting_store_name"] = st_req.store_name if st_req else req.requesting_store_id
    req_dict["donor_store_name"] = st_dn.store_name if st_dn else req.donor_store_id
    
    if req.sku_id:
        sku = db.query(SKU).filter(SKU.sku_id == req.sku_id).first()
        req_dict["sku_name"] = sku.sku_name if sku else req.sku_id
    else:
        req_dict["sku_name"] = None
        
    history = db.query(RequestApproval).filter(RequestApproval.request_id == req.request_id).order_by(RequestApproval.timestamp.asc()).all()
    req_dict["history"] = history
    return req_dict
