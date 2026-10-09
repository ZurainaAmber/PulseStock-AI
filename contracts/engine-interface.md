# PulseStock AI — Decision Engine Interface Contract
**Cypher 2026 · Challenge 6: Before the Match Starts (Zipcart)**  
**Version:** 1.0.0 · **Target Language:** Python 3.10+ (`decision_engine/`)

---

## 1. Developer 2 Quickstart

This document defines the **exact Python functions, data classes, and return dictionaries** expected by the FastAPI backend.

> [!TIP]
> **Zero Framework Dependencies:**  
> The Decision Engine is built as **pure Python functions** with zero dependencies on FastAPI, SQLite, or React. Developer 2 can write unit tests using `pytest` directly against simulated dictionaries and dataclasses!

### Recommended Directory Structure:
```text
decision_engine/
├── __init__.py
├── models.py            # Dataclasses & Enums defined below
├── demand_forecaster.py # Step 1: Hourly projection & event uplift
├── diagnostician.py     # Step 2 & 3: Stock vs shelf vs inbound vs rider
├── scope_detector.py    # Step 4: Local vs City-wide surge
├── planner.py           # Step 5: Candidate generation
├── critic.py            # Step 6: Hard constraints & traffic ETA gate
├── decider.py           # Step 7 & 8: Scoring & ranking
├── explainer.py         # Step 9: Deterministic explanation generator
├── event_manifest.py    # Section 7: 3-day multi-truck replenishment
└── test_engine.py       # Unit tests covering all 7 PDF scenarios
```

---

## 2. Core Enums and Dataclasses (`models.py`)

```python
from dataclasses import dataclass, field
from enum import Enum
from typing import List, Optional, Dict, Any
from datetime import datetime

class BottleneckType(str, Enum):
    STOCK_DEFICIT = "STOCK_DEFICIT"
    SHELF_LIMIT = "SHELF_LIMIT"
    INBOUND_DELAY = "INBOUND_DELAY"
    RIDER_SHORTAGE = "RIDER_SHORTAGE"
    HEALTHY = "HEALTHY"

class ActionType(str, Enum):
    TRANSFER = "TRANSFER"
    EARLY_TRUCK = "EARLY_TRUCK"
    SHELF_SWAP = "SHELF_SWAP"
    COMBINED_SWAP_AND_TRANSFER = "COMBINED_SWAP_AND_TRANSFER"
    RIDER_ESCALATION = "RIDER_ESCALATION"
    CITY_WIDE_ALLOCATION = "CITY_WIDE_ALLOCATION"
    WAIT = "WAIT"

class ScopeMode(str, Enum):
    LOCAL = "LOCAL"
    CITY_WIDE_SURGE = "CITY_WIDE_SURGE"

class UrgencyLevel(str, Enum):
    CRITICAL = "CRITICAL"
    HIGH = "HIGH"
    MEDIUM = "MEDIUM"
    HEALTHY = "HEALTHY"

@dataclass
class HourlyDemandPoint:
    hour_label: str             # e.g., "17:00"
    baseline_demand: float      # e.g., 3.0
    uplift_multiplier: float    # e.g., 3.0
    projected_demand: float     # baseline * uplift
    stock_at_start: float
    stock_at_end: float
    is_stockout: bool
    stockout_exact_time: Optional[str] = None  # e.g., "20:13"

@dataclass
class DemandProjectionResult:
    store_id: str
    sku_id: str
    timeline: List[HourlyDemandPoint]
    is_stockout_expected: bool
    stockout_timestamp: Optional[str]
    next_truck_timestamp: str
    exposure_minutes: int
    projected_lost_units: int
    potential_lost_margin: float

@dataclass
class DiagnosisResult:
    store_id: str
    sku_id: str
    bottleneck_type: BottleneckType
    urgency: UrgencyLevel
    root_cause: str
    is_actionable: bool         # False if HEALTHY (stockout after truck arrival)
    projection: DemandProjectionResult

@dataclass
class LogisticsEvaluation:
    origin_id: str
    destination_id: str
    base_minutes: float
    traffic_factor: float
    loading_minutes: float
    total_eta_minutes: float
    is_blocked: bool
    beats_stockout_deadline: bool

@dataclass
class ActionOption:
    action_type: ActionType
    title: str
    quantity: int
    donor_store_id: Optional[str] = None
    evicted_slot_id: Optional[str] = None
    evicted_sku_id: Optional[str] = None
    freed_slot_units: int = 0
    truck_id: Optional[str] = None
    eta_minutes: Optional[float] = None
    gross_margin_protected: float = 0.0
    intervention_cost: float = 0.0
    donor_risk_penalty: float = 0.0
    net_margin_protected: float = 0.0
    is_feasible: bool = True
    rejection_reason: Optional[str] = None

@dataclass
class DecisionOutput:
    alert_id: str
    store_id: str
    sku_id: str
    scope_mode: ScopeMode
    diagnosis: DiagnosisResult
    primary_recommendation: ActionOption
    fallback_recommendation: Optional[ActionOption]
    summary_explanation: str
    chain_of_thought: List[str]
```

