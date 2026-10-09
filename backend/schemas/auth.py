from pydantic import BaseModel, Field
from typing import Optional

class LoginRequest(BaseModel):
    username: str = Field(..., example="manager_store_007")
    password: str = Field(..., example="PulseStock2026!")

class ManagerProfile(BaseModel):
    manager_id: str = Field(..., example="MGR_STORE_007")
    username: str = Field(..., example="manager_store_007")
    full_name: str = Field(..., example="Store 7 Manager")
    role: str = Field(..., example="STORE_MANAGER")
    store_id: Optional[str] = Field(default=None, example="STORE_007")

    class Config:
        from_attributes = True

class LoginResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    manager: ManagerProfile
