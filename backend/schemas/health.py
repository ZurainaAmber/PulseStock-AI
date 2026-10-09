from pydantic import BaseModel, Field
from datetime import datetime

class HealthResponse(BaseModel):
    status: str = Field(default="ok", example="ok")
    service: str = Field(default="PulseStock AI Backend", example="PulseStock AI Backend")
    database: str = Field(default="connected", example="connected")
    timestamp: datetime = Field(default_factory=datetime.utcnow)