---

## 3. Function Specifications

### Step 1: Project Demand Hour-by-Hour
```python
def project_demand_curve(
    store_id: str,
    sku_id: str,
    current_stock: int,
    current_time: str,          # ISO string, e.g., "2026-10-10T17:00:00"
    horizon_hours: int,         # e.g., 6 hours ahead
    baseline_hourly_demands: Dict[int, float], # {17: 3.0, 18: 3.0, 19: 3.0, 20: 3.0, 21: 3.0}
    active_events: List[Dict[str, Any]],       # matching category events with uplift
    next_truck_arrival: str,                   # "2026-10-10T21:00:00"
    unit_margin: float                         # 13.50
) -> DemandProjectionResult:
    """
    Step 1 & 2: Projects hour-by-hour demand by multiplying baseline by event uplift.
    Steps forward subtracting demand from stock.
    Calculates exact stock-out time fraction (e.g., remaining 6.5 bottles / 9.0/hr = 43 mins -> 20:13).
    Calculates exposure gap (stockout_time to truck_arrival).
    """
```

---

### Step 2 & 3: Diagnose the Real Bottleneck
```python
def diagnose_bottleneck(
    projection: DemandProjectionResult,
    slot_capacity: int,
    current_stock: int,
    active_riders: int,
    orders_per_rider_hour: float,
    current_hourly_order_rate: float
) -> DiagnosisResult:
    """
    Step 3: Classifies why orders are dropping:
    1. If stock lasts beyond next truck -> BottleneckType.HEALTHY
    2. If (active_riders * orders_per_rider_hour) < current_hourly_order_rate:
       -> BottleneckType.RIDER_SHORTAGE ("don't move stock, escalate riders")
    3. If current_stock >= slot_capacity or (slot_capacity - current_stock) < projection.projected_lost_units:
       -> BottleneckType.SHELF_LIMIT
    4. Otherwise:
       -> BottleneckType.STOCK_DEFICIT
    """
```

---

### Step 4: Detect Scope (Scope Detector)
```python
def detect_systemic_scope(
    all_diagnoses: List[DiagnosisResult],
    surge_threshold_pct: float = 0.40
) -> ScopeMode:
    """
    Step 4: Checks category-wide flags.
    If >= 40% of stores are flagged with STOCK_DEFICIT for the same category,
    switches system to ScopeMode.CITY_WIDE_SURGE.
    """
```

---

### Step 5 & 6: Evaluate Feasibility & Hard Constraints (Critic)
```python
def evaluate_transit_feasibility(
    origin_store_id: str,
    destination_store_id: str,
    base_minutes: float,
    traffic_factor: float,
    loading_minutes: float,
    is_blocked: bool,
    minutes_until_stockout: float,
    safety_buffer_minutes: float = 10.0
) -> LogisticsEvaluation:
    """
    Step 6: Calculates traffic-adjusted ETA:
    ETA = (base_minutes * traffic_factor) + loading_minutes
    Feasible only if: NOT is_blocked AND (ETA + buffer) <= minutes_until_stockout.
    """
```

