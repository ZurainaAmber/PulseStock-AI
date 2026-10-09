import uuid
from datetime import datetime, timedelta
from typing import Optional, List, Dict, Any
from fastapi import APIRouter, Depends, Query, Path, HTTPException, status, Body
from sqlalchemy.orm import Session

try:
    from backend.database import get_db
    from backend.models.manager import Manager
    from backend.models.store import Store
    from backend.models.sku import SKU
    from backend.models.inventory import StoreInventory
    from backend.models.action_log import ActionLog
    from backend.models.coordination import (
        InterStoreRequest,
        RiderTransferReservation,
        StockTransferReservation,
        RequestApproval,
    )
    from backend.schemas.coordination import (
        CreateRequestSchema,
        InterStoreRequestResponse,
        ActionReasonSchema,
        StockAvailabilityResponse,
        RiderAvailabilityResponse,
        CostConfigResponse,
        CostEstimateResponse,
    )
    from backend.auth import (
        get_current_manager,
        require_store_manager,
        require_city_manager,
    )
    from backend.services.coordination_service import (
        get_cost_config,
        calculate_request_cost,
        check_stock_availability,
        check_rider_availability,
        create_notification,
        log_approval_action,
        populate_request_names,
    )
except ImportError:
    from database import get_db
    from models.manager import Manager
    from models.store import Store
    from models.sku import SKU
    from models.inventory import StoreInventory
    from models.action_log import ActionLog
    from models.coordination import (
        InterStoreRequest,
        RiderTransferReservation,
        StockTransferReservation,
        RequestApproval,
    )
    from schemas.coordination import (
        CreateRequestSchema,
        InterStoreRequestResponse,
        ActionReasonSchema,
        StockAvailabilityResponse,
        RiderAvailabilityResponse,
        CostConfigResponse,
        CostEstimateResponse,
    )
    from auth import (
        get_current_manager,
        require_store_manager,
        require_city_manager,
    )
    from services.coordination_service import (
        get_cost_config,
        calculate_request_cost,
        check_stock_availability,
        check_rider_availability,
        create_notification,
        log_approval_action,
        populate_request_names,
    )

router = APIRouter(prefix="/api/v1/coordination", tags=["Inter-Store Coordination"])

# ----------------------------------------------------
# Cost Configuration & Availability Endpoints
# ----------------------------------------------------

@router.get("/cost-config", response_model=CostConfigResponse)
async def get_operational_cost_config(db: Session = Depends(get_db)):
    """Retrieves operational cost parameters for transfers and dispatches."""
    return get_cost_config(db)

@router.get("/stock-availability", response_model=StockAvailabilityResponse)
async def query_stock_availability(
    store_id: str = Query(..., example="STORE_003"),
    sku_id: str = Query(..., example="SKU_COLD_DRINK_750ML"),
    required_units: int = Query(default=1, ge=1),
    db: Session = Depends(get_db)
):
    """Checks donor store inventory, reserved units, and projected surplus for stock transfers."""
    st = db.query(Store).filter(Store.store_id == store_id).first()
    if not st:
        raise HTTPException(status_code=404, detail=f"Store '{store_id}' not found.")
    sku = db.query(SKU).filter(SKU.sku_id == sku_id).first()
    if not sku:
        raise HTTPException(status_code=404, detail=f"SKU '{sku_id}' not found.")
        
    return check_stock_availability(db, store_id, sku_id, required_units)

@router.get("/rider-availability", response_model=RiderAvailabilityResponse)
async def query_rider_availability(
    store_id: str = Query(..., example="STORE_003"),
    start_time: Optional[datetime] = Query(default=None),
    end_time: Optional[datetime] = Query(default=None),
    required_riders: int = Query(default=1, ge=1),
    db: Session = Depends(get_db)
):
    """Checks donor store rider fleet availability and surplus for specified time interval."""
    st = db.query(Store).filter(Store.store_id == store_id).first()
    if not st:
        raise HTTPException(status_code=404, detail=f"Store '{store_id}' not found.")
        
    now = datetime.utcnow()
    st_time = start_time or now
    en_time = end_time or (st_time + timedelta(hours=2))
    if en_time <= st_time:
        raise HTTPException(status_code=400, detail="end_time must be greater than start_time.")
        
    return check_rider_availability(db, store_id, st_time, en_time, required_riders)

