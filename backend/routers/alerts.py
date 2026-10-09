from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from typing import Optional
from datetime import datetime
try:
    from backend.database import get_db
    from backend.models.alert import StockoutAlert
except ImportError:
    from database import get_db
    from models.alert import StockoutAlert

router = APIRouter(prefix="/api/v1/alerts", tags=["Alerts"])

@router.get("/stockouts")
async def get_stockout_alerts(
    store_id: Optional[str] = Query(None, description="Filter by store ID"),
    min_severity: Optional[str] = Query("LOW", description="Minimum alert severity"),
    time_horizon_hours: Optional[int] = Query(4, description="Projection window in hours"),
    db: Session = Depends(get_db)
):
    """List active stock-out alerts filtered by store or severity."""
    query = db.query(StockoutAlert)
    if store_id:
        query = query.filter(StockoutAlert.store_id == store_id)
    
    alerts = query.all()
    return {
        "timestamp": datetime.utcnow().isoformat() + "Z",
        "total_alerts": len(alerts),
        "alerts": alerts
    }

@router.get("/stockouts/{alert_id}")
async def get_stockout_alert_detail(
    alert_id: str,
    db: Session = Depends(get_db)
):
    """Fetch single stock-out alert by ID."""
    alert = db.query(StockoutAlert).filter(StockoutAlert.alert_id == alert_id).first()
    if not alert:
        return {
            "error": {
                "code": "RESOURCE_NOT_FOUND",
                "message": f"Alert with ID '{alert_id}' was not found.",
                "timestamp": datetime.utcnow().isoformat() + "Z"
            }
        }
    return alert
