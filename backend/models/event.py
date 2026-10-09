from datetime import datetime
from sqlalchemy import Column, String, Float, Integer, DateTime, ForeignKey
try:
    from backend.database import Base
except ImportError:
    from database import Base

class ExternalEvent(Base):
    __tablename__ = "external_events"

    event_id = Column(String, primary_key=True, index=True)
    event_type = Column(String, nullable=False)  # CRICKET, RAIN, FESTIVAL
    title = Column(String, nullable=False)
    store_id = Column(String, ForeignKey("stores.store_id"), nullable=True, index=True)
    affected_category = Column(String, nullable=True)
    multiplier = Column(Float, nullable=False, default=1.0)
    precipitation_mm_hr = Column(Float, default=0.0)
    is_active = Column(Integer, default=1)  # 1 for True, 0 for False
    start_time = Column(DateTime, nullable=False)
    end_time = Column(DateTime, nullable=False)

