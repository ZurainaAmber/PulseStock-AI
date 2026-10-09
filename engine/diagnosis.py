"""
PulseStock AI - Decision Engine: Inventory Problem Diagnosis Module
Cypher 2026 Challenge 6 - Store 7 Stock-out Prevention & Decision Engine

Deterministic diagnosis of operational root causes:
1. Demand Surge (DEMAND_SURGE)
2. Low Inventory (LOW_INVENTORY)
3. Shelf Capacity Constraint (SHELF_CAPACITY_CONSTRAINT)
4. Delayed Truck (DELAYED_TRUCK)
5. Rider Shortage (RIDER_SHORTAGE)

Independent of database access, FastAPI web framework, and LLM calls.
Uses only the Python standard library.
"""

from __future__ import annotations

import math
from datetime import datetime
from typing import Any, Dict, List, Optional, Sequence, Union

try:
    from engine.forecast import _format_number, _parse_timestamp
    from engine.stockout import evaluate_stockout
except ImportError:
    from forecast import _format_number, _parse_timestamp
    from stockout import evaluate_stockout


# ==========================================
# Individual Diagnostic Check Functions
# ==========================================

def diagnose_demand_surge(
    forecast_demand: Optional[Union[int, float]],
    baseline_demand: Optional[Union[int, float]] = None,
    event_uplift: Optional[Union[int, float]] = None,
    time_interval: Optional[str] = None,
    threshold_multiplier: float = 1.25,
) -> Optional[Dict[str, Any]]:
    """
    Identify when forecast demand is unusually high relative to baseline demand.

    Rules:
    - Distinguishes event-driven demand surges from ordinary demand.
    - Requires baseline_demand or event_uplift; does not label demand as high if baseline is missing.
    - Rejects negative demand values with ValueError.
    """
    if forecast_demand is not None:
        if isinstance(forecast_demand, bool) or not isinstance(forecast_demand, (int, float)):
            raise TypeError(f"forecast_demand must be numeric, got: {type(forecast_demand).__name__}")
        if math.isnan(forecast_demand) or math.isinf(forecast_demand):
            raise ValueError(f"forecast_demand cannot be NaN or infinite, got: {forecast_demand}")
        if forecast_demand < 0:
            raise ValueError(f"forecast_demand cannot be negative, got: {forecast_demand}")

    if baseline_demand is not None:
        if isinstance(baseline_demand, bool) or not isinstance(baseline_demand, (int, float)):
            raise TypeError(f"baseline_demand must be numeric, got: {type(baseline_demand).__name__}")
        if math.isnan(baseline_demand) or math.isinf(baseline_demand):
            raise ValueError(f"baseline_demand cannot be NaN or infinite, got: {baseline_demand}")
        if baseline_demand < 0:
            raise ValueError(f"baseline_demand cannot be negative, got: {baseline_demand}")

    if event_uplift is not None:
        if isinstance(event_uplift, bool) or not isinstance(event_uplift, (int, float)):
            raise TypeError(f"event_uplift must be numeric, got: {type(event_uplift).__name__}")
        if math.isnan(event_uplift) or math.isinf(event_uplift):
            raise ValueError(f"event_uplift cannot be NaN or infinite, got: {event_uplift}")
        if event_uplift < 0:
            raise ValueError(f"event_uplift cannot be negative, got: {event_uplift}")

    # Cannot diagnose surge without baseline comparison or explicit uplift
    if baseline_demand is None and event_uplift is None:
        return None

    if forecast_demand is None and event_uplift is None:
        return None

    # Calculate surge ratio
    surge_ratio = 1.0
    if baseline_demand is not None and baseline_demand > 0 and forecast_demand is not None:
        surge_ratio = float(forecast_demand) / float(baseline_demand)
    elif event_uplift is not None:
        surge_ratio = float(event_uplift)

    # If uplift is supplied alongside forecast and baseline
    if event_uplift is not None and event_uplift > surge_ratio:
        surge_ratio = float(event_uplift)

    if surge_ratio < threshold_multiplier:
        return None

    # Determine severity
    if surge_ratio >= 2.5:
        severity = "critical"
    elif surge_ratio >= 2.0:
        severity = "high"
    elif surge_ratio >= 1.5:
        severity = "medium"
    else:
        severity = "low"

    evidence: Dict[str, Any] = {
        "event_uplift": _format_number(event_uplift) if event_uplift is not None else _format_number(surge_ratio),
        "surge_multiplier": round(surge_ratio, 2),
    }
    if baseline_demand is not None:
        evidence["baseline_demand_per_hour"] = _format_number(baseline_demand)
    if forecast_demand is not None:
        evidence["forecast_demand_per_hour"] = _format_number(forecast_demand)
    if time_interval:
        evidence["time_interval"] = time_interval

    return {
        "code": "DEMAND_SURGE",
        "category": "demand",
        "severity": severity,
        "title": "Event-driven demand surge",
        "description": f"Forecast demand is {round(surge_ratio, 2)}x higher than baseline demand.",
        "evidence": evidence,
        "confidence": "high",
    }