# ----------------------------------------------------
# Requests Management Endpoints
# ----------------------------------------------------

@router.get("/requests", response_model=List[InterStoreRequestResponse])
async def list_inter_store_requests(
    store_id: Optional[str] = Query(default=None, description="Filter by store ID"),
    role_filter: Optional[str] = Query(default=None, alias="role", description="REQUESTING, DONOR, or ALL"),
    status_filter: Optional[str] = Query(default=None, alias="status", description="Filter by request status"),
    request_type: Optional[str] = Query(default=None, description="STOCK_TRANSFER or RIDER_TRANSFER"),
    current_manager: Manager = Depends(get_current_manager),
    db: Session = Depends(get_db)
):
    """Lists inter-store requests filtered by store, role, status, or type."""
    query = db.query(InterStoreRequest)
    
    # Store Manager scope enforcement: if store manager, restrict to their store unless explicit store specified
    target_store = store_id
    if current_manager.role == "STORE_MANAGER":
        if not target_store:
            target_store = current_manager.store_id
        elif target_store != current_manager.store_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Store Managers can only view requests involving their assigned store."
            )

    if target_store:
        if role_filter == "REQUESTING":
            query = query.filter(InterStoreRequest.requesting_store_id == target_store)
        elif role_filter == "DONOR":
            query = query.filter(InterStoreRequest.donor_store_id == target_store)
        else:
            query = query.filter(
                (InterStoreRequest.requesting_store_id == target_store) |
                (InterStoreRequest.donor_store_id == target_store)
            )

    if status_filter:
        query = query.filter(InterStoreRequest.status == status_filter)
    if request_type:
        query = query.filter(InterStoreRequest.request_type == request_type)

    requests = query.order_by(InterStoreRequest.created_at.desc()).all()
    return [populate_request_names(db, r) for r in requests]

