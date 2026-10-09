# PulseStock AI - Decision Engine Interface Contract

**Language/Runtime:** Python 3.10+  
**Data Validation Framework:** Pydantic v2 (`pydantic>=2.0`)  
**Integration Pattern:** Direct Python module import into FastAPI handlers (`from engine.decision_engine import PulseStockEngine`)  

---

## 1. Overview & Architectural Principles

The **PulseStock Decision Engine** is a deterministic Python module responsible for:
1. Calculating 24-hour hourly demand forecasts with non-linear event uplifts (Cricket match, Rain intensity, Festival traffic).
2. Detecting next 4-hour stock-out risks across store shelves and backrooms.
3. Evaluating and ranking 4 concrete resolution strategies:
   - `TRANSFER`: Inter-store inventory transfer via hyper-local riders.
   - `EARLIER_TRUCK`: Expediting central warehouse logistics truck dispatch.
   - `SHELF_SWAP`: Reallocating shelf real estate from slow-moving SKUs to critical SKUs.
   - `WAIT`: Doing nothing and waiting for standard scheduled replenishment.
4. Executing what-if scenario simulations based on dynamic user adjustments.

---

## 2. Python Data Models (Pydantic v2)

Below are the exact Pydantic data schemas that must be shared between the `backend/` and `engine/` modules.

