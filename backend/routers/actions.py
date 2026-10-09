from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from typing import Optional
try:
    from backend.database import get_db
    from backend.models.action_log import ActionLog
except ImportError:
    from database import get_db
    from models.action_log import ActionLog

router = APIRouter(prefix="/api/v1/actions", tags=["Actions"])

@router.get("/history")
async def get_action_history(
    store_id: Optional[str] = Query(None, description="Filter by store ID"),
    limit: Optional[int] = Query(20, description="Results limit"),
    db: Session = Depends(get_db)
):
    """Retrieve audit trail of approved, rejected, and executed actions."""
    query = db.query(ActionLog)
    if store_id:
        query = query.filter(ActionLog.store_id == store_id)
    
    actions = query.order_by(ActionLog.created_at.desc()).limit(limit).all()
    return {
        "total_records": len(actions),
        "actions": actions
    }
