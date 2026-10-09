"""
PulseStock AI - Decision Engine: Store Inventory Transfer Logic Module
Cypher 2026 Challenge 6 - Store 7 Stock-out Prevention & Decision Engine

Deterministic inter-store inventory balancing and donor store evaluation.
Calculates safe donor surplus, target store net requirements, vehicle/rider
transfer quantity constraints, and multi-donor candidate ranking.

Uses only the Python standard library. Independent of database and API frameworks.
"""

from __future__ import annotations

import math
from typing import Any, Dict, List, Optional, Sequence, Union

try:
    from engine.forecast import _format_number
except ImportError:
    from forecast import _format_number


def _validate_non_negative_number(val: Any, name: str) -> None:
    """Validate that a value is numeric, not boolean, not NaN/Inf, and >= 0."""
    if val is not None:
        if isinstance(val, bool) or not isinstance(val, (int, float)):
            raise TypeError(f"{name} must be numeric, got: {type(val).__name__}")
        if math.isnan(val) or math.isinf(val):
            raise ValueError(f"{name} cannot be NaN or infinite, got: {val}")
        if val < 0:
            raise ValueError(f"{name} cannot be negative, got: {val}")


def calculate_safe_donor_surplus(
    current_stock: Union[int, float],
    projected_demand: Optional[Union[int, float]],
    safety_stock: Union[int, float] = 0,
    reserved_stock: Union[int, float] = 0,
    has_replenishment_data: bool = True,
    inventory_scope: str = "TOTAL_AVAILABLE",
) -> Dict[str, Any]:
    """
    Calculate the safe surplus a donor store can transfer without risking a stockout.

    Formula:
    safe donor surplus = max(0, current_donor_stock - reserved_stock - projected_demand - safety_stock)

    Rules:
    - Uses donor's own demand forecast, not target's forecast.
    - If demand or replenishment data is missing/uncertain, marks donor as uncertain and ineligible.
    - Surplus is floored at 0 (never negative).
    - Rejects negative inputs with ValueError.
    """
    _validate_non_negative_number(current_stock, "current_stock")
    _validate_non_negative_number(projected_demand, "projected_demand")
    _validate_non_negative_number(safety_stock, "safety_stock")
    _validate_non_negative_number(reserved_stock, "reserved_stock")

    # Incomplete donor demand or replenishment data
    if projected_demand is None or not has_replenishment_data:
        reason = "missing_projected_demand" if projected_demand is None else "missing_replenishment_schedule"
        return {
            "safe_surplus": 0,
            "is_safe": False,
            "current_stock": _format_number(current_stock),
            "projected_demand": None,
            "safety_stock": _format_number(safety_stock),
            "reserved_stock": _format_number(reserved_stock),
            "uncertainty_reason": reason,
            "inventory_scope": inventory_scope,
        }

    available_stock = max(0.0, float(current_stock) - float(reserved_stock))
    required_retention = float(projected_demand) + float(safety_stock)
    raw_surplus = available_stock - required_retention
    safe_surplus = max(0.0, raw_surplus)

    return {
        "safe_surplus": _format_number(safe_surplus),
        "is_safe": safe_surplus > 0,
        "current_stock": _format_number(current_stock),
        "projected_demand": _format_number(projected_demand),
        "safety_stock": _format_number(safety_stock),
        "reserved_stock": _format_number(reserved_stock),
        "uncertainty_reason": None,
        "inventory_scope": inventory_scope,
    }


def calculate_target_requirement(
    current_stock: Union[int, float],
    projected_demand: Union[int, float],
    safety_stock: Union[int, float] = 0,
    in_transit_stock: Union[int, float] = 0,
) -> Dict[str, Any]:
    """
    Calculate how much additional stock the target store requires until its next replenishment.

    Formula:
    target requirement = max(0, (projected_demand + safety_stock) - (current_stock + in_transit_stock))

    Considers:
    - Current target stock.
    - Forecast demand until next replenishment.
    - Desired safety stock.
    - Confirmed in-transit inventory (avoids double-counting).
    """
    _validate_non_negative_number(current_stock, "current_stock")
    _validate_non_negative_number(projected_demand, "projected_demand")
    _validate_non_negative_number(safety_stock, "safety_stock")
    _validate_non_negative_number(in_transit_stock, "in_transit_stock")

    total_needed = float(projected_demand) + float(safety_stock)
    total_available = float(current_stock) + float(in_transit_stock)
    deficit = total_needed - total_available
    required_quantity = max(0.0, deficit)

    return {
        "target_required_quantity": _format_number(required_quantity),
        "needs_transfer": required_quantity > 0,
        "projected_demand": _format_number(projected_demand),
        "current_stock": _format_number(current_stock),
        "safety_stock": _format_number(safety_stock),
        "in_transit_stock": _format_number(in_transit_stock),
    }