```python
from enum import Enum
from typing import List, Optional, Dict
from pydantic import BaseModel, Field, ConfigDict
from datetime import datetime

# ==========================================
# Enums
# ==========================================

class AlertSeverity(str, Enum):
    CRITICAL = "CRITICAL"   # Stockout within 60 mins
    HIGH = "HIGH"           # Stockout within 120 mins
    MEDIUM = "MEDIUM"       # Stockout within 240 mins
    LOW = "LOW"             # No stockout within 4 hours

class OptionType(str, Enum):
    TRANSFER = "TRANSFER"
    EARLIER_TRUCK = "EARLIER_TRUCK"
    SHELF_SWAP = "SHELF_SWAP"
    WAIT = "WAIT"

class MatchStatus(str, Enum):
    UPCOMING = "UPCOMING"
    IN_PROGRESS = "IN_PROGRESS"
    COMPLETED = "COMPLETED"

class RainIntensity(str, Enum):
    NONE = "NONE"
    LIGHT = "LIGHT"
    MODERATE = "MODERATE"
    HEAVY_RAIN = "HEAVY_RAIN"

# ==========================================
# Input Models
# ==========================================

class StoreInventoryInput(BaseModel):
    store_id: str = Field(..., example="STORE_007")
    store_name: str = Field(..., example="Store 7 - Koramangala Tech Park")
    sku_id: str = Field(..., example="SKU_COLD_DRINK_750ML")
    sku_name: str = Field(..., example="Sparkling Cola 750ml")
    category: str = Field(..., example="Cold Beverages")
    shelf_stock_units: int = Field(..., ge=0, example=35)
    shelf_capacity_units: int = Field(..., ge=0, example=40)
    backroom_stock_units: int = Field(..., ge=0, example=20)
    safety_stock_threshold_units: int = Field(..., ge=0, example=25)
    reorder_point_units: int = Field(..., ge=0, example=50)
    unit_cost_price_inr: float = Field(..., gt=0.0, example=60.0)
    unit_selling_price_inr: float = Field(..., gt=0.0, example=90.0)
    holding_cost_per_unit_day_inr: float = Field(default=1.5, example=1.5)

class CricketMatchInput(BaseModel):
    is_active: bool = Field(..., example=True)
    match_title: str = Field(default="India vs Pakistan T20", example="India vs Pakistan T20")
    stadium_distance_km: float = Field(..., ge=0.0, example=1.4)
    status: MatchStatus = Field(default=MatchStatus.IN_PROGRESS)
    category_multiplier: float = Field(default=2.5, ge=1.0, example=2.5)

class RainForecastInput(BaseModel):
    is_active: bool = Field(..., example=True)
    precipitation_mm_hr: float = Field(..., ge=0.0, example=22.5)
    intensity: RainIntensity = Field(default=RainIntensity.HEAVY_RAIN)
    delivery_speed_reduction_pct: float = Field(default=40.0, ge=0.0, le=100.0, example=40.0)
    beverage_demand_multiplier: float = Field(default=1.35, ge=1.0, example=1.35)

class FestivalEventInput(BaseModel):
    is_active: bool = Field(..., example=True)
    festival_name: str = Field(default="Diwali", example="Diwali Pre-Shopping Week")
    category_multiplier: float = Field(default=1.25, ge=1.0, example=1.25)

class EventContextInput(BaseModel):
    cricket: Optional[CricketMatchInput] = None
    weather: Optional[RainForecastInput] = None
    festival: Optional[FestivalEventInput] = None

class DonorStoreInput(BaseModel):
    donor_store_id: str = Field(..., example="STORE_003")
    donor_store_name: str = Field(..., example="Store 3 - Indiranagar")
    distance_km: float = Field(..., ge=0.0, example=3.4)
    current_stock_units: int = Field(..., ge=0, example=210)
    surplus_units: int = Field(..., ge=0, example=140)
    transfer_eta_minutes: int = Field(..., gt=0, example=28)
    estimated_transfer_cost_inr: float = Field(..., ge=0.0, example=150.0)

class WarehouseStockInput(BaseModel):
    warehouse_id: str = Field(..., example="WH_CENTRAL_01")
    available_stock_units: int = Field(..., ge=0, example=2400)
    expedited_truck_available: bool = Field(..., example=True)
    expedited_truck_id: Optional[str] = Field(default="TRK_EXPRESS_109")
    expedited_eta_minutes: int = Field(..., gt=0, example=35)
    expedited_cost_inr: float = Field(..., ge=0.0, example=350.0)
    scheduled_truck_eta_minutes: int = Field(..., gt=0, example=120)

class LogisticsInput(BaseModel):
    available_riders: int = Field(..., ge=0, example=3)
    required_riders: int = Field(..., ge=0, example=9)
    rider_surge_multiplier: float = Field(default=1.35, ge=1.0, example=1.35)
    donors: List[DonorStoreInput] = Field(default_factory=list)
    warehouse: WarehouseStockInput

class SimulationParametersInput(BaseModel):
    override_cricket_multiplier: Optional[float] = None
    override_rain_mm_hr: Optional[float] = None
    override_available_riders: Optional[int] = None
    override_transfer_quantity_units: Optional[int] = None

class EngineInputPayload(BaseModel):
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    store_inventory: StoreInventoryInput
    events: EventContextInput
    logistics: LogisticsInput

# ==========================================
# Output Models
# ==========================================

class HourlyForecastPoint(BaseModel):
    timestamp: datetime
    hour_label: str
    baseline_demand_units: int
    cricket_uplift_units: int
    rain_uplift_units: int
    festival_uplift_units: int
    final_projected_demand_units: int
    confidence_lower_bound: int
    confidence_upper_bound: int

class StockoutAlertOutput(BaseModel):
    alert_id: str
    store_id: str
    sku_id: str
    severity: AlertSeverity
    current_total_stock_units: int
    shelf_stock_units: int
    backroom_stock_units: int
    projected_hourly_demand_units: int
    stockout_probability: float = Field(..., ge=0.0, le=1.0)
    minutes_until_stockout: Optional[int]
    estimated_stockout_timestamp: Optional[datetime]
    primary_driver: str
    shelf_replenishment_alert: bool = Field(default=False)

class ActionParametersOutput(BaseModel):
    source_type: Optional[str] = None  # "STORE", "WAREHOUSE", "INTERNAL", "NONE"
    source_id: Optional[str] = None
    truck_id: Optional[str] = None
    transfer_quantity_units: Optional[int] = None
    eta_minutes: Optional[int] = None
    estimated_arrival_timestamp: Optional[datetime] = None
    source_sku_id: Optional[str] = None
    target_sku_id: Optional[str] = None
    slots_reallocated: Optional[int] = None

class FinancialImpactOutput(BaseModel):
    execution_cost_inr: float
    revenue_saved_inr: float
    net_gain_inr: float

class TradeoffAnalysisOutput(BaseModel):
    pros: List[str]
    cons: List[str]

class RecommendationOptionOutput(BaseModel):
    recommendation_id: str
    option_type: OptionType
    rank: int
    title: str
    summary: str
    confidence_score: float = Field(..., ge=0.0, le=1.0)
    stockout_prevented: bool
    action_parameters: ActionParametersOutput
    financial_impact: FinancialImpactOutput
    tradeoff_analysis: TradeoffAnalysisOutput
    is_recommended: bool

class EngineOutputPayload(BaseModel):
    evaluated_at: datetime
    alert: StockoutAlertOutput
    hourly_forecast: List[HourlyForecastPoint]
    recommendations: List[RecommendationOptionOutput]

    model_config = ConfigDict(use_enum_values=True)
```

