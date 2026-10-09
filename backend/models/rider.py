from datetime import datetime
from sqlalchemy import Column, Integer, String, Float, DateTime, ForeignKey
try:
    from backend.database import Base
except ImportError:
    from database import Base

class RiderAvailability(Base):
    __tablename__ = "rider_availability"

    id = Column(Integer, primary_key=True, autoincrement=True)
    timestamp = Column(DateTime, nullable=False, index=True)
    store_id = Column(String, ForeignKey("stores.store_id"), nullable=False, index=True)
    available_riders = Column(Integer, nullable=False, default=0)
    required_riders = Column(Integer, nullable=False, default=0)
    orders_per_rider_hour = Column(Float, nullable=False, default=3.5)
    rider_shortage_count = Column(Integer, nullable=False, default=0)
    shortage_severity = Column(String, nullable=False, default="NONE")