@router.post("/requests", response_model=InterStoreRequestResponse, status_code=status.HTTP_201_CREATED)
async def create_inter_store_request(
    payload: CreateRequestSchema,
    current_manager: Manager = Depends(require_store_manager),
    db: Session = Depends(get_db)
):
    """Creates a new inter-store stock or rider transfer request."""
    if payload.requesting_store_id == payload.donor_store_id:
        raise HTTPException(status_code=400, detail="Requesting store and donor store cannot be the same.")
        
    if current_manager.role == "STORE_MANAGER" and current_manager.store_id != payload.requesting_store_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"Store Manager '{current_manager.manager_id}' cannot create requests on behalf of store '{payload.requesting_store_id}'."
        )

    # Validate store existence
    req_st = db.query(Store).filter(Store.store_id == payload.requesting_store_id).first()
    if not req_st:
        raise HTTPException(status_code=404, detail=f"Requesting store '{payload.requesting_store_id}' not found.")
    dn_st = db.query(Store).filter(Store.store_id == payload.donor_store_id).first()
    if not dn_st:
        raise HTTPException(status_code=404, detail=f"Donor store '{payload.donor_store_id}' not found.")

    if payload.request_type == "STOCK_TRANSFER":
        if not payload.sku_id or not payload.requested_quantity:
            raise HTTPException(status_code=400, detail="STOCK_TRANSFER requires sku_id and requested_quantity.")
        sku = db.query(SKU).filter(SKU.sku_id == payload.sku_id).first()
        if not sku:
            raise HTTPException(status_code=404, detail=f"SKU '{payload.sku_id}' not found.")
            
        # Shelf capacity & receiving store check
        rcv_inv = db.query(StoreInventory).filter(
            StoreInventory.store_id == payload.requesting_store_id,
            StoreInventory.sku_id == payload.sku_id
        ).first()
        if rcv_inv:
            max_capacity = (rcv_inv.shelf_capacity_units or 40) + 500  # Shelf + backroom max check
            if payload.requested_quantity > max_capacity:
                raise HTTPException(
                    status_code=422,
                    detail=f"Requested quantity {payload.requested_quantity} exceeds receiving store shelf/backroom capacity limit ({max_capacity})."
                )

        # Donor stock availability check
        avail = check_stock_availability(db, payload.donor_store_id, payload.sku_id, payload.requested_quantity)
        if not avail["can_fulfill"]:
            raise HTTPException(
                status_code=400,
                detail=f"Donor store '{payload.donor_store_id}' has insufficient unreserved stock ({avail['available_unreserved_stock']} units available, {payload.requested_quantity} requested)."
            )

    elif payload.request_type == "RIDER_TRANSFER":
        if not payload.requested_riders_count or not payload.start_time or not payload.end_time:
            raise HTTPException(status_code=400, detail="RIDER_TRANSFER requires requested_riders_count, start_time, and end_time.")
        
        from datetime import timezone
        if payload.start_time and hasattr(payload.start_time, 'tzinfo') and payload.start_time.tzinfo:
            payload.start_time = payload.start_time.astimezone(timezone.utc).replace(tzinfo=None)
        if payload.end_time and hasattr(payload.end_time, 'tzinfo') and payload.end_time.tzinfo:
            payload.end_time = payload.end_time.astimezone(timezone.utc).replace(tzinfo=None)

        if payload.end_time <= payload.start_time:
            raise HTTPException(status_code=400, detail="end_time must be after start_time.")
            
        avail = check_rider_availability(
            db, payload.donor_store_id, payload.start_time, payload.end_time, payload.requested_riders_count
        )
        if not avail["can_fulfill"]:
            raise HTTPException(
                status_code=400,
                detail=f"Donor store '{payload.donor_store_id}' has insufficient net available riders ({avail['net_available_riders']} available, {payload.requested_riders_count} requested)."
            )
    else:
        raise HTTPException(status_code=400, detail="Invalid request_type. Must be STOCK_TRANSFER or RIDER_TRANSFER.")

    # Calculate operational cost estimate
    cost_data = calculate_request_cost(
        db=db,
        request_type=payload.request_type,
        requesting_store_id=payload.requesting_store_id,
        donor_store_id=payload.donor_store_id,
        requested_quantity=payload.requested_quantity,
        requested_riders_count=payload.requested_riders_count,
        start_time=payload.start_time,
        end_time=payload.end_time
    )

    req_id = f"REQ_{datetime.utcnow().strftime('%Y%m%d')}_{uuid.uuid4().hex[:6].upper()}"
    new_request = InterStoreRequest(
        request_id=req_id,
        request_type=payload.request_type,
        requesting_store_id=payload.requesting_store_id,
        donor_store_id=payload.donor_store_id,
        sku_id=payload.sku_id,
        requested_quantity=payload.requested_quantity,
        requested_riders_count=payload.requested_riders_count,
        start_time=payload.start_time,
        end_time=payload.end_time,
        status="REQUESTED",
        created_by_manager_id=current_manager.manager_id,
        reason=payload.reason,
        estimated_cost_inr=cost_data["total_cost"],
        estimated_net_benefit_inr=None,
        created_at=datetime.utcnow(),
        updated_at=datetime.utcnow()
    )
    db.add(new_request)

    # Log initial approval record
    log_approval_action(
        db=db,
        request_id=req_id,
        actor_manager=current_manager,
        action="CREATE",
        from_status="NONE",
        to_status="REQUESTED",
        reason=payload.reason
    )

    # Send notifications
    donor_mgr = db.query(Manager).filter(Manager.store_id == payload.donor_store_id).first()
    if donor_mgr:
        create_notification(
            db,
            donor_mgr.manager_id,
            f"New {payload.request_type} Request",
            f"Store {payload.requesting_store_id} requested {payload.requested_quantity or payload.requested_riders_count} units/riders from your store.",
            "REQUEST_CREATED",
            req_id
        )

    city_mgrs = db.query(Manager).filter(Manager.role == "CITY_MANAGER").all()
    for cm in city_mgrs:
        create_notification(
            db,
            cm.manager_id,
            f"Inter-Store Request Created: {req_id}",
            f"Store {payload.requesting_store_id} requested transfer from Store {payload.donor_store_id}.",
            "REQUEST_CREATED",
            req_id
        )

    db.commit()
    db.refresh(new_request)
    return populate_request_names(db, new_request)

@router.get("/requests/{request_id}", response_model=InterStoreRequestResponse)
async def get_inter_store_request(
    request_id: str = Path(...),
    current_manager: Manager = Depends(get_current_manager),
    db: Session = Depends(get_db)
):
    """Retrieves detailed information for a single request including history."""
    req = db.query(InterStoreRequest).filter(InterStoreRequest.request_id == request_id).first()
    if not req:
        raise HTTPException(status_code=404, detail=f"Request '{request_id}' not found.")

    if current_manager.role == "STORE_MANAGER":
        if current_manager.store_id not in (req.requesting_store_id, req.donor_store_id):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Store Managers can only view requests involving their assigned store."
            )

    return populate_request_names(db, req)