def diagnose_low_inventory(
    current_stock: Optional[Union[int, float]] = None,
    forecast_demand: Optional[Sequence[Any]] = None,
    next_truck_arrival: Optional[Union[str, datetime]] = None,
    stockout_evaluation: Optional[Dict[str, Any]] = None,
    start_time: Optional[Union[str, datetime]] = None,
    safety_stock_threshold: Optional[Union[int, float]] = None,
) -> Optional[Dict[str, Any]]:
    """
    Identify products whose current stock or projected inventory is insufficient
    for expected demand before replenishment.

    Reuses Task 2 evaluate_stockout calculation when available or computes it directly.
    """
    if current_stock is not None:
        if isinstance(current_stock, bool) or not isinstance(current_stock, (int, float)):
            raise TypeError(f"current_stock must be numeric, got: {type(current_stock).__name__}")
        if math.isnan(current_stock) or math.isinf(current_stock):
            raise ValueError(f"current_stock cannot be NaN or infinite, got: {current_stock}")
        if current_stock < 0:
            raise ValueError(f"current_stock cannot be negative, got: {current_stock}")

    # Re-use or perform Task 2 stock-out evaluation if inputs provided
    eval_res = stockout_evaluation
    if eval_res is None and current_stock is not None and forecast_demand is not None:
        eval_res = evaluate_stockout(
            initial_stock=current_stock,
            hourly_demand=forecast_demand,
            next_truck_arrival=next_truck_arrival,
            start_time=start_time,
        )

    if eval_res is None:
        if current_stock is not None and safety_stock_threshold is not None:
            if current_stock < safety_stock_threshold:
                return {
                    "code": "LOW_INVENTORY",
                    "category": "inventory",
                    "severity": "medium",
                    "title": "Inventory below safety threshold",
                    "description": f"Current stock ({current_stock}) is below safety threshold ({safety_stock_threshold}).",
                    "evidence": {
                        "current_stock": _format_number(current_stock),
                        "safety_stock_threshold": _format_number(safety_stock_threshold),
                    },
                    "confidence": "medium",
                }
        return None

    stockout_within_horizon = eval_res.get("stockout_within_horizon", False)
    stockout_before_truck = eval_res.get("stockout_before_truck")
    stockout_time = eval_res.get("stockout_time")
    unmet_demand = eval_res.get("unmet_demand_before_truck")
    stock_at_truck = eval_res.get("stock_at_truck_arrival_before_replenishment")
    initial_stock_val = eval_res.get("initial_stock", current_stock)

    is_low_inventory = False
    severity = "medium"

    if stockout_before_truck is True:
        is_low_inventory = True
        severity = "critical" if (unmet_demand is not None and unmet_demand > 0) else "high"
    elif stockout_within_horizon is True:
        is_low_inventory = True
        severity = "high"
    elif safety_stock_threshold is not None and initial_stock_val is not None:
        if initial_stock_val < safety_stock_threshold:
            is_low_inventory = True
            severity = "low"

    if not is_low_inventory:
        return None

    evidence: Dict[str, Any] = {
        "current_stock": _format_number(initial_stock_val) if initial_stock_val is not None else None,
        "stockout_within_horizon": stockout_within_horizon,
        "stockout_time": stockout_time,
    }
    if stockout_before_truck is not None:
        evidence["stockout_before_truck"] = stockout_before_truck
    if eval_res.get("next_truck_arrival"):
        evidence["next_truck_arrival"] = eval_res["next_truck_arrival"]
    if stock_at_truck is not None:
        evidence["stock_at_truck_arrival"] = stock_at_truck
    if unmet_demand is not None:
        evidence["unmet_demand_before_truck"] = unmet_demand

    desc: str
    if stockout_before_truck:
        desc = "Current inventory will deplete before scheduled replenishment truck arrives."
    elif stockout_within_horizon:
        desc = f"Stock-out predicted at {stockout_time} within forecast horizon."
    else:
        desc = "Current inventory is insufficient relative to replenishment horizon."

    return {
        "code": "LOW_INVENTORY",
        "category": "inventory",
        "severity": severity,
        "title": "Low inventory stockout risk",
        "description": desc,
        "evidence": evidence,
        "confidence": "high",
    }


