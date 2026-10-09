from pydantic import BaseModel, Field
from typing import Dict, Any, Optional
from datetime import datetime

class ErrorDetail(BaseModel):
    code: str = Field(..., example="RESOURCE_NOT_FOUND")
    message: str = Field(..., example="Store with ID 'STORE_999' was not found.")
    details: Optional[Dict[str, Any]] = Field(default=None)
    timestamp: datetime = Field(default_factory=datetime.utcnow)

class ErrorResponse(BaseModel):
    error: ErrorDetail
