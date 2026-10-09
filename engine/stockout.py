"""
PulseStock AI - Decision Engine: Stock-Out Time Prediction Module
Cypher 2026 Challenge 6 - Store 7 Stock-out Prevention & Decision Engine

Deterministic inventory trajectory projection and stock-out time prediction.
Calculates stock depletion across continuous time intervals, evaluates replenishment
truck arrival impacts, and computes pre-replenishment unmet demand.

Uses only the Python standard library. Independent of database and API frameworks.
"""

from __future__ import annotations

import math
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional, Sequence, Tuple, Union

try:
    from engine.forecast import _format_number, _parse_timestamp
except ImportError:
    from forecast import _format_number, _parse_timestamp


def _validate_stockout_inputs(
    initial_stock: Union[int, float],
    hourly_demand: Sequence[Any],
    next_truck_arrival: Optional[Union[str, datetime]] = None,
    start_time: Optional[Union[str, datetime]] = None,
) -> None:
    """Validate all numeric values, sequences, and timestamps."""
    if isinstance(initial_stock, bool) or not isinstance(initial_stock, (int, float)):
        raise TypeError(f"initial_stock must be numeric, got: {type(initial_stock).__name__}")
    if math.isnan(initial_stock) or math.isinf(initial_stock):
        raise ValueError(f"initial_stock cannot be NaN or infinite, got: {initial_stock}")
    if initial_stock < 0:
        raise ValueError(f"initial_stock cannot be negative, got: {initial_stock}")

    if not isinstance(hourly_demand, Sequence) or isinstance(hourly_demand, (str, bytes)):
        raise TypeError(f"hourly_demand must be a sequence of demand values or forecast points, got: {type(hourly_demand).__name__}")
    if len(hourly_demand) == 0:
        raise ValueError("hourly_demand sequence cannot be empty.")

    if start_time is not None:
        _parse_timestamp(start_time)

    if next_truck_arrival is not None:
        _parse_timestamp(next_truck_arrival)


def _extract_demand_intervals(
    hourly_demand: Sequence[Any],
    start_time: Optional[Union[str, datetime]] = None,
) -> List[Dict[str, Any]]:
    """
    Normalize hourly demand sequence into structured intervals:
    [{'start': datetime, 'end': datetime, 'demand': float, 'label': str}, ...]

    Convention:
    - Each interval represents 1 hour.
    - Demand is consumed uniformly across [start, end) at rate r = demand / 3600 units/second.
    """
    if start_time is not None:
        base_start = _parse_timestamp(start_time)
    else:
        # Check if first element has timestamp
        first_item = hourly_demand[0]
        if isinstance(first_item, dict) and "timestamp" in first_item and first_item["timestamp"]:
            base_start = _parse_timestamp(first_item["timestamp"])
        else:
            base_start = datetime.now(timezone.utc).replace(minute=0, second=0, microsecond=0)

    intervals: List[Dict[str, Any]] = []

    for idx, item in enumerate(hourly_demand):
        # Extract demand value
        demand_val: float
        item_start = base_start + timedelta(hours=idx)
        item_end = item_start + timedelta(hours=1)
        item_label = f"{item_start.strftime('%H:00')} - {item_end.strftime('%H:00')}"

        if isinstance(item, (int, float)) and not isinstance(item, bool):
            if math.isnan(item) or math.isinf(item):
                raise ValueError(f"Demand value at index {idx} cannot be NaN or infinite, got: {item}")
            if item < 0:
                raise ValueError(f"Demand value at index {idx} cannot be negative, got: {item}")
            demand_val = float(item)
        elif isinstance(item, dict):
            # Check for recognized keys
            found_val = None
            for key in ("final_projected_demand_units", "demand", "units", "quantity", "baseline_demand_units"):
                if key in item and item[key] is not None:
                    found_val = item[key]
                    break
            if found_val is None:
                raise ValueError(f"Demand record at index {idx} does not contain recognized demand field.")
            if isinstance(found_val, bool) or not isinstance(found_val, (int, float)):
                raise TypeError(f"Demand value at index {idx} must be numeric, got: {type(found_val).__name__}")
            if math.isnan(found_val) or math.isinf(found_val):
                raise ValueError(f"Demand value at index {idx} cannot be NaN or infinite, got: {found_val}")
            if found_val < 0:
                raise ValueError(f"Demand value at index {idx} cannot be negative, got: {found_val}")
            demand_val = float(found_val)

            # Override timestamps if provided in dictionary
            if "timestamp" in item and item["timestamp"]:
                try:
                    parsed_ts = _parse_timestamp(item["timestamp"])
                    item_start = parsed_ts
                    item_end = item_start + timedelta(hours=1)
                except Exception:
                    pass
            if "hour_label" in item and item["hour_label"]:
                item_label = str(item["hour_label"])
        else:
            raise TypeError(f"Unsupported demand element at index {idx}: {type(item).__name__}")

        intervals.append({
            "index": idx,
            "start": item_start,
            "end": item_end,
            "demand": demand_val,
            "label": item_label,
        })

    return intervals


