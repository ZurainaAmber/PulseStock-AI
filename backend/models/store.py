from datetime import datetime
from sqlalchemy import Column, String, Float, DateTime
try:
    from backend.database import Base
except ImportError:
    from database import Base

class Store(Base):
    __tablename__ = "stores"

    store_id = Column(String, primary_key=True, index=True)
    store_name = Column(String, nullable=False)
    location_zone = Column(String, nullable=False)
    stadium_proximity_km = Column(Float, default=0.0)
    created_at = Column(DateTime, default=datetime.utcnow)