# ----------------------------------------------------
# Workflow Action Endpoints
# ----------------------------------------------------

@router.post("/requests/{request_id}/donor-accept", response_model=InterStoreRequestResponse)
async def donor_accept_request(
    request_id: str = Path(...),
    payload: ActionReasonSchema = Body(default=ActionReasonSchema()),
    current_manager: Manager = Depends(require_store_manager),
    db: Session = Depends(get_db)
):
    """Donor store manager agrees to fulfill the requested stock or rider transfer."""
    req = db.query(InterStoreRequest).filter(InterStoreRequest.request_id == request_id).first()
    if not req:
        raise HTTPException(status_code=404, detail=f"Request '{request_id}' not found.")

    # Rule: Cannot approve request on behalf of another store or approve your own request as donor
    if current_manager.role == "STORE_MANAGER":
        if current_manager.store_id != req.donor_store_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Only the manager of donor store '{req.donor_store_id}' can accept this request."
            )
        if current_manager.store_id == req.requesting_store_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Requesting store manager cannot accept their own request as donor manager."
            )

    # Idempotency check
    if req.status in ("DONOR_ACCEPTED", "PENDING_CITY_APPROVAL", "APPROVED", "SIMULATED_COMPLETED"):
        return populate_request_names(db, req)

    if req.status not in ("REQUESTED",):
        raise HTTPException(
            status_code=400,
            detail=f"Cannot accept request in status '{req.status}'. Requires status 'REQUESTED'."
        )

    # Re-validate availability under DB transaction
    if req.request_type == "STOCK_TRANSFER":
        avail = check_stock_availability(db, req.donor_store_id, req.sku_id, req.requested_quantity)
        if not avail["can_fulfill"]:
            # Auto-reject if unavailable
            req.status = "DONOR_REJECTED"
            log_approval_action(db, req.request_id, current_manager, "DONOR_REJECT", "REQUESTED", "DONOR_REJECTED", "Insufficient stock upon acceptance")
            db.commit()
            raise HTTPException(
                status_code=400,
                detail=f"Cannot accept: Donor store inventory is insufficient ({avail['available_unreserved_stock']} units available)."
            )
        # Create stock reservation
        res_id = f"RES_STK_{uuid.uuid4().hex[:8].upper()}"
        stk_res = StockTransferReservation(
            reservation_id=res_id,
            request_id=req.request_id,
            donor_store_id=req.donor_store_id,
            requesting_store_id=req.requesting_store_id,
            sku_id=req.sku_id,
            quantity=req.requested_quantity,
            status="RESERVED",
            created_at=datetime.utcnow()
        )
        db.add(stk_res)

    elif req.request_type == "RIDER_TRANSFER":
        from datetime import timezone
        r_start = req.start_time.astimezone(timezone.utc).replace(tzinfo=None) if req.start_time and hasattr(req.start_time, 'tzinfo') and req.start_time.tzinfo else req.start_time
        r_end = req.end_time.astimezone(timezone.utc).replace(tzinfo=None) if req.end_time and hasattr(req.end_time, 'tzinfo') and req.end_time.tzinfo else req.end_time

        avail = check_rider_availability(db, req.donor_store_id, r_start, r_end, req.requested_riders_count)
        if not avail["can_fulfill"]:
            req.status = "DONOR_REJECTED"
            log_approval_action(db, req.request_id, current_manager, "DONOR_REJECT", "REQUESTED", "DONOR_REJECTED", "Insufficient riders upon acceptance")
            db.commit()
            raise HTTPException(
                status_code=400,
                detail=f"Cannot accept: Donor store has overlapping rider reservations or insufficient riders ({avail['net_available_riders']} net available)."
            )
        # Create rider reservation
        res_id = f"RES_RDR_{uuid.uuid4().hex[:8].upper()}"
        rdr_res = RiderTransferReservation(
            reservation_id=res_id,
            request_id=req.request_id,
            donor_store_id=req.donor_store_id,
            requesting_store_id=req.requesting_store_id,
            riders_count=req.requested_riders_count,
            start_time=r_start,
            end_time=r_end,
            status="RESERVED",
            created_at=datetime.utcnow()
        )
        db.add(rdr_res)

    prev_status = req.status
    req.status = "PENDING_CITY_APPROVAL"
    req.updated_at = datetime.utcnow()

    log_approval_action(
        db, req.request_id, current_manager, "DONOR_ACCEPT", prev_status, "PENDING_CITY_APPROVAL", payload.reason or payload.notes
    )

    # Notifications
    create_notification(
        db,
        req.created_by_manager_id,
        "Donor Accepted Request",
        f"Donor store '{req.donor_store_id}' manager accepted request {req.request_id}. Awaiting City Ops approval.",
        "DONOR_ACCEPTED",
        req.request_id
    )

    city_mgrs = db.query(Manager).filter(Manager.role == "CITY_MANAGER").all()
    for cm in city_mgrs:
        create_notification(
            db,
            cm.manager_id,
            "Request Pending City Approval",
            f"Request {req.request_id} accepted by donor store '{req.donor_store_id}'. Ready for city manager approval.",
            "DONOR_ACCEPTED",
            req.request_id
        )

    db.commit()
    db.refresh(req)
    return populate_request_names(db, req)

