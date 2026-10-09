from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

try:
    from backend.database import get_db
    from backend.models.manager import Manager
    from backend.schemas.auth import LoginRequest, LoginResponse, ManagerProfile
    from backend.auth import verify_password, create_access_token, get_current_manager
except ImportError:
    from database import get_db
    from models.manager import Manager
    from schemas.auth import LoginRequest, LoginResponse, ManagerProfile
    from auth import verify_password, create_access_token, get_current_manager

router = APIRouter(prefix="/api/v1/auth", tags=["Authentication"])

@router.post("/login", response_model=LoginResponse)
async def login(payload: LoginRequest, db: Session = Depends(get_db)):
    """Authenticates store or city operations manager and returns access token."""
    manager = db.query(Manager).filter(Manager.username == payload.username).first()
    if not manager or not verify_password(payload.password, manager.password_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid username or password.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    token_data = {
        "sub": manager.manager_id,
        "username": manager.username,
        "role": manager.role,
        "store_id": manager.store_id
    }
    token = create_access_token(data=token_data)

    return LoginResponse(
        access_token=token,
        token_type="bearer",
        manager=ManagerProfile.model_validate(manager)
    )

@router.get("/me", response_model=ManagerProfile)
async def get_me(current_manager: Manager = Depends(get_current_manager)):
    """Retrieves current authenticated manager profile details."""
    return ManagerProfile.model_validate(current_manager)