---

## 3. Decision Engine Interface Specification

The core class must implement the following public method interface:

```python
class PulseStockEngine:
    def __init__(self, demand_decay_rate: float = 0.05):
        """Initializes decision engine with heuristic weighting parameters."""
        self.demand_decay_rate = demand_decay_rate

    def evaluate_stockout_risk(self, payload: EngineInputPayload) -> EngineOutputPayload:
        """
        Executes full evaluation pipeline:
        1. Calculates hourly demand curve using multiplicative event model.
        2. Projects inventory depletion across shelf & backroom.
        3. Identifies stockout timeframe and severity level.
        4. Generates and ranks 4 resolution options (TRANSFER, EARLIER_TRUCK, SHELF_SWAP, WAIT).
        """
        ...

    def calculate_hourly_forecast(
        self, 
        store_inventory: StoreInventoryInput, 
        events: EventContextInput
    ) -> List[HourlyForecastPoint]:
        """Calculates 24-hour demand curve given baseline and active multipliers."""
        ...

    def run_what_if_simulation(
        self, 
        payload: EngineInputPayload, 
        sim_params: SimulationParametersInput
    ) -> EngineOutputPayload:
        """
        Clones payload, applies parameter overrides, and returns simulated evaluation 
        without mutating persistent database state.
        """
        ...
```

---

## 4. Business Logic & Edge Case Rules

The engine implementation MUST obey these deterministic guidelines:

### Rule 1: Multiplicative Demand Uplift Formula
$$\text{Final Demand} = \text{Baseline Demand} \times \text{Cricket Multiplier} \times \text{Rain Multiplier} \times \text{Festival Multiplier}$$
- *Cap:* Combined total demand multiplier is capped at `4.5x` baseline to prevent unrealistically divergent spikes.

### Rule 2: Shelf vs Backroom Inventory Depletion Sequence
- Primary sales deplete **shelf stock** first.
- If `shelf_stock_units == 0` but `backroom_stock_units > 0`:
  - Emit `shelf_replenishment_alert = True`.
  - Minutes until stockout is evaluated against `total_stock_units` (Shelf + Backroom).

### Rule 3: Rider Shortage Impact on `TRANSFER` Option
- If `available_riders < 2`:
  - `TRANSFER` ETA increases by `+25 minutes` due to courier delay.
  - Confidence score for `TRANSFER` option is penalized by `-0.25`.
  - `EARLIER_TRUCK` rank automatically moves above `TRANSFER`.

### Rule 4: Zero Warehouse Stock Scenario
- If `warehouse.available_stock_units == 0`:
  - `EARLIER_TRUCK` option is marked `stockout_prevented = False` and demoted to lowest rank.

---

## 5. Backend FastAPI Usage Example

```python
# backend/routers/recommendations.py
from fastapi import APIRouter, HTTPException, Depends
from engine.decision_engine import PulseStockEngine
from engine.models import EngineInputPayload, EngineOutputPayload

router = APIRouter(prefix="/api/v1", tags=["Recommendations"])
engine = PulseStockEngine()

@router.get("/recommendations", response_model=EngineOutputPayload)
async def get_recommendations(alert_id: str):
    # 1. Fetch raw store inventory, events, logistics from SQLite DB
    raw_payload = await fetch_engine_input_from_db(alert_id)
    
    # 2. Invoke Decision Engine directly in Python
    output: EngineOutputPayload = engine.evaluate_stockout_risk(raw_payload)
    
    return output
```