@router.post("/requests/{request_id}/donor-reject", response_model=InterStoreRequestResponse)
async def donor_reject_request(
    request_id: str = Path(...),
    payload: ActionReasonSchema = Body(default=ActionReasonSchema()),
    current_manager: Manager = Depends(require_store_manager),
    db: Session = Depends(get_db)
):
    """Donor store manager declines the requested stock or rider transfer."""
    req = db.query(InterStoreRequest).filter(InterStoreRequest.request_id == request_id).first()
    if not req:
        raise HTTPException(status_code=404, detail=f"Request '{request_id}' not found.")

    if current_manager.role == "STORE_MANAGER":
        if current_manager.store_id != req.donor_store_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Only donor store '{req.donor_store_id}' manager can reject this request."
            )

    if req.status in ("DONOR_REJECTED", "CITY_REJECTED", "CANCELLED"):
        return populate_request_names(db, req)

    prev_status = req.status
    req.status = "DONOR_REJECTED"
    req.updated_at = datetime.utcnow()

    # Cancel reservations if any
    db.query(StockTransferReservation).filter(StockTransferReservation.request_id == req.request_id).update({"status": "CANCELLED"})
    db.query(RiderTransferReservation).filter(RiderTransferReservation.request_id == req.request_id).update({"status": "CANCELLED"})

    log_approval_action(
        db, req.request_id, current_manager, "DONOR_REJECT", prev_status, "DONOR_REJECTED", payload.reason or payload.notes
    )

    create_notification(
        db,
        req.created_by_manager_id,
        "Request Rejected by Donor",
        f"Donor store '{req.donor_store_id}' manager rejected request {req.request_id}. Reason: {payload.reason or 'Not specified'}.",
        "DONOR_REJECTED",
        req.request_id
    )

    db.commit()
    db.refresh(req)
    return populate_request_names(db, req)

