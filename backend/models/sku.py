from datetime import datetime
from sqlalchemy import Column, String, Float, DateTime
try:
    from backend.database import Base
except ImportError:
    from database import Base

class SKU(Base):
    __tablename__ = "skus"

    sku_id = Column(String, primary_key=True, index=True)
    sku_name = Column(String, nullable=False)
    category = Column(String, nullable=False)
    size = Column(String, nullable=True)
    unit_selling_price_inr = Column(Float, nullable=False)
    margin_pct = Column(Float, nullable=True)
    unit_cost_price_inr = Column(Float, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)

