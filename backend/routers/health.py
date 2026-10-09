from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from sqlalchemy import text
from datetime import datetime
try:
    from backend.database import get_db
    from backend.schemas.health import HealthResponse
except ImportError:
    from database import get_db
    from schemas.health import HealthResponse

router = APIRouter(tags=["Health"])

@router.get("/health", response_model=HealthResponse)
@router.get("/api/v1/health", response_model=HealthResponse)
async def check_health(db: Session = Depends(get_db)):
    """Health check endpoint to verify backend service and SQLite database connection."""
    db_status = "connected"
    try:
        # Simple lightweight DB connectivity check
        db.execute(text("SELECT 1"))
    except Exception as e:
        db_status = f"error: {str(e)}"

    return HealthResponse(
        status="ok" if db_status == "connected" else "degraded",
        service="PulseStock AI Backend",
        database=db_status,
        timestamp=datetime.utcnow()
    )