def calculate_projected_inventory(
    initial_stock: Union[int, float],
    hourly_demand: Sequence[Any],
    start_time: Optional[Union[str, datetime]] = None,
) -> List[Dict[str, Any]]:
    """
    Calculate projected inventory trajectory over time from current stock and hourly demand.

    Inventory Calculation Rules:
    - Starts from supplied current stock.
    - Physical inventory is depleted continuously and never drops below 0.0.
    - Unmet demand is tracked separately from physical inventory.
    - Fractional demand is handled with full float precision without premature rounding.

    Returns:
        List[Dict[str, Any]]: Interval-by-interval inventory tracking records.
    """
    _validate_stockout_inputs(initial_stock, hourly_demand, start_time=start_time)
    intervals = _extract_demand_intervals(hourly_demand, start_time=start_time)

    current_stock = float(initial_stock)
    cumulative_unmet = 0.0
    projected: List[Dict[str, Any]] = []

    for inv in intervals:
        start_stock = current_stock
        demand = inv["demand"]
        interval_start: datetime = inv["start"]
        interval_end: datetime = inv["end"]
        interval_seconds = (interval_end - interval_start).total_seconds()

        stockout_in_interval = False
        stockout_timestamp: Optional[str] = None
        consumed_stock: float
        end_stock: float
        unmet_in_interval: float

        if start_stock >= demand:
            # Demand fully covered by available inventory
            consumed_stock = demand
            end_stock = start_stock - demand
            unmet_in_interval = 0.0
            if demand > 0 and end_stock == 0.0:
                # Stock runs out exactly at the end boundary
                stockout_in_interval = True
                stockout_timestamp = interval_end.strftime("%Y-%m-%dT%H:%M:%SZ")
        elif start_stock > 0:
            # Stock runs out partially through this interval
            stockout_in_interval = True
            consumed_stock = start_stock
            end_stock = 0.0
            unmet_in_interval = demand - start_stock
            fraction = start_stock / demand
            stockout_dt = interval_start + timedelta(seconds=interval_seconds * fraction)
            stockout_timestamp = stockout_dt.strftime("%Y-%m-%dT%H:%M:%SZ")
        else:
            # Stock was already 0 at start of interval
            consumed_stock = 0.0
            end_stock = 0.0
            unmet_in_interval = demand

        cumulative_unmet += unmet_in_interval
        current_stock = end_stock

        projected.append({
            "interval_index": inv["index"],
            "timestamp": interval_start.strftime("%Y-%m-%dT%H:%M:%SZ"),
            "end_timestamp": interval_end.strftime("%Y-%m-%dT%H:%M:%SZ"),
            "hour_label": inv["label"],
            "start_stock": _format_number(start_stock),
            "demand": _format_number(demand),
            "consumed_stock": _format_number(consumed_stock),
            "end_stock": _format_number(end_stock),
            "unmet_demand": _format_number(unmet_in_interval),
            "cumulative_unmet_demand": _format_number(cumulative_unmet),
            "stockout_in_interval": stockout_in_interval,
            "stockout_timestamp": stockout_timestamp,
        })

    return projected


