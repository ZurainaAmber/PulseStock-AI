"""
PulseStock AI - Decision Engine: Action Simulation and Comparison Module
Cypher 2026 Challenge 6 - Store 7 Stock-out Prevention & Decision Engine

Deterministic simulation of alternative inventory interventions against a common
no-action baseline. Evaluates:
1. Inter-store inventory transfers (Task 4 logic)
2. Expedited / earlier warehouse trucks
3. Shelf-space swaps (Task 5 logic)
4. Wait baseline (Tasks 1 & 2 logic)
5. Sensible combinations (e.g., Transfer + Shelf Swap)

Produces consistent, comparable metrics (protected units, unmet demand, ETA, costs,
data gaps) for downstream financial evaluation (Task 7) and recommendation ranking (Task 8).

Uses only the Python standard library. Independent of database and API frameworks.
"""

from __future__ import annotations

import math
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional, Sequence, Tuple, Union

try:
    from engine.forecast import _format_number, _parse_timestamp
    from engine.stockout import (
        _extract_demand_intervals,
        _validate_stockout_inputs,
        calculate_projected_inventory,
        evaluate_stockout,
        predict_stockout_time,
    )
    from engine.transfer import (
        calculate_safe_donor_surplus,
        calculate_target_requirement,
        calculate_transfer_quantity,
        evaluate_donor_candidate,
    )
    from engine.constraints import (
        calculate_available_shelf_capacity,
        evaluate_shelf_and_transfer_feasibility,
        evaluate_shelf_swap,
        validate_direct_placement,
    )
except ImportError:
    from forecast import _format_number, _parse_timestamp
    from stockout import (
        _extract_demand_intervals,
        _validate_stockout_inputs,
        calculate_projected_inventory,
        evaluate_stockout,
        predict_stockout_time,
    )
    from transfer import (
        calculate_safe_donor_surplus,
        calculate_target_requirement,
        calculate_transfer_quantity,
        evaluate_donor_candidate,
    )
    from constraints import (
        calculate_available_shelf_capacity,
        evaluate_shelf_and_transfer_feasibility,
        evaluate_shelf_swap,
        validate_direct_placement,
    )


def _validate_non_negative_number(val: Any, name: str) -> None:
    """Validate that a value is numeric, not boolean, not NaN/Inf, and >= 0."""
    if val is not None:
        if isinstance(val, bool) or not isinstance(val, (int, float)):
            raise TypeError(f"{name} must be numeric, got: {type(val).__name__}")
        if math.isnan(val) or math.isinf(val):
            raise ValueError(f"{name} cannot be NaN or infinite, got: {val}")
        if val < 0:
            raise ValueError(f"{name} cannot be negative, got: {val}")