def diagnose_shelf_capacity(
    shelf_capacity_units: Optional[Union[int, float]] = None,
    shelf_stock_units: Optional[Union[int, float]] = None,
    proposed_additional_units: Optional[Union[int, float]] = None,
    backroom_stock_units: Optional[Union[int, float]] = None,
) -> Optional[Dict[str, Any]]:
    """
    Identify when shelf capacity prevents additional units from being placed on the shelf.

    Rules:
    - Compares shelf capacity with current shelf occupancy.
    - Does not confuse backroom stock with front-facing shelf stock.
    - Rejects negative capacity or stock with ValueError.
    """
    if shelf_capacity_units is None or shelf_stock_units is None:
        return None

    if isinstance(shelf_capacity_units, bool) or not isinstance(shelf_capacity_units, (int, float)):
        raise TypeError(f"shelf_capacity_units must be numeric, got: {type(shelf_capacity_units).__name__}")
    if isinstance(shelf_stock_units, bool) or not isinstance(shelf_stock_units, (int, float)):
        raise TypeError(f"shelf_stock_units must be numeric, got: {type(shelf_stock_units).__name__}")

    if math.isnan(shelf_capacity_units) or math.isinf(shelf_capacity_units) or shelf_capacity_units < 0:
        raise ValueError(f"shelf_capacity_units must be non-negative, got: {shelf_capacity_units}")
    if math.isnan(shelf_stock_units) or math.isinf(shelf_stock_units) or shelf_stock_units < 0:
        raise ValueError(f"shelf_stock_units must be non-negative, got: {shelf_stock_units}")

    if proposed_additional_units is not None:
        if isinstance(proposed_additional_units, bool) or not isinstance(proposed_additional_units, (int, float)):
            raise TypeError("proposed_additional_units must be numeric.")
        if proposed_additional_units < 0:
            raise ValueError(f"proposed_additional_units cannot be negative, got: {proposed_additional_units}")

    if backroom_stock_units is not None:
        if isinstance(backroom_stock_units, bool) or not isinstance(backroom_stock_units, (int, float)):
            raise TypeError("backroom_stock_units must be numeric.")
        if backroom_stock_units < 0:
            raise ValueError(f"backroom_stock_units cannot be negative, got: {backroom_stock_units}")

    available_capacity = max(0.0, float(shelf_capacity_units) - float(shelf_stock_units))
    utilization_pct = (float(shelf_stock_units) / float(shelf_capacity_units) * 100.0) if shelf_capacity_units > 0 else 100.0

    is_constrained = False
    severity = "medium"

    if shelf_stock_units >= shelf_capacity_units:
        is_constrained = True
        severity = "high" if (backroom_stock_units and backroom_stock_units > 0) else "medium"
    elif proposed_additional_units is not None and proposed_additional_units > available_capacity:
        is_constrained = True
        severity = "medium"

    if not is_constrained:
        return None

    evidence: Dict[str, Any] = {
        "shelf_capacity_units": _format_number(shelf_capacity_units),
        "shelf_stock_units": _format_number(shelf_stock_units),
        "available_shelf_capacity": _format_number(available_capacity),
        "utilization_pct": round(utilization_pct, 1),
    }
    if backroom_stock_units is not None:
        evidence["backroom_stock_units"] = _format_number(backroom_stock_units)
    if proposed_additional_units is not None:
        evidence["proposed_additional_units"] = _format_number(proposed_additional_units)

    desc = (
        f"Shelf is at 100% capacity ({shelf_stock_units}/{shelf_capacity_units} units). "
        "No additional units can be placed on display."
        if available_capacity == 0
        else f"Available shelf capacity ({available_capacity} units) is insufficient for required placement."
    )

    return {
        "code": "SHELF_CAPACITY_CONSTRAINT",
        "category": "shelf",
        "severity": severity,
        "title": "Shelf capacity constraint",
        "description": desc,
        "evidence": evidence,
        "confidence": "high",
    }


