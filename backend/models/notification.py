from datetime import datetime
from sqlalchemy import Column, String, Integer, DateTime, ForeignKey, Text
try:
    from backend.database import Base
except ImportError:
    from database import Base

class ManagerNotification(Base):
    __tablename__ = "manager_notifications"

    notification_id = Column(String, primary_key=True, index=True)
    manager_id = Column(String, ForeignKey("managers.manager_id"), nullable=False, index=True)
    title = Column(String, nullable=False)
    message = Column(Text, nullable=False)
    type = Column(String, nullable=False)  # REQUEST_CREATED, DONOR_ACCEPTED, DONOR_REJECTED, CITY_APPROVED, CITY_REJECTED, CANCELLED
    request_id = Column(String, ForeignKey("inter_store_requests.request_id"), nullable=True, index=True)
    is_read = Column(Integer, nullable=False, default=0)
    created_at = Column(DateTime, default=datetime.utcnow, index=True)
