from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from typing import Optional
try:
    from backend.database import get_db
    from backend.models.event import ExternalEvent
except ImportError:
    from database import get_db
    from models.event import ExternalEvent

router = APIRouter(prefix="/api/v1/events", tags=["Events"])

@router.get("/context")
async def get_events_context(
    store_id: Optional[str] = Query(None, description="Store ID filter"),
    db: Session = Depends(get_db)
):
    """Fetch active external event context (Cricket match, Rain, Festival)."""
    query = db.query(ExternalEvent).filter(ExternalEvent.is_active == 1)
    if store_id:
        query = query.filter((ExternalEvent.store_id == store_id) | (ExternalEvent.store_id.is_(None)))
    
    events = query.all()
    return {
        "store_id": store_id,
        "active_events_count": len(events),
        "events": events
    }