def calculate_transfer_quantity(
    target_required_quantity: Union[int, float],
    safe_surplus: Union[int, float],
    max_vehicle_capacity: Optional[Union[int, float]] = None,
    min_transfer_quantity: Optional[Union[int, float]] = None,
    indivisible_units: bool = True,
) -> Dict[str, Any]:
    """
    Determine the feasible transfer quantity bounded by target need, donor surplus,
    vehicle capacity, and packaging constraints.

    Rules:
    - Never exceeds target need or donor surplus.
    - Never exceeds vehicle / rider capacity.
    - Must satisfy minimum transfer quantity threshold if configured.
    - Returns whole numbers if units are indivisible.
    """
    _validate_non_negative_number(target_required_quantity, "target_required_quantity")
    _validate_non_negative_number(safe_surplus, "safe_surplus")
    _validate_non_negative_number(max_vehicle_capacity, "max_vehicle_capacity")
    _validate_non_negative_number(min_transfer_quantity, "min_transfer_quantity")

    if target_required_quantity <= 0:
        return {
            "transfer_quantity": 0,
            "remaining_shortage": 0,
            "donor_surplus_remaining": _format_number(safe_surplus),
            "is_feasible": False,
            "infeasibility_reason": "Target store requires 0 units.",
        }

    if safe_surplus <= 0:
        return {
            "transfer_quantity": 0,
            "remaining_shortage": _format_number(target_required_quantity),
            "donor_surplus_remaining": 0,
            "is_feasible": False,
            "infeasibility_reason": "Donor has 0 safe surplus units.",
        }

    # Constrained by target need and donor surplus
    feasible_qty = min(float(target_required_quantity), float(safe_surplus))

    # Constrained by vehicle / rider capacity
    if max_vehicle_capacity is not None:
        feasible_qty = min(feasible_qty, float(max_vehicle_capacity))

    # Whole unit rounding if indivisible
    if indivisible_units:
        feasible_qty = math.floor(feasible_qty)

    # Check minimum transfer quantity threshold
    if min_transfer_quantity is not None and feasible_qty < min_transfer_quantity:
        return {
            "transfer_quantity": 0,
            "remaining_shortage": _format_number(target_required_quantity),
            "donor_surplus_remaining": _format_number(safe_surplus),
            "is_feasible": False,
            "infeasibility_reason": (
                f"Transfer quantity ({feasible_qty}) is below configured "
                f"minimum batch size ({min_transfer_quantity})."
            ),
        }

    if feasible_qty <= 0:
        return {
            "transfer_quantity": 0,
            "remaining_shortage": _format_number(target_required_quantity),
            "donor_surplus_remaining": _format_number(safe_surplus),
            "is_feasible": False,
            "infeasibility_reason": "Transfer quantity is zero after applying operational constraints.",
        }

    remaining_shortage = max(0.0, float(target_required_quantity) - feasible_qty)
    donor_surplus_remaining = max(0.0, float(safe_surplus) - feasible_qty)

    return {
        "transfer_quantity": _format_number(feasible_qty),
        "remaining_shortage": _format_number(remaining_shortage),
        "donor_surplus_remaining": _format_number(donor_surplus_remaining),
        "is_feasible": True,
        "infeasibility_reason": None,
    }


