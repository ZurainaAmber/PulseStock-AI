from datetime import datetime
from sqlalchemy import Column, String, Integer, Float, DateTime, ForeignKey, Text
try:
    from backend.database import Base
except ImportError:
    from database import Base

class Recommendation(Base):
    __tablename__ = "recommendations"

    recommendation_id = Column(String, primary_key=True, index=True)
    alert_id = Column(String, ForeignKey("stockout_alerts.alert_id"), nullable=False, index=True)
    option_type = Column(String, nullable=False)  # TRANSFER, EARLIER_TRUCK, SHELF_SWAP, WAIT
    rank = Column(Integer, nullable=False)
    title = Column(String, nullable=False)
    confidence_score = Column(Float, nullable=False)
    stockout_prevented = Column(Integer, nullable=False)  # 1 for True, 0 for False
    action_params_json = Column(Text, nullable=False)  # JSON string
    execution_cost_inr = Column(Float, nullable=False)
    revenue_saved_inr = Column(Float, nullable=False)
    is_recommended = Column(Integer, nullable=False, default=0)
    created_at = Column(DateTime, default=datetime.utcnow)
