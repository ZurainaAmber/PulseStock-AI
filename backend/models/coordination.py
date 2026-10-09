from datetime import datetime
from sqlalchemy import Column, String, Integer, Float, DateTime, ForeignKey, Text
try:
    from backend.database import Base
except ImportError:
    from database import Base

class InterStoreRequest(Base):
    __tablename__ = "inter_store_requests"

    request_id = Column(String, primary_key=True, index=True)
    request_type = Column(String, nullable=False, index=True)  # STOCK_TRANSFER, RIDER_TRANSFER
    requesting_store_id = Column(String, ForeignKey("stores.store_id"), nullable=False, index=True)
    donor_store_id = Column(String, ForeignKey("stores.store_id"), nullable=False, index=True)
    sku_id = Column(String, ForeignKey("skus.sku_id"), nullable=True, index=True)
    requested_quantity = Column(Integer, nullable=True)
    requested_riders_count = Column(Integer, nullable=True)
    start_time = Column(DateTime, nullable=True)
    end_time = Column(DateTime, nullable=True)
    status = Column(String, nullable=False, index=True, default="REQUESTED")
    # REQUESTED, DONOR_ACCEPTED, DONOR_REJECTED, PENDING_CITY_APPROVAL, APPROVED, CITY_REJECTED, SIMULATED_COMPLETED, CANCELLED, EXPIRED
    created_by_manager_id = Column(String, ForeignKey("managers.manager_id"), nullable=False)
    reason = Column(Text, nullable=True)
    estimated_cost_inr = Column(Float, nullable=False, default=0.0)
    estimated_net_benefit_inr = Column(Float, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class RiderTransferReservation(Base):
    __tablename__ = "rider_transfer_reservations"

    reservation_id = Column(String, primary_key=True, index=True)
    request_id = Column(String, ForeignKey("inter_store_requests.request_id"), nullable=False, index=True)
    donor_store_id = Column(String, ForeignKey("stores.store_id"), nullable=False, index=True)
    requesting_store_id = Column(String, ForeignKey("stores.store_id"), nullable=False, index=True)
    riders_count = Column(Integer, nullable=False)
    start_time = Column(DateTime, nullable=False, index=True)
    end_time = Column(DateTime, nullable=False, index=True)
    status = Column(String, nullable=False, default="RESERVED")  # RESERVED, ACTIVE, COMPLETED, CANCELLED
    created_at = Column(DateTime, default=datetime.utcnow)


class StockTransferReservation(Base):
    __tablename__ = "stock_transfer_reservations"

    reservation_id = Column(String, primary_key=True, index=True)
    request_id = Column(String, ForeignKey("inter_store_requests.request_id"), nullable=False, index=True)
    donor_store_id = Column(String, ForeignKey("stores.store_id"), nullable=False, index=True)
    requesting_store_id = Column(String, ForeignKey("stores.store_id"), nullable=False, index=True)
    sku_id = Column(String, ForeignKey("skus.sku_id"), nullable=False, index=True)
    quantity = Column(Integer, nullable=False)
    status = Column(String, nullable=False, default="RESERVED")  # RESERVED, IN_TRANSIT, COMPLETED, CANCELLED
    created_at = Column(DateTime, default=datetime.utcnow)


class RequestApproval(Base):
    __tablename__ = "request_approvals"

    approval_id = Column(String, primary_key=True, index=True)
    request_id = Column(String, ForeignKey("inter_store_requests.request_id"), nullable=False, index=True)
    actor_manager_id = Column(String, ForeignKey("managers.manager_id"), nullable=False)
    actor_role = Column(String, nullable=False)
    action = Column(String, nullable=False)  # CREATE, DONOR_ACCEPT, DONOR_REJECT, CITY_APPROVE, CITY_REJECT, CANCEL
    from_status = Column(String, nullable=False)
    to_status = Column(String, nullable=False)
    reason = Column(Text, nullable=True)
    timestamp = Column(DateTime, default=datetime.utcnow)
