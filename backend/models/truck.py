from datetime import datetime
from sqlalchemy import Column, Integer, String, DateTime, ForeignKey
try:
    from backend.database import Base
except ImportError:
    from database import Base

class TruckSchedule(Base):
    __tablename__ = "truck_schedules"

    id = Column(Integer, primary_key=True, autoincrement=True)
    truck_id = Column(String, nullable=False, index=True)
    store_id = Column(String, ForeignKey("stores.store_id"), nullable=False, index=True)
    route_id = Column(String, nullable=False)
    driver_name = Column(String, nullable=False)
    scheduled_departure_time = Column(DateTime, nullable=False)
    scheduled_arrival_time = Column(DateTime, nullable=False)
    truck_capacity_units = Column(Integer, nullable=False, default=500)
    status = Column(String, nullable=False, default="SCHEDULED")
    sku_id = Column(String, ForeignKey("skus.sku_id"), nullable=False)
    allocated_quantity_units = Column(Integer, nullable=False, default=0)