def evaluate_donor_candidate(
    donor: Dict[str, Any],
    target_store_id: str,
    sku_id: str,
    target_required_quantity: Union[int, float],
    max_vehicle_capacity: Optional[Union[int, float]] = None,
    min_transfer_quantity: Optional[Union[int, float]] = None,
) -> Dict[str, Any]:
    """
    Evaluate a single donor store candidate for a target store and SKU.

    Validates:
    - Target != Donor (same store check).
    - SKU compatibility.
    - Safe surplus availability.
    - Capacity and travel parameters.
    """
    donor_id = str(donor.get("donor_store_id") or donor.get("store_id") or "UNKNOWN_DONOR")
    donor_sku = str(donor.get("sku_id") or sku_id)
    infeasibility_reasons: List[str] = []

    # 1. Target cannot donate to itself
    if donor_id == target_store_id:
        infeasibility_reasons.append("Target store cannot be its own donor.")

    # 2. SKU compatibility check
    if donor_sku != sku_id:
        infeasibility_reasons.append(f"SKU mismatch: donor stocks '{donor_sku}' but target needs '{sku_id}'.")

    # 3. Extract inventory and forecast metrics
    donor_stock = donor.get("current_stock")
    if donor_stock is None:
        donor_stock = donor.get("current_stock_units")

    # Check if explicit surplus is already provided or needs calculation
    projected_demand = donor.get("projected_demand") or donor.get("projected_donor_demand")
    safety_stock = donor.get("safety_stock", donor.get("required_safety_stock", 0))
    reserved_stock = donor.get("reserved_stock", 0)
    has_replenishment = donor.get("has_replenishment_data", True)

    safe_surplus_val: float = 0.0

    if "surplus_units" in donor and projected_demand is None:
        # Pre-calculated surplus supplied in donor record
        safe_surplus_val = float(donor["surplus_units"])
        donor_stock_val = float(donor_stock) if donor_stock is not None else safe_surplus_val
        projected_demand_val = None
        safety_stock_val = float(safety_stock)
    else:
        # Calculate surplus from scratch
        if donor_stock is None:
            infeasibility_reasons.append("Donor current stock information is missing.")
            donor_stock_val = None
        else:
            donor_stock_val = float(donor_stock)

        if projected_demand is None or not has_replenishment:
            infeasibility_reasons.append(
                "Missing donor demand or replenishment data; cannot safely establish surplus."
            )
            projected_demand_val = None
            safety_stock_val = float(safety_stock)
        else:
            projected_demand_val = float(projected_demand)
            safety_stock_val = float(safety_stock)
            surplus_calc = calculate_safe_donor_surplus(
                current_stock=donor_stock_val,
                projected_demand=projected_demand_val,
                safety_stock=safety_stock_val,
                reserved_stock=float(reserved_stock),
                has_replenishment_data=has_replenishment,
            )
            safe_surplus_val = float(surplus_calc["safe_surplus"])

    # 4. Safe surplus sufficiency check
    if safe_surplus_val <= 0 and not infeasibility_reasons:
        infeasibility_reasons.append(
            f"Donor has zero safe surplus (Stock: {donor_stock_val}, Needed: {projected_demand_val} + {safety_stock_val})."
        )

    # 5. Calculate feasible transfer quantity
    max_transfer_qty = 0
    if not infeasibility_reasons and safe_surplus_val > 0:
        qty_res = calculate_transfer_quantity(
            target_required_quantity=target_required_quantity,
            safe_surplus=safe_surplus_val,
            max_vehicle_capacity=max_vehicle_capacity,
            min_transfer_quantity=min_transfer_quantity,
        )
        if qty_res["is_feasible"]:
            max_transfer_qty = qty_res["transfer_quantity"]
        else:
            infeasibility_reasons.append(qty_res["infeasibility_reason"] or "Zero feasible transfer quantity.")

    is_feasible = len(infeasibility_reasons) == 0 and max_transfer_qty > 0

    # Operational logistics attributes
    eta_mins = donor.get("transfer_eta_minutes", donor.get("estimated_eta_minutes"))
    cost = donor.get("estimated_transfer_cost_inr", donor.get("estimated_transfer_cost"))
    distance = donor.get("distance_km")

    return {
        "donor_store_id": donor_id,
        "target_store_id": target_store_id,
        "sku_id": sku_id,
        "current_donor_stock": _format_number(donor_stock_val) if donor_stock_val is not None else None,
        "projected_donor_demand": _format_number(projected_demand_val) if projected_demand_val is not None else None,
        "required_safety_stock": _format_number(safety_stock_val) if safety_stock_val is not None else 0,
        "safe_surplus": _format_number(safe_surplus_val),
        "target_required_quantity": _format_number(target_required_quantity),
        "maximum_transfer_quantity": _format_number(max_transfer_qty),
        "estimated_eta_minutes": _format_number(eta_mins) if eta_mins is not None else None,
        "estimated_transfer_cost": _format_number(cost) if cost is not None else None,
        "distance_km": _format_number(distance) if distance is not None else None,
        "feasible": is_feasible,
        "infeasibility_reasons": infeasibility_reasons,
        "assumptions": {
            "inventory_scope": "TOTAL_AVAILABLE",
            "indivisible_units": True,
            "replenishment_verified": has_replenishment,
        },
    }


