from datetime import datetime
from sqlalchemy import Column, String, Integer, Float, DateTime, ForeignKey
try:
    from backend.database import Base
except ImportError:
    from database import Base

class StockoutAlert(Base):
    __tablename__ = "stockout_alerts"

    alert_id = Column(String, primary_key=True, index=True)
    store_id = Column(String, ForeignKey("stores.store_id"), nullable=False, index=True)
    sku_id = Column(String, ForeignKey("skus.sku_id"), nullable=False, index=True)
    severity = Column(String, nullable=False)  # CRITICAL, HIGH, MEDIUM, LOW
    current_total_stock = Column(Integer, nullable=False)
    projected_hourly_demand = Column(Integer, nullable=False)
    stockout_probability = Column(Float, nullable=False)
    minutes_until_stockout = Column(Integer, nullable=True)
    estimated_stockout_time = Column(DateTime, nullable=True)
    status = Column(String, default="PENDING")  # PENDING, RESOLVED, EXPIRED
    created_at = Column(DateTime, default=datetime.utcnow)
