from datetime import datetime
from sqlalchemy import Column, String, Float, DateTime, Text
try:
    from backend.database import Base
except ImportError:
    from database import Base

class ActionLog(Base):
    __tablename__ = "action_logs"

    action_id = Column(String, primary_key=True, index=True)
    alert_id = Column(String, nullable=False, index=True)
    recommendation_id = Column(String, nullable=False)
    store_id = Column(String, nullable=False, index=True)
    sku_id = Column(String, nullable=False)
    action_type = Column(String, nullable=False)  # TRANSFER, EARLIER_TRUCK, SHELF_SWAP, WAIT
    status = Column(String, nullable=False)  # APPROVED, REJECTED, EXECUTED
    manager_id = Column(String, nullable=False)
    notes = Column(Text, nullable=True)
    cost_inr = Column(Float, nullable=False, default=0.0)
    created_at = Column(DateTime, default=datetime.utcnow)