def simulate_inventory_trajectory(
    initial_stock: Union[int, float],
    hourly_demand: Sequence[Any],
    injections: Optional[Sequence[Dict[str, Any]]] = None,
    start_time: Optional[Union[str, datetime]] = None,
) -> Dict[str, Any]:
    """
    Simulate deterministic inventory trajectory across time intervals with mid-horizon arrivals.

    Rules:
    - Reuses Task 2 demand interval extraction and uniform hourly consumption.
    - Accurately applies stock injections at their exact arrival timestamps.
    - Transferred or replenished stock is NEVER available before arrival time.
    - Past unmet demand occurring before an injection is NEVER retroactively reversed.
    - Correctly calculates sub-hourly stockout times and cumulative unmet demand.
    - Rejects negative initial stock, negative demand, and negative injection quantities.
    """
    _validate_stockout_inputs(initial_stock, hourly_demand, start_time=start_time)
    intervals = _extract_demand_intervals(hourly_demand, start_time=start_time)

    base_start: datetime = intervals[0]["start"]
    horizon_end: datetime = intervals[-1]["end"]

    # Validate and normalize injections: list of {'timestamp': datetime, 'quantity': float}
    parsed_injections: List[Dict[str, Any]] = []
    if injections:
        for idx, inj in enumerate(injections):
            if not isinstance(inj, dict):
                raise TypeError(f"Injection at index {idx} must be a dictionary.")
            qty = inj.get("quantity", inj.get("units", inj.get("quantity_units")))
            _validate_non_negative_number(qty, f"Injection[{idx}] quantity")
            if qty is None:
                raise ValueError(f"Injection[{idx}] missing quantity field.")

            ts = inj.get("timestamp", inj.get("arrival_time"))
            if ts is None:
                raise ValueError(f"Injection[{idx}] missing timestamp field.")
            inj_dt = _parse_timestamp(ts)

            parsed_injections.append({
                "timestamp": inj_dt,
                "quantity": float(qty),
                "label": inj.get("label", f"INJECTION_{idx}"),
            })

    # Sort injections chronologically
    parsed_injections.sort(key=lambda x: x["timestamp"])

    current_stock = float(initial_stock)
    cumulative_unmet = 0.0
    first_stockout_dt: Optional[datetime] = None

    # Injections before or at base_start are applied immediately at start
    early_injections = [inj for inj in parsed_injections if inj["timestamp"] <= base_start]
    for inj in early_injections:
        current_stock += inj["quantity"]

    projected: List[Dict[str, Any]] = []

    for inv in intervals:
        inv_start: datetime = inv["start"]
        inv_end: datetime = inv["end"]
        inv_demand = float(inv["demand"])
        inv_duration_sec = (inv_end - inv_start).total_seconds()
        demand_rate = inv_demand / inv_duration_sec if inv_duration_sec > 0 else 0.0

        # Injections within this interval: inv_start < inj_dt < inv_end
        # Note: injections exactly at inv_start (if not base_start) are applied at segment 0
        interval_injections = [
            inj for inj in parsed_injections
            if inv_start < inj["timestamp"] < inv_end
            or (inj["timestamp"] == inv_start and inv_start > base_start)
        ]

        # Any injection exactly at inv_start
        for inj in interval_injections:
            if inj["timestamp"] == inv_start:
                current_stock += inj["quantity"]

        mid_injections = [inj for inj in interval_injections if inj["timestamp"] > inv_start]

        start_stock_for_interval = current_stock
        stockout_in_interval = False
        stockout_timestamp_str: Optional[str] = None
        consumed_in_interval = 0.0
        unmet_in_interval = 0.0

        # Construct time checkpoints within the interval: [inv_start, t1, t2, ..., inv_end]
        time_checkpoints: List[Tuple[datetime, Optional[Dict[str, Any]]]] = [(inv_start, None)]
        for inj in mid_injections:
            time_checkpoints.append((inj["timestamp"], inj))
        time_checkpoints.append((inv_end, None))

        for seg_idx in range(len(time_checkpoints) - 1):
            t_seg_start, _ = time_checkpoints[seg_idx]
            t_seg_end, next_inj = time_checkpoints[seg_idx + 1]

            seg_seconds = (t_seg_end - t_seg_start).total_seconds()
            if seg_seconds <= 0:
                continue

            seg_demand = demand_rate * seg_seconds

            if current_stock >= seg_demand:
                current_stock -= seg_demand
                consumed_in_interval += seg_demand
                if seg_demand > 0 and current_stock == 0.0:
                    stockout_in_interval = True
                    if stockout_timestamp_str is None:
                        stockout_timestamp_str = t_seg_end.strftime("%Y-%m-%dT%H:%M:%SZ")
                    if first_stockout_dt is None:
                        first_stockout_dt = t_seg_end
            elif current_stock > 0:
                stockout_in_interval = True
                consumed_seg = current_stock
                unmet_seg = seg_demand - current_stock
                frac = current_stock / seg_demand if seg_demand > 0 else 0.0
                exact_stockout_dt = t_seg_start + timedelta(seconds=seg_seconds * frac)
                if stockout_timestamp_str is None:
                    stockout_timestamp_str = exact_stockout_dt.strftime("%Y-%m-%dT%H:%M:%SZ")
                if first_stockout_dt is None:
                    first_stockout_dt = exact_stockout_dt
                consumed_in_interval += consumed_seg
                unmet_in_interval += unmet_seg
                current_stock = 0.0
            else:
                # current_stock == 0
                stockout_in_interval = True
                if stockout_timestamp_str is None and seg_demand > 0:
                    stockout_timestamp_str = t_seg_start.strftime("%Y-%m-%dT%H:%M:%SZ")
                if first_stockout_dt is None and seg_demand > 0:
                    first_stockout_dt = t_seg_start
                unmet_in_interval += seg_demand

            # Apply injection arriving at t_seg_end if present
            if next_inj is not None:
                current_stock += next_inj["quantity"]

        cumulative_unmet += unmet_in_interval

        projected.append({
            "interval_index": inv["index"],
            "timestamp": inv_start.strftime("%Y-%m-%dT%H:%M:%SZ"),
            "end_timestamp": inv_end.strftime("%Y-%m-%dT%H:%M:%SZ"),
            "hour_label": inv["label"],
            "start_stock": _format_number(start_stock_for_interval),
            "demand": _format_number(inv_demand),
            "consumed_stock": _format_number(consumed_in_interval),
            "end_stock": _format_number(current_stock),
            "unmet_demand": _format_number(unmet_in_interval),
            "cumulative_unmet_demand": _format_number(cumulative_unmet),
            "stockout_in_interval": stockout_in_interval,
            "stockout_timestamp": stockout_timestamp_str,
        })

    first_stockout_iso = first_stockout_dt.strftime("%Y-%m-%dT%H:%M:%SZ") if first_stockout_dt else None

    return {
        "initial_stock": _format_number(initial_stock),
        "final_stock": _format_number(current_stock),
        "expected_unmet_demand": _format_number(cumulative_unmet),
        "first_stockout_time": first_stockout_iso,
        "stockout_within_horizon": first_stockout_dt is not None,
        "projected_inventory": projected,
        "forecast_horizon_start": base_start.strftime("%Y-%m-%dT%H:%M:%SZ"),
        "forecast_horizon_end": horizon_end.strftime("%Y-%m-%dT%H:%M:%SZ"),
    }


def simulate_wait_baseline(
    initial_stock: Union[int, float],
    hourly_demand: Sequence[Any],
    scheduled_truck: Optional[Dict[str, Any]] = None,
    shelf_capacity: Optional[Union[int, float]] = None,
    current_occupancy: Optional[Union[int, float]] = None,
    start_time: Optional[Union[str, datetime]] = None,
    action_id: str = "wait_baseline",
) -> Dict[str, Any]:
    """
    Establish the consistent baseline (WAIT / no-intervention scenario).

    Reuses Tasks 1 & 2 forecasting and stock-out calculations.
    Includes:
    - Current inventory.
    - Hourly forecast demand.
    - Predicted stock-out time.
    - Expected unmet demand.
    - Next scheduled replenishment arrival (if provided).
    - Relevant inventory constraints (shelf capacity).
    """
    _validate_stockout_inputs(initial_stock, hourly_demand, start_time=start_time)
    _validate_non_negative_number(shelf_capacity, "shelf_capacity")
    _validate_non_negative_number(current_occupancy, "current_occupancy")

    scheduled_arrival_iso: Optional[str] = None
    injections: List[Dict[str, Any]] = []

    if scheduled_truck:
        sched_arr = scheduled_truck.get("scheduled_arrival_time") or scheduled_truck.get("arrival_time") or scheduled_truck.get("eta")
        sched_qty = scheduled_truck.get("allocated_quantity_units", scheduled_truck.get("quantity", 0))
        if sched_arr:
            dt = _parse_timestamp(sched_arr)
            scheduled_arrival_iso = dt.strftime("%Y-%m-%dT%H:%M:%SZ")
            if sched_qty > 0:
                injections.append({"timestamp": dt, "quantity": float(sched_qty), "label": "SCHEDULED_TRUCK"})

    # Simulate baseline trajectory
    sim_result = simulate_inventory_trajectory(
        initial_stock=initial_stock,
        hourly_demand=hourly_demand,
        injections=injections,
        start_time=start_time,
    )

    unmet_demand = sim_result["expected_unmet_demand"]
    stockout_time = sim_result["first_stockout_time"]

    constraints_info: Dict[str, Any] = {}
    if shelf_capacity is not None:
        occ = current_occupancy if current_occupancy is not None else initial_stock
        cap_info = calculate_available_shelf_capacity(shelf_capacity, occ)
        constraints_info = {
            "shelf_capacity": _format_number(shelf_capacity),
            "current_occupancy": _format_number(occ),
            "available_shelf_capacity": cap_info["available_shelf_capacity"],
        }

    return {
        "action_id": action_id,
        "action_type": "WAIT",
        "feasible": True,
        "expected_unmet_demand": _format_number(unmet_demand),
        "protected_units": 0,
        "current_inventory": _format_number(initial_stock),
        "predicted_stockout_time": stockout_time,
        "next_replenishment_arrival": scheduled_arrival_iso,
        "relevant_constraints": constraints_info,
        "remaining_stock": sim_result["final_stock"],
        "projected_inventory": sim_result["projected_inventory"],
        "assumptions": [
            "Baseline scenario: no operational intervention taken.",
            "Demand follows uniform hourly consumption without interventions.",
        ],
        "infeasibility_reasons": [],
    }


