from fastapi import APIRouter, Depends, Query, Body, HTTPException
from sqlalchemy.orm import Session
from typing import Optional, Dict, Any
from datetime import datetime
try:
    from backend.database import get_db
    from backend.models.recommendation import Recommendation
    from backend.models.action_log import ActionLog
except ImportError:
    from database import get_db
    from models.recommendation import Recommendation
    from models.action_log import ActionLog

router = APIRouter(prefix="/api/v1/recommendations", tags=["Recommendations"])

@router.get("")
async def get_recommendations(
    alert_id: str = Query(..., description="Alert ID to evaluate"),
    db: Session = Depends(get_db)
):
    """Retrieve decision engine recommendations for a stockout alert."""
    recommendations = db.query(Recommendation).filter(Recommendation.alert_id == alert_id).all()
    return {
        "alert_id": alert_id,
        "evaluated_at": datetime.utcnow().isoformat() + "Z",
        "recommendations": recommendations
    }

@router.post("/{recommendation_id}/approve")
async def approve_recommendation(
    recommendation_id: str,
    payload: Dict[str, Any] = Body(...),
    db: Session = Depends(get_db)
):
    """Submit manager approval for a recommendation."""
    rec = db.query(Recommendation).filter(Recommendation.recommendation_id == recommendation_id).first()
    if not rec:
        raise HTTPException(status_code=404, detail=f"Recommendation '{recommendation_id}' not found.")
    
    manager_id = payload.get("manager_id", "UNKNOWN_MANAGER")
    notes = payload.get("manager_notes", "")
    
    import uuid
    action_id = f"ACT_{datetime.utcnow().strftime('%Y%m%d%H%M%S')}_{uuid.uuid4().hex[:4].upper()}"
    
    action = ActionLog(
        action_id=action_id,
        alert_id=rec.alert_id,
        recommendation_id=rec.recommendation_id,
        store_id="STORE_007",
        sku_id="SKU_COLD_DRINK_750ML",
        action_type=rec.option_type,
        status="APPROVED",
        manager_id=manager_id,
        notes=notes,
        cost_inr=rec.execution_cost_inr
    )
    db.add(action)
    db.commit()
    db.refresh(action)

    return {
        "action_id": action_id,
        "alert_id": rec.alert_id,
        "recommendation_id": recommendation_id,
        "status": "APPROVED",
        "executed_at": datetime.utcnow().isoformat() + "Z",
        "manager_id": manager_id,
        "action_summary": f"Approved {rec.option_type} recommendation.",
        "simulated_outcome": {
            "stockout_prevented": bool(rec.stockout_prevented)
        }
    }

@router.post("/{recommendation_id}/reject")
async def reject_recommendation(
    recommendation_id: str,
    payload: Dict[str, Any] = Body(...),
    db: Session = Depends(get_db)
):
    """Submit manager rejection for a recommendation."""
    rec = db.query(Recommendation).filter(Recommendation.recommendation_id == recommendation_id).first()
    if not rec:
        raise HTTPException(status_code=404, detail=f"Recommendation '{recommendation_id}' not found.")

    manager_id = payload.get("manager_id", "UNKNOWN_MANAGER")
    notes = payload.get("notes", "")

    import uuid
    action_id = f"ACT_REJ_{datetime.utcnow().strftime('%Y%m%d%H%M%S')}_{uuid.uuid4().hex[:4].upper()}"

    action = ActionLog(
        action_id=action_id,
        alert_id=rec.alert_id,
        recommendation_id=rec.recommendation_id,
        store_id="STORE_007",
        sku_id="SKU_COLD_DRINK_750ML",
        action_type=rec.option_type,
        status="REJECTED",
        manager_id=manager_id,
        notes=notes,
        cost_inr=0.0
    )
    db.add(action)
    db.commit()

    return {
        "recommendation_id": recommendation_id,
        "status": "REJECTED",
        "rejected_at": datetime.utcnow().isoformat() + "Z"
    }