def diagnose_delayed_truck(
    planned_arrival_time: Optional[Union[str, datetime]] = None,
    estimated_arrival_time: Optional[Union[str, datetime]] = None,
    delay_minutes: Optional[Union[int, float]] = None,
    truck_id: Optional[str] = None,
) -> Optional[Dict[str, Any]]:
    """
    Identify potential replenishment delays using planned and updated estimated arrival timestamps.

    Rules:
    - Compares timestamps consistently in UTC.
    - Reports delay duration in minutes.
    - Distinguishes confirmed delays from missing delivery information.
    """
    calculated_delay: Optional[float] = None

    if planned_arrival_time is not None and estimated_arrival_time is not None:
        p_dt = _parse_timestamp(planned_arrival_time)
        e_dt = _parse_timestamp(estimated_arrival_time)
        diff_sec = (e_dt - p_dt).total_seconds()
        calculated_delay = max(0.0, diff_sec / 60.0)
    elif delay_minutes is not None:
        if isinstance(delay_minutes, bool) or not isinstance(delay_minutes, (int, float)):
            raise TypeError("delay_minutes must be numeric.")
        if delay_minutes < 0:
            raise ValueError(f"delay_minutes cannot be negative, got: {delay_minutes}")
        calculated_delay = float(delay_minutes)

    if calculated_delay is None or calculated_delay <= 0:
        return None

    if calculated_delay >= 60:
        severity = "high"
    elif calculated_delay >= 30:
        severity = "medium"
    else:
        severity = "low"

    evidence: Dict[str, Any] = {
        "delay_minutes": _format_number(calculated_delay),
    }
    if planned_arrival_time:
        evidence["planned_arrival_time"] = _parse_timestamp(planned_arrival_time).strftime("%Y-%m-%dT%H:%M:%SZ")
    if estimated_arrival_time:
        evidence["estimated_arrival_time"] = _parse_timestamp(estimated_arrival_time).strftime("%Y-%m-%dT%H:%M:%SZ")
    if truck_id:
        evidence["truck_id"] = truck_id

    return {
        "code": "DELAYED_TRUCK",
        "category": "logistics",
        "severity": severity,
        "title": "Replenishment delivery delayed",
        "description": f"Scheduled replenishment truck is delayed by {_format_number(calculated_delay)} minutes.",
        "evidence": evidence,
        "confidence": "high",
    }