def predict_stockout_time(
    initial_stock: Union[int, float],
    hourly_demand: Sequence[Any],
    start_time: Optional[Union[str, datetime]] = None,
) -> Dict[str, Any]:
    """
    Predict the exact timestamp and interval when stock will run out.

    Calculates the exact sub-hourly stockout time assuming uniform consumption.
    For example, with stock=6 and demand=12/hr, stockout occurs at 30 minutes.
    If demand is zero, inventory will not run out during that interval.
    If stock hits 0 exactly at an interval boundary, reports the boundary timestamp.
    If no stockout occurs within horizon, returns stockout_time=None and stockout_within_horizon=False.
    """
    _validate_stockout_inputs(initial_stock, hourly_demand, start_time=start_time)
    projected = calculate_projected_inventory(initial_stock, hourly_demand, start_time=start_time)
    intervals = _extract_demand_intervals(hourly_demand, start_time=start_time)
    base_start = intervals[0]["start"]

    if float(initial_stock) == 0.0:
        first_demand = intervals[0]["demand"]
        if first_demand > 0:
            stockout_iso = base_start.strftime("%Y-%m-%dT%H:%M:%SZ")
            return {
                "stockout_time": stockout_iso,
                "stockout_within_horizon": True,
                "minutes_until_stockout": 0,
            }
        # If stock is 0 and demand is 0, no stockout occurred because there was no unmet demand

    for item in projected:
        if item["stockout_in_interval"] and item["stockout_timestamp"]:
            stockout_iso = item["stockout_timestamp"]
            stockout_dt = _parse_timestamp(stockout_iso)
            minutes_until = max(0.0, (stockout_dt - base_start).total_seconds() / 60.0)
            return {
                "stockout_time": stockout_iso,
                "stockout_within_horizon": True,
                "minutes_until_stockout": _format_number(minutes_until),
            }

    return {
        "stockout_time": None,
        "stockout_within_horizon": False,
        "minutes_until_stockout": None,
    }


def calculate_truck_arrival_impact(
    initial_stock: Union[int, float],
    hourly_demand: Sequence[Any],
    next_truck_arrival: Union[str, datetime],
    start_time: Optional[Union[str, datetime]] = None,
) -> Dict[str, Any]:
    """
    Calculate the impact of scheduled truck replenishment on inventory depletion.

    Evaluates:
    1. Whether stock runs out before the truck arrives.
    2. Physical stock remaining at truck arrival before replenishment is unloaded.
    3. Total unmet demand accumulated before truck arrival.

    Handles sub-interval truck arrival times with exact fractional demand consumption.
    If next truck arrives beyond the forecast horizon, reports insufficient horizon (None values).
    """
    _validate_stockout_inputs(initial_stock, hourly_demand, next_truck_arrival=next_truck_arrival, start_time=start_time)
    intervals = _extract_demand_intervals(hourly_demand, start_time=start_time)
    base_start = intervals[0]["start"]
    horizon_end = intervals[-1]["end"]
    truck_dt = _parse_timestamp(next_truck_arrival)

    if truck_dt < base_start:
        raise ValueError(
            f"next_truck_arrival ({truck_dt.isoformat()}) cannot be earlier than "
            f"forecast start time ({base_start.isoformat()})."
        )

    prediction = predict_stockout_time(initial_stock, hourly_demand, start_time=start_time)
    stockout_iso = prediction["stockout_time"]
    stockout_dt = _parse_timestamp(stockout_iso) if stockout_iso else None

    # Scenario 1: Truck arrives beyond the forecast horizon
    if truck_dt > horizon_end:
        # If stockout occurred within the horizon, we know for certain stock ran out before truck arrival
        if stockout_dt is not None and stockout_dt <= horizon_end:
            return {
                "stockout_before_truck": True,
                "stock_at_truck_arrival_before_replenishment": 0,
                "unmet_demand_before_truck": None,  # Demand between horizon_end and truck_arrival is unknown
                "truck_within_horizon": False,
            }
        # Stock survived through the horizon, but truck arrives later: outcome cannot be determined
        return {
            "stockout_before_truck": None,
            "stock_at_truck_arrival_before_replenishment": None,
            "unmet_demand_before_truck": None,
            "truck_within_horizon": False,
        }

    # Scenario 2: Truck arrives within or at the horizon boundary [base_start, horizon_end]
    # Trace inventory up to exact truck arrival timestamp
    curr_stock = float(initial_stock)
    unmet_before_truck = 0.0

    for inv in intervals:
        inv_start: datetime = inv["start"]
        inv_end: datetime = inv["end"]
        inv_demand = inv["demand"]
        inv_duration_sec = (inv_end - inv_start).total_seconds()

        # If truck arrived before or at this interval's start
        if truck_dt <= inv_start:
            break

        # Calculate effective duration applicable before truck arrival
        if truck_dt >= inv_end:
            eff_fraction = 1.0
        else:
            eff_seconds = (truck_dt - inv_start).total_seconds()
            eff_fraction = max(0.0, min(1.0, eff_seconds / inv_duration_sec))

        eff_demand = inv_demand * eff_fraction

        if curr_stock >= eff_demand:
            curr_stock -= eff_demand
        elif curr_stock > 0:
            unmet_in_slot = eff_demand - curr_stock
            curr_stock = 0.0
            unmet_before_truck += unmet_in_slot
        else:
            unmet_before_truck += eff_demand

    stockout_before_truck: bool
    if stockout_dt is not None and stockout_dt < truck_dt:
        stockout_before_truck = True
    else:
        stockout_before_truck = False

    return {
        "stockout_before_truck": stockout_before_truck,
        "stock_at_truck_arrival_before_replenishment": _format_number(curr_stock),
        "unmet_demand_before_truck": _format_number(unmet_before_truck),
        "truck_within_horizon": True,
    }


