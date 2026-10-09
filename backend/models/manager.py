from datetime import datetime
from sqlalchemy import Column, String, DateTime, ForeignKey
try:
    from backend.database import Base
except ImportError:
    from database import Base

class Manager(Base):
    __tablename__ = "managers"

    manager_id = Column(String, primary_key=True, index=True)
    username = Column(String, unique=True, nullable=False, index=True)
    password_hash = Column(String, nullable=False)
    full_name = Column(String, nullable=False)
    role = Column(String, nullable=False)  # STORE_MANAGER, CITY_MANAGER
    store_id = Column(String, ForeignKey("stores.store_id"), nullable=True, index=True)
    created_at = Column(DateTime, default=datetime.utcnow)
