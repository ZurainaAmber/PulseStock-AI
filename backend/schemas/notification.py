from pydantic import BaseModel
from typing import Optional
from datetime import datetime

class NotificationResponse(BaseModel):
    notification_id: str
    manager_id: str
    title: str
    message: str
    type: str
    request_id: Optional[str] = None
    is_read: bool
    created_at: datetime

    class Config:
        from_attributes = True