```python
def check_donor_safety(
    donor_current_stock: int,
    donor_hourly_demand: float,
    hours_until_donor_next_truck: float,
    requested_transfer_units: int,
    donor_safety_buffer: int = 5
) -> bool:
    """
    Ensures transfer NEVER creates a new stock-out at the donor store:
    donor_surplus = donor_stock - (donor_demand * hours) - safety_buffer
    Returns True if donor_surplus >= requested_transfer_units.
    """
```

---

### Step 7: Score & Rank Interventions (Decider)
```python
def rank_and_select_action(
    diagnosis: DiagnosisResult,
    candidate_options: List[ActionOption],
    unit_margin: float
) -> DecisionOutput:
    """
    Step 7 & 8: Scores candidates by:
    Net Margin Protected = (Avoided Lost Units * Unit Margin) - Intervention Cost - Donor Risk Cost.
    
    Ranks feasible options descending by net margin.
    Selects #1 as Primary, #2 as Fallback.
    Returns DecisionOutput with deterministic explanation.
    """
```

---

### Section 7 Differentiator: 3-Day Event Truck Manifest
```python
@dataclass
class ManifestDrop:
    truck_id: str
    drop_day: str              # "DAY_BEFORE", "EVENT_DAY", "DAY_AFTER"
    sku_id: str
    planned_units: int
    binding_constraint: str    # "limited by shelf: 30 units" | "limited by truck capacity" | "limited by warehouse"
    margin_density: float

def build_3day_event_manifest(
    store_id: str,
    sku_list: List[str],
    scheduled_trucks: List[Dict[str, Any]],
    shelf_capacities: Dict[str, int],
    current_stocks: Dict[str, int],
    projected_demands_until_next: Dict[str, int],
    warehouse_available_stocks: Dict[str, int]
) -> List[ManifestDrop]:
    """
    Calculates drops for each truck using the formula:
    Max drop = min(
        projected_demand_until_next_truck - current_stock,
        shelf_slot_capacity - current_stock,
        warehouse_stock_available,
        remaining_truck_capacity
    )
    Fills truck greedily by value density (margin per unit volume).
    Identifies and logs the binding constraint.
    """
```

---

### Step 10: Re-Planning Engine Trigger
```python
def trigger_replan(
    alert_id: str,
    reason: str,               # "MANAGER_REJECTED" | "TRAFFIC_BLOCKAGE" | "SALES_SPIKE"
    updated_state: Dict[str, Any]
) -> DecisionOutput:
    """
    Automatically re-evaluates candidates when:
    - Manager rejects Primary option (promotes Fallback to Primary)
    - Traffic blockage is simulated on route (reroutes to alternative donor or early truck)
    - Actual sales pace exceeds forecast by > 20%
    """
```

---

## 4. Test Verification Checklist (Demo Scenarios)

The Decision Engine test suite (`test_engine.py`) must pass tests for all 7 scenarios specified in Section 11 of the solution document:

1. **Scenario 1 (Match-Night Transfer):** Store 7 Cola stock-out at 20:13 resolved by Store 9 transfer.
2. **Scenario 2 (Full Shelf Swap):** Slot full, clears 4-sales/week snack slot before transfer.
3. **Scenario 3 (Donor Safety Check):** Donor store has insufficient surplus; transfer correctly rejected.
4. **Scenario 4 (Rider Shortage):** Stock is 78 units, 1 rider active; outputs rider escalation, zero stock transfer.
5. **Scenario 5 (Simulated Traffic Blockage):** Route blocked (`is_blocked = True`); switches to Early Truck.
6. **Scenario 6 (City-Wide Surge):** 60% stores short; disables lateral transfers and switches to warehouse allocation.
7. **Scenario 7 (Healthy Store):** Stock lasts past truck; returns `HEALTHY` and takes zero disruptive actions.
