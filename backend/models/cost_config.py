from datetime import datetime
from sqlalchemy import Column, Integer, Float, DateTime
try:
    from backend.database import Base
except ImportError:
    from database import Base

class OperationalCostConfig(Base):
    __tablename__ = "operational_cost_config"

    id = Column(Integer, primary_key=True, autoincrement=True)
    base_transport_cost_per_trip = Column(Float, nullable=False, default=100.0)
    var_transport_cost_per_km = Column(Float, nullable=False, default=15.0)
    loading_unloading_cost = Column(Float, nullable=False, default=30.0)
    shelf_swap_labor_cost = Column(Float, nullable=False, default=50.0)
    additional_rider_cost_per_hour = Column(Float, nullable=False, default=80.0)
    rider_relocation_cost = Column(Float, nullable=False, default=40.0)
    extra_truck_dispatch_cost = Column(Float, nullable=False, default=350.0)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