@router.post("/requests/{request_id}/city-approve", response_model=InterStoreRequestResponse)
async def city_approve_request(
    request_id: str = Path(...),
    payload: ActionReasonSchema = Body(default=ActionReasonSchema()),
    current_manager: Manager = Depends(require_city_manager),
    db: Session = Depends(get_db)
):
    """City Operations Manager gives final authorization for inter-store movement."""
    req = db.query(InterStoreRequest).filter(InterStoreRequest.request_id == request_id).first()
    if not req:
        raise HTTPException(status_code=404, detail=f"Request '{request_id}' not found.")

    # Safe repeated approval (Idempotency)
    if req.status in ("APPROVED", "SIMULATED_COMPLETED"):
        return populate_request_names(db, req)

    if req.status not in ("DONOR_ACCEPTED", "PENDING_CITY_APPROVAL"):
        raise HTTPException(
            status_code=400,
            detail=f"Cannot approve request in status '{req.status}'. Must be accepted by donor store first ('PENDING_CITY_APPROVAL')."
        )

    # Final availability re-validation under DB transaction
    if req.request_type == "STOCK_TRANSFER":
        avail = check_stock_availability(db, req.donor_store_id, req.sku_id, req.requested_quantity)
        if not avail["can_fulfill"]:
            raise HTTPException(
                status_code=400,
                detail=f"Final approval failed: Donor stock is no longer available ({avail['available_unreserved_stock']} available)."
            )
        # Apply simulated inventory transfer
        donor_inv = db.query(StoreInventory).filter(StoreInventory.store_id == req.donor_store_id, StoreInventory.sku_id == req.sku_id).first()
        rcv_inv = db.query(StoreInventory).filter(StoreInventory.store_id == req.requesting_store_id, StoreInventory.sku_id == req.sku_id).first()
        if donor_inv:
            donor_inv.backroom_stock_units = max(0, donor_inv.backroom_stock_units - req.requested_quantity)
            donor_inv.total_stock_units = (donor_inv.shelf_stock_units or 0) + donor_inv.backroom_stock_units
        if rcv_inv:
            rcv_inv.backroom_stock_units += req.requested_quantity
            rcv_inv.total_stock_units = (rcv_inv.shelf_stock_units or 0) + rcv_inv.backroom_stock_units

        # Update reservation status to COMPLETED
        db.query(StockTransferReservation).filter(StockTransferReservation.request_id == req.request_id).update({"status": "COMPLETED"})

    elif req.request_type == "RIDER_TRANSFER":
        avail = check_rider_availability(db, req.donor_store_id, req.start_time, req.end_time, req.requested_riders_count)
        if not avail["can_fulfill"]:
            raise HTTPException(
                status_code=400,
                detail=f"Final approval failed: Donor rider availability is insufficient ({avail['net_available_riders']} net available)."
            )
        # Update reservation status to ACTIVE
        db.query(RiderTransferReservation).filter(RiderTransferReservation.request_id == req.request_id).update({"status": "ACTIVE"})

    prev_status = req.status
    req.status = "APPROVED"
    req.updated_at = datetime.utcnow()

    log_approval_action(
        db, req.request_id, current_manager, "CITY_APPROVE", prev_status, "APPROVED", payload.reason or payload.notes
    )

    # Record in audit ActionLog
    act_id = f"ACT_COORD_{datetime.utcnow().strftime('%Y%m%d%H%M%S')}_{uuid.uuid4().hex[:4].upper()}"
    act_log = ActionLog(
        action_id=act_id,
        alert_id=f"ALT_COORD_{req.request_id}",
        recommendation_id=f"REC_COORD_{req.request_id}",
        store_id=req.requesting_store_id,
        sku_id=req.sku_id or "RIDER_RESOURCE",
        action_type=req.request_type,
        status="APPROVED",
        manager_id=current_manager.manager_id,
        notes=payload.notes or f"City approved {req.request_type} from {req.donor_store_id} to {req.requesting_store_id}",
        cost_inr=req.estimated_cost_inr,
        created_at=datetime.utcnow()
    )
    db.add(act_log)

    # Notifications to both store managers
    donor_mgr = db.query(Manager).filter(Manager.store_id == req.donor_store_id).first()
    if donor_mgr:
        create_notification(
            db,
            donor_mgr.manager_id,
            "Inter-Store Transfer Approved",
            f"City Ops approved transfer {req.request_id} from your store to Store {req.requesting_store_id}.",
            "CITY_APPROVED",
            req.request_id
        )

    req_mgr = db.query(Manager).filter(Manager.store_id == req.requesting_store_id).first()
    if req_mgr:
        create_notification(
            db,
            req_mgr.manager_id,
            "Inter-Store Transfer Approved",
            f"City Ops approved transfer {req.request_id} from Store {req.donor_store_id} to your store.",
            "CITY_APPROVED",
            req.request_id
        )

    db.commit()
    db.refresh(req)
    return populate_request_names(db, req)