def simulate_transfer_action(
    initial_stock: Union[int, float],
    hourly_demand: Sequence[Any],
    donor: Dict[str, Any],
    target_store_id: str = "STORE_007",
    sku_id: str = "SKU_COLD_DRINK_750ML",
    target_required_quantity: Optional[Union[int, float]] = None,
    max_vehicle_capacity: Optional[Union[int, float]] = None,
    min_transfer_quantity: Optional[Union[int, float]] = None,
    shelf_capacity: Optional[Union[int, float]] = None,
    current_occupancy: Optional[Union[int, float]] = None,
    start_time: Optional[Union[str, datetime]] = None,
    baseline_unmet_demand: Optional[Union[int, float]] = None,
    action_id: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Simulate an inter-store inventory transfer from a donor store.

    Uses Task 4 transfer feasibility logic:
    - Validates donor safe surplus and donor safety (preventing donor stock-out).
    - Respects target requirement and vehicle/rider capacity.
    - Respects transfer arrival time; stock is never available before arrival.
    - Recalculates target inventory and unmet demand after transfer arrives.
    - Does not reverse unmet demand that occurred before arrival.
    - If transfer ETA is missing, reports missing ETA explicitly without assuming zero travel time.
    - If transfer cost is missing, reports missing cost explicitly without assuming zero cost.
    """
    _validate_stockout_inputs(initial_stock, hourly_demand, start_time=start_time)
    intervals = _extract_demand_intervals(hourly_demand, start_time=start_time)
    base_start = intervals[0]["start"]

    donor_id = str(donor.get("donor_store_id") or donor.get("store_id") or "UNKNOWN_DONOR")
    donor_sku = str(donor.get("sku_id") or sku_id)
    cand_id = action_id or f"transfer_{donor_id.lower()}"

    infeasibility_reasons: List[str] = []
    assumptions: List[str] = []
    data_gaps: List[str] = []

    # 1. Target cannot donate to itself
    if donor_id == target_store_id:
        infeasibility_reasons.append("Target store cannot be its own donor.")

    # 2. SKU check
    if donor_sku != sku_id:
        infeasibility_reasons.append(f"SKU mismatch: donor stocks '{donor_sku}' but target needs '{sku_id}'.")

    # 3. Donor safe surplus calculation (Task 4)
    has_replenishment = donor.get("has_replenishment_data", True)
    donor_stock = donor.get("current_stock", donor.get("current_stock_units", 0))
    donor_demand = donor.get("projected_demand", donor.get("projected_donor_demand"))
    safety_stock = donor.get("safety_stock", donor.get("required_safety_stock", 0))
    reserved_stock = donor.get("reserved_stock", 0)

    # Check if explicit safe_surplus is already provided or needs calculation
    if "safe_surplus" in donor:
        safe_surplus = donor["safe_surplus"]
        is_safe = donor.get("is_safe", safe_surplus > 0)
        _validate_non_negative_number(safe_surplus, "donor.safe_surplus")
    else:
        surplus_eval = calculate_safe_donor_surplus(
            current_stock=donor_stock,
            projected_demand=donor_demand,
            safety_stock=safety_stock,
            reserved_stock=reserved_stock,
            has_replenishment_data=has_replenishment,
        )
        safe_surplus = surplus_eval["safe_surplus"]
        is_safe = surplus_eval["is_safe"]
        if surplus_eval["uncertainty_reason"]:
            data_gaps.append(f"donor_{surplus_eval['uncertainty_reason']}")

    if not is_safe or safe_surplus <= 0:
        infeasibility_reasons.append(
            f"Donor store '{donor_id}' has 0 safe surplus units (unsafe donor)."
        )

    # 4. Target requirement
    total_demand = sum(float(inv["demand"]) for inv in intervals)
    if target_required_quantity is None:
        req_eval = calculate_target_requirement(
            current_stock=initial_stock,
            projected_demand=total_demand,
        )
        target_need = req_eval["target_required_quantity"]
    else:
        _validate_non_negative_number(target_required_quantity, "target_required_quantity")
        target_need = float(target_required_quantity)

    # 5. Feasible transfer quantity
    qty_eval = calculate_transfer_quantity(
        target_required_quantity=target_need,
        safe_surplus=safe_surplus,
        max_vehicle_capacity=max_vehicle_capacity,
        min_transfer_quantity=min_transfer_quantity,
    )
    transfer_qty = qty_eval["transfer_quantity"]

    if not qty_eval["is_feasible"]:
        if qty_eval["infeasibility_reason"] and qty_eval["infeasibility_reason"] not in infeasibility_reasons:
            infeasibility_reasons.append(qty_eval["infeasibility_reason"])

    # 6. Physical shelf capacity check at target store
    if shelf_capacity is not None and transfer_qty > 0:
        occ = current_occupancy if current_occupancy is not None else initial_stock
        cap_eval = calculate_available_shelf_capacity(shelf_capacity, occ)
        avail_units = cap_eval["available_units"]
        if transfer_qty > avail_units:
            assumptions.append(
                f"Proposed transfer quantity ({transfer_qty}) exceeds direct shelf capacity ({avail_units} units available). "
                f"Requires shelf swap or backroom storage to fit."
            )

    # 7. Transfer ETA / arrival time
    estimated_arrival_iso: Optional[str] = None
    arrival_dt: Optional[datetime] = None

    raw_eta_min = donor.get("transfer_eta_minutes", donor.get("eta_minutes"))
    raw_arrival = donor.get("estimated_arrival_time", donor.get("arrival_time"))

    if raw_arrival is not None:
        arrival_dt = _parse_timestamp(raw_arrival)
        estimated_arrival_iso = arrival_dt.strftime("%Y-%m-%dT%H:%M:%SZ")
    elif raw_eta_min is not None:
        _validate_non_negative_number(raw_eta_min, "transfer_eta_minutes")
        arrival_dt = base_start + timedelta(minutes=float(raw_eta_min))
        estimated_arrival_iso = arrival_dt.strftime("%Y-%m-%dT%H:%M:%SZ")
    else:
        # Unknown ETA: do not assume zero travel time
        data_gaps.append("missing_transfer_eta")
        infeasibility_reasons.append("Transfer ETA is unknown; travel time cannot be assumed to be zero.")
        assumptions.append("Transfer ETA is missing; cannot determine when stock becomes available.")

    # 8. Known intervention cost
    raw_cost = donor.get("estimated_transfer_cost_inr", donor.get("transfer_cost_inr", donor.get("cost")))
    known_cost: Optional[float] = None
    if raw_cost is not None:
        _validate_non_negative_number(raw_cost, "transfer_cost")
        known_cost = float(raw_cost)
    else:
        data_gaps.append("missing_transfer_cost")
        assumptions.append("Transfer cost is unknown and was not assumed to be zero.")

    # 9. Feasibility determination
    is_feasible = (len(infeasibility_reasons) == 0) and (transfer_qty > 0) and (arrival_dt is not None)

    # Calculate baseline unmet demand if not provided
    if baseline_unmet_demand is None:
        base_res = simulate_wait_baseline(initial_stock, hourly_demand, start_time=start_time)
        base_unmet = float(base_res["expected_unmet_demand"])
    else:
        _validate_non_negative_number(baseline_unmet_demand, "baseline_unmet_demand")
        base_unmet = float(baseline_unmet_demand)

    # 10. Simulation trajectory
    if is_feasible and arrival_dt is not None:
        injections = [{"timestamp": arrival_dt, "quantity": transfer_qty, "label": f"TRANSFER_{donor_id}"}]
        sim_result = simulate_inventory_trajectory(
            initial_stock=initial_stock,
            hourly_demand=hourly_demand,
            injections=injections,
            start_time=start_time,
        )
        cand_unmet = float(sim_result["expected_unmet_demand"])
        protected_units = max(0.0, base_unmet - cand_unmet)
        protected_units = min(protected_units, base_unmet)
        remaining_stock = sim_result["final_stock"]
        projected_inv = sim_result["projected_inventory"]
    else:
        cand_unmet = base_unmet
        protected_units = 0.0
        remaining_stock = _format_number(initial_stock)
        projected_inv = []

    return {
        "action_id": cand_id,
        "action_type": "TRANSFER",
        "feasible": is_feasible,
        "expected_unmet_demand": _format_number(cand_unmet),
        "protected_units": _format_number(protected_units),
        "estimated_arrival_time": estimated_arrival_iso,
        "known_intervention_cost": known_cost,
        "transfer_quantity": _format_number(transfer_qty),
        "donor_store_id": donor_id,
        "remaining_stock": remaining_stock,
        "assumptions": assumptions,
        "infeasibility_reasons": infeasibility_reasons,
        "data_gaps": data_gaps,
        "projected_inventory": projected_inv,
    }


def simulate_early_truck_action(
    initial_stock: Union[int, float],
    hourly_demand: Sequence[Any],
    truck: Dict[str, Any],
    target_store_id: str = "STORE_007",
    sku_id: str = "SKU_COLD_DRINK_750ML",
    warehouse: Optional[Dict[str, Any]] = None,
    shelf_capacity: Optional[Union[int, float]] = None,
    current_occupancy: Optional[Union[int, float]] = None,
    start_time: Optional[Union[str, datetime]] = None,
    baseline_unmet_demand: Optional[Union[int, float]] = None,
    action_id: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Simulate an expedited or earlier warehouse replenishment truck.

    Verifies:
    - Truck can serve the target store.
    - Relevant warehouse stock and truck capacity are sufficient.
    - Proposed earlier ETA is genuinely earlier than the scheduled ETA.
    - Does not invent an achievable earlier arrival time when data is missing.
    - Recalculates target inventory and unmet demand starting from arrival time.
    - Includes known expediting cost without substituting zero for missing cost.
    """
    _validate_stockout_inputs(initial_stock, hourly_demand, start_time=start_time)
    intervals = _extract_demand_intervals(hourly_demand, start_time=start_time)
    base_start = intervals[0]["start"]

    truck_id = str(truck.get("truck_id") or "TRK_EXPEDITED")
    truck_store_id = truck.get("store_id") or truck.get("destination_store_id")
    cand_id = action_id or f"early_truck_{truck_id.lower()}"

    infeasibility_reasons: List[str] = []
    assumptions: List[str] = []
    data_gaps: List[str] = []

    # 1. Target store check
    if truck_store_id is not None and str(truck_store_id) != target_store_id:
        infeasibility_reasons.append(
            f"Truck '{truck_id}' is assigned to {truck_store_id}, cannot serve target {target_store_id}."
        )

    # 2. Replenishment quantity
    raw_qty = truck.get("allocated_quantity_units", truck.get("quantity", truck.get("replenishment_quantity")))
    if raw_qty is None:
        infeasibility_reasons.append("Replenishment quantity is not specified for early truck.")
        replenish_qty = 0.0
    else:
        _validate_non_negative_number(raw_qty, "replenishment_quantity")
        replenish_qty = float(raw_qty)
        if replenish_qty <= 0:
            infeasibility_reasons.append("Replenishment quantity must be strictly greater than 0.")

    # 3. Warehouse stock verification
    wh_stock = None
    if warehouse:
        wh_stock = warehouse.get("available_stock_units", warehouse.get("available_stock", warehouse.get("free_stock_units")))
    elif "warehouse_stock_units" in truck:
        wh_stock = truck["warehouse_stock_units"]

    if wh_stock is not None:
        _validate_non_negative_number(wh_stock, "warehouse_stock")
        if float(wh_stock) < replenish_qty:
            infeasibility_reasons.append(
                f"Insufficient warehouse stock: available {wh_stock} < required {replenish_qty} units."
            )

    # 4. Truck capacity verification
    truck_cap = truck.get("truck_capacity_units", truck.get("truck_capacity", truck.get("capacity")))
    if truck_cap is not None:
        _validate_non_negative_number(truck_cap, "truck_capacity")
        if float(truck_cap) < replenish_qty:
            infeasibility_reasons.append(
                f"Insufficient truck capacity: capacity {truck_cap} < allocated {replenish_qty} units."
            )

    # 5. Earlier arrival verification
    early_arr_iso: Optional[str] = None
    early_arr_dt: Optional[datetime] = None

    raw_early_arr = truck.get("earlier_arrival_time", truck.get("expedited_arrival_time", truck.get("earlier_arrival")))
    raw_early_min = truck.get("expedited_eta_minutes", truck.get("earlier_eta_minutes"))

    if raw_early_arr is not None:
        early_arr_dt = _parse_timestamp(raw_early_arr)
        early_arr_iso = early_arr_dt.strftime("%Y-%m-%dT%H:%M:%SZ")
    elif raw_early_min is not None:
        _validate_non_negative_number(raw_early_min, "expedited_eta_minutes")
        early_arr_dt = base_start + timedelta(minutes=float(raw_early_min))
        early_arr_iso = early_arr_dt.strftime("%Y-%m-%dT%H:%M:%SZ")
    else:
        data_gaps.append("missing_early_truck_eta")
        infeasibility_reasons.append("Early truck arrival time is unknown; cannot invent an achievable earlier arrival time.")
        assumptions.append("Achievable earlier truck arrival is uncertain; cannot establish feasibility.")

    # Compare with scheduled truck arrival
    raw_sched_arr = truck.get("scheduled_arrival_time", truck.get("scheduled_arrival"))
    raw_sched_min = truck.get("scheduled_truck_eta_minutes")

    if early_arr_dt is not None:
        sched_dt: Optional[datetime] = None
        if raw_sched_arr is not None:
            sched_dt = _parse_timestamp(raw_sched_arr)
        elif raw_sched_min is not None:
            sched_dt = base_start + timedelta(minutes=float(raw_sched_min))

        if sched_dt is not None and early_arr_dt >= sched_dt:
            infeasibility_reasons.append(
                f"Proposed earlier truck arrival ({early_arr_iso}) is not earlier than scheduled arrival ({sched_dt.strftime('%Y-%m-%dT%H:%M:%SZ')})."
            )

    # 6. Known expediting cost
    raw_cost = truck.get("expedited_cost_inr", truck.get("expediting_cost", truck.get("cost")))
    known_cost: Optional[float] = None
    if raw_cost is not None:
        _validate_non_negative_number(raw_cost, "expedited_cost")
        known_cost = float(raw_cost)
    else:
        data_gaps.append("missing_expediting_cost")
        assumptions.append("Expediting cost is unknown and was not assumed to be zero.")

    # 7. Shelf capacity awareness
    if shelf_capacity is not None and replenish_qty > 0:
        occ = current_occupancy if current_occupancy is not None else initial_stock
        cap_eval = calculate_available_shelf_capacity(shelf_capacity, occ)
        avail_units = cap_eval["available_units"]
        if replenish_qty > avail_units:
            assumptions.append(
                f"Truck replenishment quantity ({replenish_qty}) exceeds direct shelf capacity ({avail_units} units available). "
                f"Requires shelf swap or backroom storage."
            )

    # 8. Feasibility determination
    is_feasible = (len(infeasibility_reasons) == 0) and (replenish_qty > 0) and (early_arr_dt is not None)

    # Baseline unmet demand
    if baseline_unmet_demand is None:
        base_res = simulate_wait_baseline(initial_stock, hourly_demand, start_time=start_time)
        base_unmet = float(base_res["expected_unmet_demand"])
    else:
        _validate_non_negative_number(baseline_unmet_demand, "baseline_unmet_demand")
        base_unmet = float(baseline_unmet_demand)

    # 9. Simulation
    if is_feasible and early_arr_dt is not None:
        injections = [{"timestamp": early_arr_dt, "quantity": replenish_qty, "label": f"EARLY_TRUCK_{truck_id}"}]
        sim_result = simulate_inventory_trajectory(
            initial_stock=initial_stock,
            hourly_demand=hourly_demand,
            injections=injections,
            start_time=start_time,
        )
        cand_unmet = float(sim_result["expected_unmet_demand"])
        protected_units = max(0.0, base_unmet - cand_unmet)
        protected_units = min(protected_units, base_unmet)
        remaining_stock = sim_result["final_stock"]
        projected_inv = sim_result["projected_inventory"]
    else:
        cand_unmet = base_unmet
        protected_units = 0.0
        remaining_stock = _format_number(initial_stock)
        projected_inv = []

    return {
        "action_id": cand_id,
        "action_type": "EARLIER_TRUCK",
        "feasible": is_feasible,
        "expected_unmet_demand": _format_number(cand_unmet),
        "protected_units": _format_number(protected_units),
        "estimated_arrival_time": early_arr_iso,
        "known_intervention_cost": known_cost,
        "replenishment_quantity": _format_number(replenish_qty),
        "truck_id": truck_id,
        "remaining_stock": remaining_stock,
        "assumptions": assumptions,
        "infeasibility_reasons": infeasibility_reasons,
        "data_gaps": data_gaps,
        "projected_inventory": projected_inv,
    }


def simulate_shelf_swap_action(
    initial_stock: Union[int, float],
    hourly_demand: Sequence[Any],
    shelf_capacity: Union[int, float],
    current_occupancy: Union[int, float],
    existing_shelf_products: Sequence[Dict[str, Any]],
    target_sku_id: str = "SKU_COLD_DRINK_750ML",
    needed_space: Optional[Union[int, float]] = None,
    swap_labor_cost: Optional[Union[int, float]] = None,
    start_time: Optional[Union[str, datetime]] = None,
    baseline_unmet_demand: Optional[Union[int, float]] = None,
    action_id: str = "shelf_swap_action",
) -> Dict[str, Any]:
    """
    Simulate a standalone shelf-swap action using Task 5 constraints.

    Rules:
    - Verifies physical feasibility, movable flags, and alternative storage capacity.
    - CRITICAL: A shelf swap does NOT create or destroy inventory.
    - Rearranging shelf space alone does NOT increase total inventory or fulfill demand
      unless incoming or backroom stock is placed onto the freed space.
    - Standalone shelf swap preserves baseline unmet demand (protected_units = 0).
    - Rejects swaps that violate compatibility or storage constraints.
    """
    _validate_stockout_inputs(initial_stock, hourly_demand, start_time=start_time)
    _validate_non_negative_number(shelf_capacity, "shelf_capacity")
    _validate_non_negative_number(current_occupancy, "current_occupancy")
    _validate_non_negative_number(needed_space, "needed_space")
    _validate_non_negative_number(swap_labor_cost, "swap_labor_cost")

    target_needed_space = float(needed_space) if needed_space is not None else 1.0

    swap_eval = evaluate_shelf_swap(
        shelf_capacity=shelf_capacity,
        current_occupancy=current_occupancy,
        target_sku_id=target_sku_id,
        needed_space=target_needed_space,
        existing_shelf_products=existing_shelf_products,
    )

    is_feasible = swap_eval["shelf_swap_possible"]
    infeasibility_reasons = list(swap_eval["infeasibility_reasons"])
    data_gaps: List[str] = []
    assumptions: List[str] = [
        "Shelf swap reallocates customer display slots; it does not create or destroy physical inventory.",
        "Total sellable inventory is unchanged; standalone shelf swap protects 0 units of unmet demand.",
    ]

    known_cost: Optional[float] = None
    if swap_labor_cost is not None:
        known_cost = float(swap_labor_cost)
    else:
        # If cost not provided, report gap
        data_gaps.append("missing_shelf_swap_cost")
        assumptions.append("Shelf swap labor cost is unknown and was not assumed to be zero.")

    if baseline_unmet_demand is None:
        base_res = simulate_wait_baseline(initial_stock, hourly_demand, start_time=start_time)
        base_unmet = float(base_res["expected_unmet_demand"])
    else:
        _validate_non_negative_number(baseline_unmet_demand, "baseline_unmet_demand")
        base_unmet = float(baseline_unmet_demand)

    return {
        "action_id": action_id,
        "action_type": "SHELF_SWAP",
        "feasible": is_feasible,
        "expected_unmet_demand": _format_number(base_unmet),
        "protected_units": 0,
        "estimated_arrival_time": None,  # Shelf swap is internal store execution
        "known_intervention_cost": known_cost,
        "space_freed": swap_eval["space_freed"],
        "needed_space": swap_eval["needed_space"],
        "products_moved": swap_eval["products_moved"],
        "remaining_stock": _format_number(initial_stock),
        "assumptions": assumptions,
        "infeasibility_reasons": infeasibility_reasons,
        "data_gaps": data_gaps,
        "projected_inventory": [],
    }


def simulate_combined_action(
    combination_type: str,
    initial_stock: Union[int, float],
    hourly_demand: Sequence[Any],
    transfer_donor: Optional[Dict[str, Any]] = None,
    truck_candidate: Optional[Dict[str, Any]] = None,
    shelf_capacity: Optional[Union[int, float]] = None,
    current_occupancy: Optional[Union[int, float]] = None,
    existing_shelf_products: Optional[Sequence[Dict[str, Any]]] = None,
    target_store_id: str = "STORE_007",
    sku_id: str = "SKU_COLD_DRINK_750ML",
    warehouse: Optional[Dict[str, Any]] = None,
    shelf_swap_cost: Optional[Union[int, float]] = None,
    start_time: Optional[Union[str, datetime]] = None,
    baseline_unmet_demand: Optional[Union[int, float]] = None,
    action_id: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Simulate sensible combinations of interventions.

    Supported combinations:
    1. TRANSFER_AND_SHELF_SWAP:
       Transferred stock arrives from a donor store, but exceeds available shelf space.
       Shelf swap moves lower-priority items to alternative storage to accommodate incoming transfer.
    2. EARLIER_TRUCK_AND_SHELF_SWAP:
       Expedited truck arrives, but incoming stock exceeds available shelf space.
       Shelf swap frees required display space.

    Rules:
    - Every component must be verified for feasibility.
    - If any mandatory component is infeasible, the entire combination is marked infeasible.
    - Avoids double-counting inventory or costs.
    - Respects arrival times and sequential dependencies.
    """
    _validate_stockout_inputs(initial_stock, hourly_demand, start_time=start_time)
    _validate_non_negative_number(shelf_capacity, "shelf_capacity")
    _validate_non_negative_number(current_occupancy, "current_occupancy")

    if combination_type not in ("TRANSFER_AND_SHELF_SWAP", "EARLIER_TRUCK_AND_SHELF_SWAP"):
        raise ValueError(
            f"Unsupported combination_type: '{combination_type}'. "
            "Supported: 'TRANSFER_AND_SHELF_SWAP', 'EARLIER_TRUCK_AND_SHELF_SWAP'."
        )

    cand_id = action_id or f"combined_{combination_type.lower()}"
    infeasibility_reasons: List[str] = []
    assumptions: List[str] = []
    data_gaps: List[str] = []

    combined_injections: List[Dict[str, Any]] = []
    total_cost: Optional[float] = None
    arrival_time_iso: Optional[str] = None

    if combination_type == "TRANSFER_AND_SHELF_SWAP":
        if not transfer_donor:
            raise ValueError("transfer_donor is required for TRANSFER_AND_SHELF_SWAP.")

        # 1. Evaluate transfer candidate component
        trans_res = simulate_transfer_action(
            initial_stock=initial_stock,
            hourly_demand=hourly_demand,
            donor=transfer_donor,
            target_store_id=target_store_id,
            sku_id=sku_id,
            shelf_capacity=None,  # Checked below in combination
            start_time=start_time,
            baseline_unmet_demand=baseline_unmet_demand,
        )

        infeasibility_reasons.extend(trans_res["infeasibility_reasons"])
        data_gaps.extend(trans_res["data_gaps"])
        assumptions.extend(trans_res["assumptions"])
        arrival_time_iso = trans_res["estimated_arrival_time"]
        transfer_qty = float(trans_res["transfer_quantity"])

        # 2. Evaluate shelf swap component to accommodate transfer
        if shelf_capacity is not None:
            occ = float(current_occupancy) if current_occupancy is not None else float(initial_stock)
            cap_eval = calculate_available_shelf_capacity(shelf_capacity, occ)
            avail_units = float(cap_eval["available_units"])

            if transfer_qty > avail_units:
                space_needed = transfer_qty - avail_units
                if existing_shelf_products is None:
                    infeasibility_reasons.append("Shelf swap is required to fit transfer, but existing shelf products were not supplied.")
                else:
                    swap_eval = evaluate_shelf_swap(
                        shelf_capacity=shelf_capacity,
                        current_occupancy=occ,
                        target_sku_id=sku_id,
                        needed_space=space_needed,
                        existing_shelf_products=existing_shelf_products,
                    )
                    if not swap_eval["shelf_swap_possible"]:
                        infeasibility_reasons.extend(swap_eval["infeasibility_reasons"])
                    else:
                        assumptions.append(
                            f"Shelf swap successfully frees {swap_eval['space_freed']} units of display space "
                            f"to accommodate {transfer_qty} incoming transferred units."
                        )

        # Combine costs
        trans_cost = trans_res["known_intervention_cost"]
        if trans_cost is not None and shelf_swap_cost is not None:
            total_cost = trans_cost + float(shelf_swap_cost)
        elif trans_cost is not None:
            total_cost = trans_cost
            data_gaps.append("missing_shelf_swap_cost")
        elif shelf_swap_cost is not None:
            total_cost = float(shelf_swap_cost)
        else:
            total_cost = None

        if arrival_time_iso and transfer_qty > 0:
            combined_injections.append({
                "timestamp": _parse_timestamp(arrival_time_iso),
                "quantity": transfer_qty,
                "label": "COMBINED_TRANSFER",
            })

    elif combination_type == "EARLIER_TRUCK_AND_SHELF_SWAP":
        if not truck_candidate:
            raise ValueError("truck_candidate is required for EARLIER_TRUCK_AND_SHELF_SWAP.")

        # 1. Evaluate truck component
        truck_res = simulate_early_truck_action(
            initial_stock=initial_stock,
            hourly_demand=hourly_demand,
            truck=truck_candidate,
            target_store_id=target_store_id,
            sku_id=sku_id,
            warehouse=warehouse,
            shelf_capacity=None,
            start_time=start_time,
            baseline_unmet_demand=baseline_unmet_demand,
        )

        infeasibility_reasons.extend(truck_res["infeasibility_reasons"])
        data_gaps.extend(truck_res["data_gaps"])
        assumptions.extend(truck_res["assumptions"])
        arrival_time_iso = truck_res["estimated_arrival_time"]
        replenish_qty = float(truck_res["replenishment_quantity"])

        # 2. Evaluate shelf swap component to accommodate replenishment
        if shelf_capacity is not None:
            occ = float(current_occupancy) if current_occupancy is not None else float(initial_stock)
            cap_eval = calculate_available_shelf_capacity(shelf_capacity, occ)
            avail_units = float(cap_eval["available_units"])

            if replenish_qty > avail_units:
                space_needed = replenish_qty - avail_units
                if existing_shelf_products is None:
                    infeasibility_reasons.append("Shelf swap is required to fit truck stock, but existing shelf products were not supplied.")
                else:
                    swap_eval = evaluate_shelf_swap(
                        shelf_capacity=shelf_capacity,
                        current_occupancy=occ,
                        target_sku_id=sku_id,
                        needed_space=space_needed,
                        existing_shelf_products=existing_shelf_products,
                    )
                    if not swap_eval["shelf_swap_possible"]:
                        infeasibility_reasons.extend(swap_eval["infeasibility_reasons"])
                    else:
                        assumptions.append(
                            f"Shelf swap successfully frees {swap_eval['space_freed']} units of display space "
                            f"to accommodate {replenish_qty} truck replenishment units."
                        )

        # Combine costs
        truck_cost = truck_res["known_intervention_cost"]
        if truck_cost is not None and shelf_swap_cost is not None:
            total_cost = truck_cost + float(shelf_swap_cost)
        elif truck_cost is not None:
            total_cost = truck_cost
            data_gaps.append("missing_shelf_swap_cost")
        elif shelf_swap_cost is not None:
            total_cost = float(shelf_swap_cost)
        else:
            total_cost = None

        if arrival_time_iso and replenish_qty > 0:
            combined_injections.append({
                "timestamp": _parse_timestamp(arrival_time_iso),
                "quantity": replenish_qty,
                "label": "COMBINED_EARLY_TRUCK",
            })

    is_feasible = (len(infeasibility_reasons) == 0) and (len(combined_injections) > 0)

    # Baseline unmet demand
    if baseline_unmet_demand is None:
        base_res = simulate_wait_baseline(initial_stock, hourly_demand, start_time=start_time)
        base_unmet = float(base_res["expected_unmet_demand"])
    else:
        _validate_non_negative_number(baseline_unmet_demand, "baseline_unmet_demand")
        base_unmet = float(baseline_unmet_demand)

    if is_feasible and combined_injections:
        sim_result = simulate_inventory_trajectory(
            initial_stock=initial_stock,
            hourly_demand=hourly_demand,
            injections=combined_injections,
            start_time=start_time,
        )
        cand_unmet = float(sim_result["expected_unmet_demand"])
        protected_units = max(0.0, base_unmet - cand_unmet)
        protected_units = min(protected_units, base_unmet)
        remaining_stock = sim_result["final_stock"]
        projected_inv = sim_result["projected_inventory"]
    else:
        cand_unmet = base_unmet
        protected_units = 0.0
        remaining_stock = _format_number(initial_stock)
        projected_inv = []

    return {
        "action_id": cand_id,
        "action_type": combination_type,
        "feasible": is_feasible,
        "expected_unmet_demand": _format_number(cand_unmet),
        "protected_units": _format_number(protected_units),
        "estimated_arrival_time": arrival_time_iso,
        "known_intervention_cost": total_cost,
        "remaining_stock": remaining_stock,
        "assumptions": assumptions,
        "infeasibility_reasons": infeasibility_reasons,
        "data_gaps": list(set(data_gaps)),
        "projected_inventory": projected_inv,
    }


def simulate_and_compare_actions(
    initial_stock: Union[int, float],
    hourly_demand: Sequence[Any],
    scheduled_truck: Optional[Dict[str, Any]] = None,
    donor_candidates: Optional[Sequence[Dict[str, Any]]] = None,
    early_truck_candidates: Optional[Sequence[Dict[str, Any]]] = None,
    shelf_data: Optional[Dict[str, Any]] = None,
    target_store_id: str = "STORE_007",
    sku_id: str = "SKU_COLD_DRINK_750ML",
    warehouse: Optional[Dict[str, Any]] = None,
    max_vehicle_capacity: Optional[Union[int, float]] = None,
    start_time: Optional[Union[str, datetime]] = None,
    scenario_id: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Simulate and compare all alternative inventory interventions against the common baseline.

    Master orchestrator:
    - Calculates baseline (WAIT) outcome.
    - Evaluates each candidate independently using the same initial scenario.
    - Computes protected units consistently as baseline_unmet - candidate_unmet.
    - Identifies plausible combinations (e.g., Transfer + Shelf Swap).
    - Collects data gaps and returns structured JSON-serializable dictionary.
    - Does NOT select or rank the final best action (deferred to Task 8).
    """
    _validate_stockout_inputs(initial_stock, hourly_demand, start_time=start_time)

    scenario_label = scenario_id or "scenario_store_stockout_comparison"

    shelf_cap = None
    curr_occ = None
    existing_prods = None

    if shelf_data:
        shelf_cap = shelf_data.get("shelf_capacity_units", shelf_data.get("shelf_capacity"))
        curr_occ = shelf_data.get("current_shelf_occupancy", shelf_data.get("current_occupancy"))
        existing_prods = shelf_data.get("existing_shelf_products", shelf_data.get("products", []))

    # 1. Baseline simulation (WAIT)
    baseline = simulate_wait_baseline(
        initial_stock=initial_stock,
        hourly_demand=hourly_demand,
        scheduled_truck=scheduled_truck,
        shelf_capacity=shelf_cap,
        current_occupancy=curr_occ,
        start_time=start_time,
    )
    base_unmet = float(baseline["expected_unmet_demand"])

    candidates: List[Dict[str, Any]] = []
    all_data_gaps: List[str] = []

    # 2. Simulate Transfer candidates
    if donor_candidates:
        for idx, donor in enumerate(donor_candidates):
            t_res = simulate_transfer_action(
                initial_stock=initial_stock,
                hourly_demand=hourly_demand,
                donor=donor,
                target_store_id=target_store_id,
                sku_id=sku_id,
                max_vehicle_capacity=max_vehicle_capacity,
                shelf_capacity=shelf_cap,
                current_occupancy=curr_occ,
                start_time=start_time,
                baseline_unmet_demand=base_unmet,
                action_id=f"transfer_{donor.get('donor_store_id', donor.get('store_id', idx)).lower()}",
            )
            candidates.append(t_res)
            all_data_gaps.extend(t_res["data_gaps"])

    # 3. Simulate Early Truck candidates
    if early_truck_candidates:
        for idx, truck in enumerate(early_truck_candidates):
            trk_res = simulate_early_truck_action(
                initial_stock=initial_stock,
                hourly_demand=hourly_demand,
                truck=truck,
                target_store_id=target_store_id,
                sku_id=sku_id,
                warehouse=warehouse,
                shelf_capacity=shelf_cap,
                current_occupancy=curr_occ,
                start_time=start_time,
                baseline_unmet_demand=base_unmet,
                action_id=f"early_truck_{truck.get('truck_id', idx).lower()}",
            )
            candidates.append(trk_res)
            all_data_gaps.extend(trk_res["data_gaps"])

    # 4. Simulate Shelf Swap candidate (standalone)
    if shelf_cap is not None and existing_prods is not None and len(existing_prods) > 0:
        swap_res = simulate_shelf_swap_action(
            initial_stock=initial_stock,
            hourly_demand=hourly_demand,
            shelf_capacity=shelf_cap,
            current_occupancy=curr_occ if curr_occ is not None else initial_stock,
            existing_shelf_products=existing_prods,
            target_sku_id=sku_id,
            start_time=start_time,
            baseline_unmet_demand=base_unmet,
        )
        candidates.append(swap_res)
        all_data_gaps.extend(swap_res["data_gaps"])

    # 5. Simulate Sensible Combinations: TRANSFER_AND_SHELF_SWAP
    # Evaluated when a donor exists whose transfer would exceed direct shelf capacity
    if donor_candidates and shelf_cap is not None and existing_prods is not None:
        occ = float(curr_occ) if curr_occ is not None else float(initial_stock)
        avail_space = float(shelf_cap) - occ
        for donor in donor_candidates:
            # Check if this donor candidate needs additional shelf space
            donor_surplus = donor.get("safe_surplus", donor.get("current_stock", 0))
            if donor_surplus > avail_space:
                comb_res = simulate_combined_action(
                    combination_type="TRANSFER_AND_SHELF_SWAP",
                    initial_stock=initial_stock,
                    hourly_demand=hourly_demand,
                    transfer_donor=donor,
                    shelf_capacity=shelf_cap,
                    current_occupancy=curr_occ,
                    existing_shelf_products=existing_prods,
                    target_store_id=target_store_id,
                    sku_id=sku_id,
                    start_time=start_time,
                    baseline_unmet_demand=base_unmet,
                    action_id=f"combined_transfer_swap_{donor.get('donor_store_id', donor.get('store_id', 'donor')).lower()}",
                )
                candidates.append(comb_res)
                all_data_gaps.extend(comb_res["data_gaps"])
                break  # Generate only sensible primary combination

    # Deduplicate data gaps
    unique_data_gaps = sorted(list(set(all_data_gaps)))

    # Determine comparison status
    if len(unique_data_gaps) == 0:
        comparison_status = "complete"
    else:
        comparison_status = "partial"

    # Clean candidate dictionaries for structured return conforming to Section 9
    clean_candidates: List[Dict[str, Any]] = []
    for cand in candidates:
        clean_candidates.append({
            "action_id": cand["action_id"],
            "action_type": cand["action_type"],
            "feasible": cand["feasible"],
            "expected_unmet_demand": cand["expected_unmet_demand"],
            "protected_units": cand["protected_units"],
            "estimated_arrival_time": cand["estimated_arrival_time"],
            "known_intervention_cost": cand["known_intervention_cost"],
            "remaining_stock": cand.get("remaining_stock"),
            "assumptions": cand["assumptions"],
            "infeasibility_reasons": cand["infeasibility_reasons"],
        })

    return {
        "scenario_id": scenario_label,
        "baseline": {
            "action_type": baseline["action_type"],
            "feasible": baseline["feasible"],
            "expected_unmet_demand": baseline["expected_unmet_demand"],
            "current_inventory": baseline["current_inventory"],
            "predicted_stockout_time": baseline["predicted_stockout_time"],
            "next_replenishment_arrival": baseline["next_replenishment_arrival"],
        },
        "candidates": clean_candidates,
        "comparison_status": comparison_status,
        "data_gaps": unique_data_gaps,
    }
