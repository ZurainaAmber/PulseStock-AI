from datetime import datetime
from sqlalchemy import Column, Integer, String, DateTime, ForeignKey
try:
    from backend.database import Base
except ImportError:
    from database import Base

class Order(Base):
    __tablename__ = "orders"

    id = Column(Integer, primary_key=True, autoincrement=True)
    timestamp = Column(DateTime, nullable=False, index=True)
    store_id = Column(String, ForeignKey("stores.store_id"), nullable=False, index=True)
    sku_id = Column(String, ForeignKey("skus.sku_id"), nullable=False, index=True)
    quantity = Column(Integer, nullable=False, default=1)