def diagnose_rider_shortage(
    required_riders: Optional[Union[int, float]] = None,
    available_riders: Optional[Union[int, float]] = None,
) -> Optional[Dict[str, Any]]:
    """
    Identify potential hyper-local rider shortage from available vs required rider capacity.

    Rules:
    - Reports exact shortage count.
    - Does not infer a shortage if either field is missing.
    - Rejects negative rider values with ValueError.
    """
    if required_riders is None or available_riders is None:
        return None

    if isinstance(required_riders, bool) or not isinstance(required_riders, (int, float)):
        raise TypeError(f"required_riders must be numeric, got: {type(required_riders).__name__}")
    if isinstance(available_riders, bool) or not isinstance(available_riders, (int, float)):
        raise TypeError(f"available_riders must be numeric, got: {type(available_riders).__name__}")

    if required_riders < 0:
        raise ValueError(f"required_riders cannot be negative, got: {required_riders}")
    if available_riders < 0:
        raise ValueError(f"available_riders cannot be negative, got: {available_riders}")

    if available_riders >= required_riders:
        return None

    shortage = required_riders - available_riders
    capacity_pct = (float(available_riders) / float(required_riders) * 100.0) if required_riders > 0 else 0.0

    if shortage >= 4 or capacity_pct <= 50.0:
        severity = "high"
    elif shortage >= 2 or capacity_pct <= 75.0:
        severity = "medium"
    else:
        severity = "low"

    return {
        "code": "RIDER_SHORTAGE",
        "category": "fulfillment",
        "severity": severity,
        "title": "Hyper-local rider shortage",
        "description": (
            f"Fulfillment fleet is short by {_format_number(shortage)} riders "
            f"({available_riders} available vs {required_riders} required)."
        ),
        "evidence": {
            "required_riders": _format_number(required_riders),
            "available_riders": _format_number(available_riders),
            "shortage_count": _format_number(shortage),
            "capacity_fulfillment_pct": round(capacity_pct, 1),
        },
        "confidence": "high",
    }


# ==========================================
# Master Diagnosis Orchestrator
# ==========================================

