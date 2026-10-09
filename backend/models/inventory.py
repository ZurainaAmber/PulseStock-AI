from datetime import datetime
from sqlalchemy import Column, Integer, String, DateTime, ForeignKey
try:
    from backend.database import Base
except ImportError:
    from database import Base

class StoreInventory(Base):
    __tablename__ = "store_inventories"

    id = Column(Integer, primary_key=True, autoincrement=True)
    store_id = Column(String, ForeignKey("stores.store_id"), nullable=False, index=True)
    sku_id = Column(String, ForeignKey("skus.sku_id"), nullable=False, index=True)
    shelf_slot = Column(String, nullable=True)
    shelf_stock_units = Column(Integer, nullable=False, default=0)
    shelf_capacity_units = Column(Integer, nullable=False, default=40)
    backroom_stock_units = Column(Integer, nullable=False, default=0)
    total_stock_units = Column(Integer, nullable=True)
    safety_stock_threshold_units = Column(Integer, nullable=False, default=25)
    reorder_point_units = Column(Integer, nullable=False, default=50)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

