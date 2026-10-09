from typing import List, Optional
from fastapi import APIRouter, Depends, Query, Path, HTTPException, status
from sqlalchemy.orm import Session

try:
    from backend.database import get_db
    from backend.models.manager import Manager
    from backend.models.notification import ManagerNotification
    from backend.schemas.notification import NotificationResponse
    from backend.auth import get_current_manager
except ImportError:
    from database import get_db
    from models.manager import Manager
    from models.notification import ManagerNotification
    from schemas.notification import NotificationResponse
    from auth import get_current_manager

router = APIRouter(prefix="/api/v1/notifications", tags=["Notifications"])

@router.get("", response_model=List[NotificationResponse])
async def list_notifications(
    is_read: Optional[bool] = Query(default=None, description="Filter by read status"),
    limit: int = Query(default=50, ge=1, le=100),
    current_manager: Manager = Depends(get_current_manager),
    db: Session = Depends(get_db)
):
    """Retrieves notifications for the current authenticated manager (polling endpoint)."""
    query = db.query(ManagerNotification).filter(ManagerNotification.manager_id == current_manager.manager_id)
    if is_read is not None:
        query = query.filter(ManagerNotification.is_read == (1 if is_read else 0))
    notifications = query.order_by(ManagerNotification.created_at.desc()).limit(limit).all()
    return notifications

@router.patch("/{notification_id}/read", response_model=NotificationResponse)
async def mark_notification_as_read(
    notification_id: str = Path(...),
    current_manager: Manager = Depends(get_current_manager),
    db: Session = Depends(get_db)
):
    """Marks a notification as read."""
    notif = db.query(ManagerNotification).filter(
        ManagerNotification.notification_id == notification_id,
        ManagerNotification.manager_id == current_manager.manager_id
    ).first()
    if not notif:
        raise HTTPException(status_code=404, detail=f"Notification '{notification_id}' not found.")
    
    notif.is_read = 1
    db.commit()
    db.refresh(notif)
    return notif