@router.post("/requests/{request_id}/city-reject", response_model=InterStoreRequestResponse)
async def city_reject_request(
    request_id: str = Path(...),
    payload: ActionReasonSchema = Body(default=ActionReasonSchema()),
    current_manager: Manager = Depends(require_city_manager),
    db: Session = Depends(get_db)
):
    """City Operations Manager rejects an inter-store request."""
    req = db.query(InterStoreRequest).filter(InterStoreRequest.request_id == request_id).first()
    if not req:
        raise HTTPException(status_code=404, detail=f"Request '{request_id}' not found.")

    if req.status in ("CITY_REJECTED", "CANCELLED"):
        return populate_request_names(db, req)

    prev_status = req.status
    req.status = "CITY_REJECTED"
    req.updated_at = datetime.utcnow()

    # Cancel reservations
    db.query(StockTransferReservation).filter(StockTransferReservation.request_id == req.request_id).update({"status": "CANCELLED"})
    db.query(RiderTransferReservation).filter(RiderTransferReservation.request_id == req.request_id).update({"status": "CANCELLED"})

    log_approval_action(
        db, req.request_id, current_manager, "CITY_REJECT", prev_status, "CITY_REJECTED", payload.reason or payload.notes
    )

    act_id = f"ACT_REJ_{datetime.utcnow().strftime('%Y%m%d%H%M%S')}_{uuid.uuid4().hex[:4].upper()}"
    act_log = ActionLog(
        action_id=act_id,
        alert_id=f"ALT_COORD_{req.request_id}",
        recommendation_id=f"REC_COORD_{req.request_id}",
        store_id=req.requesting_store_id,
        sku_id=req.sku_id or "RIDER_RESOURCE",
        action_type=req.request_type,
        status="REJECTED",
        manager_id=current_manager.manager_id,
        notes=payload.notes or f"City rejected request: {payload.reason}",
        cost_inr=0.0,
        created_at=datetime.utcnow()
    )
    db.add(act_log)

    create_notification(
        db,
        req.created_by_manager_id,
        "Request Rejected by City Ops",
        f"City Operations rejected request {req.request_id}. Reason: {payload.reason or 'None'}.",
        "CITY_REJECTED",
        req.request_id
    )

    db.commit()
    db.refresh(req)
    return populate_request_names(db, req)

@router.post("/requests/{request_id}/cancel", response_model=InterStoreRequestResponse)
async def cancel_request(
    request_id: str = Path(...),
    payload: ActionReasonSchema = Body(default=ActionReasonSchema()),
    current_manager: Manager = Depends(require_store_manager),
    db: Session = Depends(get_db)
):
    """Cancels a pending request prior to final approval."""
    req = db.query(InterStoreRequest).filter(InterStoreRequest.request_id == request_id).first()
    if not req:
        raise HTTPException(status_code=404, detail=f"Request '{request_id}' not found.")

    if current_manager.role == "STORE_MANAGER" and current_manager.store_id != req.requesting_store_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only the requesting store manager or city manager can cancel this request."
        )

    if req.status in ("APPROVED", "SIMULATED_COMPLETED"):
        raise HTTPException(status_code=400, detail="Cannot cancel an already approved request.")

    prev_status = req.status
    req.status = "CANCELLED"
    req.updated_at = datetime.utcnow()

    db.query(StockTransferReservation).filter(StockTransferReservation.request_id == req.request_id).update({"status": "CANCELLED"})
    db.query(RiderTransferReservation).filter(RiderTransferReservation.request_id == req.request_id).update({"status": "CANCELLED"})

    log_approval_action(
        db, req.request_id, current_manager, "CANCEL", prev_status, "CANCELLED", payload.reason or payload.notes
    )

    db.commit()
    db.refresh(req)
    return populate_request_names(db, req)

@router.get("/requests/{request_id}/cost-estimate", response_model=CostEstimateResponse)
async def get_request_cost_estimate(
    request_id: str = Path(...),
    db: Session = Depends(get_db)
):
    """Returns cost estimation and uncomputed financial benefit placeholder for a request."""
    req = db.query(InterStoreRequest).filter(InterStoreRequest.request_id == request_id).first()
    if not req:
        raise HTTPException(status_code=404, detail=f"Request '{request_id}' not found.")

    cost_data = calculate_request_cost(
        db=db,
        request_type=req.request_type,
        requesting_store_id=req.requesting_store_id,
        donor_store_id=req.donor_store_id,
        requested_quantity=req.requested_quantity,
        requested_riders_count=req.requested_riders_count,
        start_time=req.start_time,
        end_time=req.end_time
    )

    return CostEstimateResponse(
        request_id=req.request_id,
        request_type=req.request_type,
        estimated_cost_inr=cost_data["total_cost"],
        estimated_net_benefit_inr=None,
        financial_benefit_status="UNAVAILABLE_AWAITING_ENGINE",
        cost_breakdown=cost_data["breakdown"]
    )
