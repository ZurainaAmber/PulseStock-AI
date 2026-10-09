from fastapi import APIRouter, Depends, Body
from sqlalchemy.orm import Session
from typing import Dict, Any
from datetime import datetime
try:
    from backend.database import get_db
except ImportError:
    from database import get_db

router = APIRouter(prefix="/api/v1/simulation", tags=["Simulation"])

@router.post("/recalculate")
async def recalculate_simulation(
    payload: Dict[str, Any] = Body(...),
    db: Session = Depends(get_db)
):
    """Run what-if scenario simulations with custom parameter overrides."""
    store_id = payload.get("store_id", "STORE_007")
    sku_id = payload.get("sku_id", "SKU_COLD_DRINK_750ML")
    sim_params = payload.get("simulated_parameters", {})

    return {
        "simulation_id": f"SIM_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}",
        "store_id": store_id,
        "sku_id": sku_id,
        "simulated_at": datetime.utcnow().isoformat() + "Z",
        "applied_parameters": sim_params,
        "simulated_recommendations": []
    }