def diagnose_inventory_problems(
    store_id: str = "STORE_007",
    sku_id: str = "SKU_COLD_DRINK_750ML",
    # Demand surge inputs
    forecast_demand: Optional[Union[int, float, Sequence[Any]]] = None,
    baseline_demand: Optional[Union[int, float]] = None,
    event_uplift: Optional[Union[int, float]] = None,
    time_interval: Optional[str] = None,
    # Inventory inputs
    current_stock: Optional[Union[int, float]] = None,
    safety_stock_threshold: Optional[Union[int, float]] = None,
    stockout_evaluation: Optional[Dict[str, Any]] = None,
    start_time: Optional[Union[str, datetime]] = None,
    # Shelf inputs
    shelf_capacity_units: Optional[Union[int, float]] = None,
    shelf_stock_units: Optional[Union[int, float]] = None,
    backroom_stock_units: Optional[Union[int, float]] = None,
    proposed_additional_units: Optional[Union[int, float]] = None,
    # Logistics / Truck inputs
    next_truck_arrival: Optional[Union[str, datetime]] = None,
    planned_truck_arrival: Optional[Union[str, datetime]] = None,
    delay_minutes: Optional[Union[int, float]] = None,
    truck_id: Optional[str] = None,
    # Fulfillment / Rider inputs
    required_riders: Optional[Union[int, float]] = None,
    available_riders: Optional[Union[int, float]] = None,
) -> Dict[str, Any]:
    """
    Run comprehensive operational diagnosis across demand, inventory, shelf, logistics, and riders.

    Features:
    - Evaluates all 5 operational problem categories independently.
    - Returns all supported diagnoses without stopping at the first.
    - Identifies primary cause without confusing correlation with causation.
    - Reports explicit data gaps for missing information.
    - Guarantees 100% JSON-serializable structured output.
    """
    diagnoses: List[Dict[str, Any]] = []
    data_gaps: List[str] = []

    # 1. Demand Surge Check
    norm_forecast_scalar: Optional[Union[int, float]] = None
    forecast_sequence: Optional[Sequence[Any]] = None
    if forecast_demand is not None:
        if isinstance(forecast_demand, (int, float)):
            norm_forecast_scalar = forecast_demand
            forecast_sequence = [forecast_demand]
        elif isinstance(forecast_demand, Sequence) and not isinstance(forecast_demand, (str, bytes)):
            forecast_sequence = forecast_demand
            first = forecast_demand[0]
            if isinstance(first, (int, float)):
                norm_forecast_scalar = first
            elif isinstance(first, dict):
                norm_forecast_scalar = first.get("final_projected_demand_units", first.get("demand"))

    if baseline_demand is None and event_uplift is None and forecast_demand is not None:
        data_gaps.append("missing_baseline_demand")

    surge_diag = diagnose_demand_surge(
        forecast_demand=norm_forecast_scalar,
        baseline_demand=baseline_demand,
        event_uplift=event_uplift,
        time_interval=time_interval,
    )
    if surge_diag:
        diagnoses.append(surge_diag)

    # 2. Low Inventory Check
    effective_truck_arrival = next_truck_arrival or planned_truck_arrival
    low_inv_diag = diagnose_low_inventory(
        current_stock=current_stock,
        forecast_demand=forecast_sequence,
        next_truck_arrival=effective_truck_arrival,
        stockout_evaluation=stockout_evaluation,
        start_time=start_time,
        safety_stock_threshold=safety_stock_threshold,
    )
    if low_inv_diag:
        diagnoses.append(low_inv_diag)

    # 3. Shelf Capacity Check
    if shelf_capacity_units is None or shelf_stock_units is None:
        if shelf_capacity_units is None and shelf_stock_units is not None:
            data_gaps.append("missing_shelf_capacity")
        elif shelf_stock_units is None and shelf_capacity_units is not None:
            data_gaps.append("missing_shelf_stock_occupancy")
    else:
        shelf_diag = diagnose_shelf_capacity(
            shelf_capacity_units=shelf_capacity_units,
            shelf_stock_units=shelf_stock_units,
            proposed_additional_units=proposed_additional_units,
            backroom_stock_units=backroom_stock_units,
        )
        if shelf_diag:
            diagnoses.append(shelf_diag)

    # 4. Delayed Truck Check
    if planned_truck_arrival is not None and next_truck_arrival is not None:
        truck_diag = diagnose_delayed_truck(
            planned_arrival_time=planned_truck_arrival,
            estimated_arrival_time=next_truck_arrival,
            delay_minutes=delay_minutes,
            truck_id=truck_id,
        )
        if truck_diag:
            diagnoses.append(truck_diag)
    elif delay_minutes is not None and delay_minutes > 0:
        truck_diag = diagnose_delayed_truck(
            delay_minutes=delay_minutes,
            truck_id=truck_id,
        )
        if truck_diag:
            diagnoses.append(truck_diag)

    # 5. Rider Shortage Check
    if required_riders is None or available_riders is None:
        if required_riders is not None or available_riders is not None:
            data_gaps.append("missing_rider_capacity_data")
    else:
        rider_diag = diagnose_rider_shortage(
            required_riders=required_riders,
            available_riders=available_riders,
        )
        if rider_diag:
            diagnoses.append(rider_diag)

    # Determine Primary Cause
    primary_cause: Optional[str] = None
    if diagnoses:
        # Severity rank weighting: critical=4, high=3, medium=2, low=1
        sev_rank = {"critical": 4, "high": 3, "medium": 2, "low": 1}
        # Root cause priority order when severity ties
        code_prio = {
            "DEMAND_SURGE": 5,
            "DELAYED_TRUCK": 4,
            "LOW_INVENTORY": 3,
            "RIDER_SHORTAGE": 2,
            "SHELF_CAPACITY_CONSTRAINT": 1,
        }

        # Sort diagnoses by (-severity_weight, -code_prio)
        sorted_diags = sorted(
            diagnoses,
            key=lambda d: (sev_rank.get(d["severity"], 0), code_prio.get(d["code"], 0)),
            reverse=True,
        )
        primary_cause = sorted_diags[0]["code"]

    return {
        "store_id": str(store_id),
        "sku_id": str(sku_id),
        "diagnoses": diagnoses,
        "primary_cause": primary_cause,
        "data_gaps": data_gaps,
    }
