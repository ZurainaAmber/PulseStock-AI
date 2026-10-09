from pydantic import BaseModel, Field
from typing import Optional, Dict, Any, List
from datetime import datetime

class CreateRequestSchema(BaseModel):
    request_type: str = Field(..., example="STOCK_TRANSFER", description="STOCK_TRANSFER or RIDER_TRANSFER")
    requesting_store_id: str = Field(..., example="STORE_007")
    donor_store_id: str = Field(..., example="STORE_003")
    sku_id: Optional[str] = Field(default=None, example="SKU_COLD_DRINK_750ML")
    requested_quantity: Optional[int] = Field(default=None, ge=1, example=50)
    requested_riders_count: Optional[int] = Field(default=None, ge=1, example=3)
    start_time: Optional[datetime] = Field(default=None, example="2026-10-10T18:00:00Z")
    end_time: Optional[datetime] = Field(default=None, example="2026-10-10T20:00:00Z")
    reason: Optional[str] = Field(default=None, example="Match demand surge expected")

class RequestApprovalHistorySchema(BaseModel):
    approval_id: str
    actor_manager_id: str
    actor_role: str
    action: str
    from_status: str
    to_status: str
    reason: Optional[str] = None
    timestamp: datetime

    class Config:
        from_attributes = True

class InterStoreRequestResponse(BaseModel):
    request_id: str
    request_type: str
    requesting_store_id: str
    requesting_store_name: Optional[str] = None
    donor_store_id: str
    donor_store_name: Optional[str] = None
    sku_id: Optional[str] = None
    sku_name: Optional[str] = None
    requested_quantity: Optional[int] = None
    requested_riders_count: Optional[int] = None
    start_time: Optional[datetime] = None
    end_time: Optional[datetime] = None
    status: str
    created_by_manager_id: str
    reason: Optional[str] = None
    estimated_cost_inr: float
    estimated_net_benefit_inr: Optional[float] = None
    financial_benefit_status: str = "UNAVAILABLE_AWAITING_ENGINE"
    created_at: datetime
    updated_at: datetime
    history: List[RequestApprovalHistorySchema] = Field(default_factory=list)

    class Config:
        from_attributes = True

class ActionReasonSchema(BaseModel):
    reason: Optional[str] = Field(default=None, example="Accepting surplus request")
    notes: Optional[str] = Field(default=None, example="Manager notes")

class StockAvailabilityResponse(BaseModel):
    store_id: str
    sku_id: str
    sku_name: Optional[str] = None
    shelf_stock_units: int
    backroom_stock_units: int
    current_total_stock: int
    reserved_stock: int
    available_unreserved_stock: int
    safety_stock_threshold: int
    donor_surplus: int
    can_fulfill: bool
    is_safe_surplus: bool

class RiderAvailabilityResponse(BaseModel):
    store_id: str
    start_time: datetime
    end_time: datetime
    total_riders: int
    required_riders: int
    reserved_riders: int
    net_available_riders: int
    safe_surplus_riders: int
    can_fulfill: bool
    is_safe_surplus: bool

class CostConfigResponse(BaseModel):
    base_transport_cost_per_trip: float
    var_transport_cost_per_km: float
    loading_unloading_cost: float
    shelf_swap_labor_cost: float
    additional_rider_cost_per_hour: float
    rider_relocation_cost: float
    extra_truck_dispatch_cost: float
    updated_at: datetime

    class Config:
        from_attributes = True

class CostEstimateResponse(BaseModel):
    request_id: Optional[str] = None
    request_type: str
    estimated_cost_inr: float
    estimated_net_benefit_inr: Optional[float] = None
    financial_benefit_status: str = "UNAVAILABLE_AWAITING_ENGINE"
    cost_breakdown: Dict[str, float]