def evaluate_stockout(
    initial_stock: Union[int, float],
    hourly_demand: Sequence[Any],
    next_truck_arrival: Optional[Union[str, datetime]] = None,
    start_time: Optional[Union[str, datetime]] = None,
) -> Dict[str, Any]:
    """
    Comprehensive stock-out risk evaluation for Person 1 Decision Engine.

    Produces a complete JSON-serializable dictionary with:
    - initial_stock: Starting physical inventory units
    - stockout_time: ISO 8601 UTC timestamp of predicted depletion, or None
    - stockout_within_horizon: Boolean flag whether depletion occurs in forecast horizon
    - stockout_before_truck: Boolean flag (or None if horizon insufficient)
    - next_truck_arrival: ISO 8601 UTC timestamp of next scheduled replenishment truck
    - stock_at_truck_arrival_before_replenishment: Units remaining at truck arrival, or None
    - unmet_demand_before_truck: Total lost sales units before truck arrives, or None
    - projected_inventory: Hourly trajectory records
    - forecast_horizon_end: ISO 8601 UTC timestamp of horizon end
    - status: High-level classification status code
    - assumptions: Explicit model parameters and consumption rules
    """
    _validate_stockout_inputs(initial_stock, hourly_demand, next_truck_arrival=next_truck_arrival, start_time=start_time)
    intervals = _extract_demand_intervals(hourly_demand, start_time=start_time)
    horizon_end_iso = intervals[-1]["end"].strftime("%Y-%m-%dT%H:%M:%SZ")

    projected_inventory = calculate_projected_inventory(initial_stock, hourly_demand, start_time=start_time)
    prediction = predict_stockout_time(initial_stock, hourly_demand, start_time=start_time)

    truck_arrival_iso: Optional[str] = None
    stockout_before_truck: Optional[bool] = None
    stock_at_truck: Optional[Union[int, float]] = None
    unmet_before_truck: Optional[Union[int, float]] = None
    status: str

    if next_truck_arrival is not None:
        truck_dt = _parse_timestamp(next_truck_arrival)
        truck_arrival_iso = truck_dt.strftime("%Y-%m-%dT%H:%M:%SZ")
        truck_impact = calculate_truck_arrival_impact(
            initial_stock, hourly_demand, next_truck_arrival, start_time=start_time
        )
        stockout_before_truck = truck_impact["stockout_before_truck"]
        stock_at_truck = truck_impact["stock_at_truck_arrival_before_replenishment"]
        unmet_before_truck = truck_impact["unmet_demand_before_truck"]

        if not truck_impact["truck_within_horizon"]:
            if stockout_before_truck is True:
                status = "STOCKOUT_BEFORE_TRUCK_HORIZON_EXCEEDED"
            else:
                status = "INSUFFICIENT_HORIZON_FOR_TRUCK"
        elif stockout_before_truck:
            status = "STOCKOUT_BEFORE_TRUCK"
        else:
            status = "SAFE_UNTIL_TRUCK"
    else:
        if prediction["stockout_within_horizon"]:
            status = "STOCKOUT_PREDICTED"
        else:
            status = "NO_STOCKOUT_WITHIN_HORIZON"

    assumptions = {
        "consumption_rate": "UNIFORM_HOURLY",
        "consumption_description": "Hourly demand is assumed to be consumed at a constant uniform rate within each 1-hour interval.",
        "timezone": "UTC",
        "time_boundary_convention": "HALF_OPEN_INTERVAL_[START, END)",
        "depletion_sequence": "AVAILABLE_STOCK",
        "replenishment_source": "SCHEDULED_TRUCK" if next_truck_arrival else "NONE",
    }

    return {
        "initial_stock": _format_number(initial_stock),
        "stockout_time": prediction["stockout_time"],
        "stockout_within_horizon": prediction["stockout_within_horizon"],
        "stockout_before_truck": stockout_before_truck,
        "next_truck_arrival": truck_arrival_iso,
        "stock_at_truck_arrival_before_replenishment": stock_at_truck,
        "unmet_demand_before_truck": unmet_before_truck,
        "projected_inventory": projected_inventory,
        "forecast_horizon_end": horizon_end_iso,
        "status": status,
        "assumptions": assumptions,
    }