def evaluate_and_rank_donors(
    target_store_id: str,
    sku_id: str,
    target_stock: Optional[Union[int, float]] = None,
    target_demand: Optional[Union[int, float]] = None,
    target_safety_stock: Union[int, float] = 0,
    target_in_transit: Union[int, float] = 0,
    target_required_quantity: Optional[Union[int, float]] = None,
    donor_candidates: Sequence[Dict[str, Any]] = (),
    max_vehicle_capacity: Optional[Union[int, float]] = None,
    min_transfer_quantity: Optional[Union[int, float]] = None,
) -> Dict[str, Any]:
    """
    Evaluate multiple candidate donor stores and rank feasible options.

    Ranking Criteria:
    1. Feasibility: Feasible donors always rank ahead of infeasible candidates.
    2. Fulfillment: Higher transfer quantity (satisfies more of the target requirement).
    3. Delivery Speed: Lower estimated ETA (minutes).
    4. Cost: Lower transfer cost.
    5. Proximity: Lower distance in km.

    Returns:
        Structured JSON-serializable dictionary with evaluated candidates and recommended donor.
    """
    # 1. Determine target store net requirement
    if target_required_quantity is not None:
        _validate_non_negative_number(target_required_quantity, "target_required_quantity")
        req_qty = float(target_required_quantity)
    elif target_stock is not None and target_demand is not None:
        target_calc = calculate_target_requirement(
            current_stock=target_stock,
            projected_demand=target_demand,
            safety_stock=target_safety_stock,
            in_transit_stock=target_in_transit,
        )
        req_qty = float(target_calc["target_required_quantity"])
    else:
        req_qty = 0.0

    if not isinstance(donor_candidates, Sequence) or isinstance(donor_candidates, (str, bytes)):
        raise TypeError("donor_candidates must be a sequence of donor dictionaries.")

    # 2. Evaluate each candidate
    evaluated_candidates: List[Dict[str, Any]] = []
    for cand in donor_candidates:
        if not isinstance(cand, dict):
            raise TypeError("Each donor candidate must be a dictionary.")
        eval_item = evaluate_donor_candidate(
            donor=cand,
            target_store_id=target_store_id,
            sku_id=sku_id,
            target_required_quantity=req_qty,
            max_vehicle_capacity=max_vehicle_capacity,
            min_transfer_quantity=min_transfer_quantity,
        )
        evaluated_candidates.append(eval_item)

    # 3. Transparent multi-criteria ranking
    # Sort key: (-feasible, -quantity_transferred, eta, cost, distance)
    def donor_sort_key(d: Dict[str, Any]) -> tuple:
        is_feasible_int = 1 if d["feasible"] else 0
        transfer_qty = float(d["maximum_transfer_quantity"] or 0)
        eta = float(d["estimated_eta_minutes"]) if d["estimated_eta_minutes"] is not None else 9999.0
        cost = float(d["estimated_transfer_cost"]) if d["estimated_transfer_cost"] is not None else 9999.0
        dist = float(d["distance_km"]) if d["distance_km"] is not None else 9999.0
        return (-is_feasible_int, -transfer_qty, eta, cost, dist)

    ranked_candidates = sorted(evaluated_candidates, key=donor_sort_key)

    # 4. Determine status and recommendation
    feasible_candidates = [d for d in ranked_candidates if d["feasible"]]
    recommended_donor: Optional[Dict[str, Any]] = None
    recommended_qty: Optional[Union[int, float]] = None
    status: str

    if req_qty <= 0 and (target_stock is not None or target_required_quantity == 0):
        status = "TARGET_STOCK_SUFFICIENT"
    elif len(feasible_candidates) > 0:
        recommended_donor = feasible_candidates[0]
        recommended_qty = recommended_donor["maximum_transfer_quantity"]
        status = "TRANSFER_RECOMMENDED"
    elif len(donor_candidates) > 0:
        status = "NO_FEASIBLE_DONOR"
    else:
        status = "NO_CANDIDATES_SUPPLIED"

    return {
        "target_store_id": str(target_store_id),
        "sku_id": str(sku_id),
        "target_required_quantity": _format_number(req_qty),
        "candidates": ranked_candidates,
        "recommended_donor": recommended_donor,
        "recommended_transfer_quantity": recommended_qty,
        "status": status,
        "assumptions": {
            "ranking_strategy": "FEASIBILITY_FULFILLMENT_ETA_COST",
            "unit_divisibility": "INTEGER_UNITS",
            "rider_capacity_applied": max_vehicle_capacity is not None,
        },
    }
