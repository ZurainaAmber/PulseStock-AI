"""
PulseStock AI - Decision Engine: Shelf-Space Constraints & Shelf-Swap Feasibility Module
Cypher 2026 Challenge 6 - Store 7 Stock-out Prevention & Decision Engine

Deterministic evaluation of physical shelf capacity, direct placement limits,
and shelf-swap feasibility. Prevents stock allocations that exceed physical
customer display capacity and coordinates displaced product storage.

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


def calculate_available_shelf_capacity(
    shelf_capacity: Union[int, float],
    current_occupancy: Union[int, float],
    slots_per_unit: Union[int, float] = 1,
) -> Dict[str, Any]:
    """
    Calculate available shelf capacity and unit placement potential.

    Formula:
    available capacity = shelf_capacity - current_occupancy

    Rules:
    - Capacity and occupancy must be non-negative.
    - Rejects current_occupancy > shelf_capacity with ValueError.
    - Accounts for slots_per_unit when products consume multiple shelf slots.
    """
    _validate_non_negative_number(shelf_capacity, "shelf_capacity")
    _validate_non_negative_number(current_occupancy, "current_occupancy")
    _validate_non_negative_number(slots_per_unit, "slots_per_unit")

    if slots_per_unit <= 0:
        raise ValueError(f"slots_per_unit must be strictly positive (> 0), got: {slots_per_unit}")

    if current_occupancy > shelf_capacity:
        raise ValueError(
            f"current_occupancy ({current_occupancy}) cannot exceed shelf_capacity ({shelf_capacity})."
        )

    available_space = max(0.0, float(shelf_capacity) - float(current_occupancy))
    available_units = math.floor(available_space / float(slots_per_unit))
    utilization_pct = (float(current_occupancy) / float(shelf_capacity) * 100.0) if shelf_capacity > 0 else 100.0

    return {
        "shelf_capacity": _format_number(shelf_capacity),
        "current_occupancy": _format_number(current_occupancy),
        "available_shelf_capacity": _format_number(available_space),
        "available_units": _format_number(available_units),
        "slots_per_unit": _format_number(slots_per_unit),
        "utilization_pct": round(utilization_pct, 1),
        "is_full": available_space == 0,
    }


def validate_direct_placement(
    shelf_capacity: Union[int, float],
    current_occupancy: Union[int, float],
    proposed_quantity: Union[int, float],
    slots_per_unit: Union[int, float] = 1,
    backroom_capacity: Optional[Union[int, float]] = None,
    current_backroom_occupancy: Optional[Union[int, float]] = None,
) -> Dict[str, Any]:
    """
    Validate whether a proposed quantity can be placed directly on the shelf.

    Rules:
    - Calculates maximum quantity that fits on customer shelf directly.
    - Never silently claims all units fit when only partial fits.
    - Tracks overflow and backroom placement separately.
    - Rejects negative inputs with ValueError.
    """
    _validate_non_negative_number(proposed_quantity, "proposed_quantity")
    cap_info = calculate_available_shelf_capacity(shelf_capacity, current_occupancy, slots_per_unit)
    available_units = cap_info["available_units"]

    proposed_val = float(proposed_quantity)
    direct_placement_qty = min(proposed_val, float(available_units))
    unplaced_qty = max(0.0, proposed_val - direct_placement_qty)

    direct_feasible = (proposed_val <= available_units) and (proposed_val > 0)
    if proposed_val == 0:
        direct_feasible = True

    infeasibility_reasons: List[str] = []
    if proposed_val > available_units:
        if available_units == 0:
            infeasibility_reasons.append(
                f"Shelf is full (Occupancy: {cap_info['current_occupancy']}/{cap_info['shelf_capacity']}). "
                f"Direct placement of {proposed_val} units is impossible."
            )
        else:
            infeasibility_reasons.append(
                f"Partial space available: only {direct_placement_qty} of {proposed_val} proposed units "
                f"can fit directly on the shelf."
            )

    # Optional backroom storage evaluation for unplaced overflow
    backroom_available = None
    backroom_fits_overflow = None
    if backroom_capacity is not None and current_backroom_occupancy is not None:
        _validate_non_negative_number(backroom_capacity, "backroom_capacity")
        _validate_non_negative_number(current_backroom_occupancy, "current_backroom_occupancy")
        backroom_available = max(0.0, float(backroom_capacity) - float(current_backroom_occupancy))
        backroom_fits_overflow = unplaced_qty <= backroom_available

    return {
        "shelf_capacity": cap_info["shelf_capacity"],
        "current_occupancy": cap_info["current_occupancy"],
        "available_shelf_capacity": cap_info["available_shelf_capacity"],
        "proposed_quantity": _format_number(proposed_val),
        "direct_placement_quantity": _format_number(direct_placement_qty),
        "unplaced_quantity": _format_number(unplaced_qty),
        "direct_placement_feasible": direct_feasible,
        "backroom_available": _format_number(backroom_available) if backroom_available is not None else None,
        "backroom_fits_overflow": backroom_fits_overflow,
        "infeasibility_reasons": infeasibility_reasons,
    }


def evaluate_shelf_swap(
    shelf_capacity: Union[int, float],
    current_occupancy: Union[int, float],
    target_sku_id: str,
    needed_space: Union[int, float],
    existing_shelf_products: Sequence[Dict[str, Any]] = (),
) -> Dict[str, Any]:
    """
    Evaluate whether moving one or more existing shelf products can free sufficient space
    for a target SKU.

    Requirements:
    - Products must be marked movable (`is_movable=True`).
    - Displaced products must have confirmed alternative storage capacity.
    - Preserves product compatibility (`is_compatible_with_alternative=True`).
    - Prioritizes moving lower-priority products when priority is supplied.
    - Supports moving multiple products if a single product is insufficient.
    - Does not invent priorities when missing.
    """
    _validate_non_negative_number(needed_space, "needed_space")
    cap_info = calculate_available_shelf_capacity(shelf_capacity, current_occupancy)

    needed_val = float(needed_space)
    if needed_val <= 0:
        return {
            "shelf_swap_possible": True,
            "space_freed": 0,
            "needed_space": 0,
            "products_moved": [],
            "infeasibility_reasons": [],
        }

    if not isinstance(existing_shelf_products, Sequence) or isinstance(existing_shelf_products, (str, bytes)):
        raise TypeError("existing_shelf_products must be a sequence of product dictionaries.")

    # Priority mapping: lower rank numbers represent lower retention priority (swapped first)
    prio_map = {"LOW": 1, "MEDIUM": 2, "HIGH": 3, "CRITICAL": 4}

    # Filter and validate eligible movable products
    eligible_candidates: List[Dict[str, Any]] = []
    ineligibility_notes: List[str] = []

    for idx, prod in enumerate(existing_shelf_products):
        if not isinstance(prod, dict):
            raise TypeError(f"Product at index {idx} must be a dictionary.")

        p_sku = str(prod.get("sku_id", f"SKU_PRODUCT_{idx}"))
        if p_sku == target_sku_id:
            continue  # Cannot swap target SKU with itself

        is_movable = prod.get("is_movable", True)
        if not is_movable:
            ineligibility_notes.append(f"Product '{p_sku}' is marked non-movable.")
            continue

        is_compat = prod.get("is_compatible_with_alternative", True)
        if not is_compat:
            ineligibility_notes.append(f"Product '{p_sku}' cannot be moved due to location incompatibility.")
            continue

        alt_cap = prod.get("alternative_capacity", prod.get("target_alternative_capacity"))
        if alt_cap is None or alt_cap <= 0:
            ineligibility_notes.append(f"Product '{p_sku}' has no confirmed alternative storage capacity.")
            continue

        units_on_shelf = prod.get("units", prod.get("shelf_stock_units", 0))
        slots_per_unit = prod.get("slots_per_unit", 1)
        _validate_non_negative_number(units_on_shelf, f"Product '{p_sku}' units")
        _validate_non_negative_number(slots_per_unit, f"Product '{p_sku}' slots_per_unit")

        if units_on_shelf <= 0:
            continue

        # Maximum units that can be displaced into alternative storage
        movable_units = min(float(units_on_shelf), float(alt_cap))
        space_freed = movable_units * float(slots_per_unit)

        raw_prio = prod.get("priority")
        if isinstance(raw_prio, str):
            prio_score = prio_map.get(raw_prio.upper(), 2)
        elif isinstance(raw_prio, (int, float)):
            prio_score = int(raw_prio)
        else:
            prio_score = 2  # Default neutral priority without inventing ordering

        eligible_candidates.append({
            "sku_id": p_sku,
            "units_on_shelf": float(units_on_shelf),
            "movable_units": movable_units,
            "slots_per_unit": float(slots_per_unit),
            "space_freed": space_freed,
            "priority_score": prio_score,
            "destination": prod.get("destination", "BACKROOM_STORAGE"),
        })

    # Sort eligible candidates: lower priority score first, then higher space freed
    sorted_candidates = sorted(eligible_candidates, key=lambda c: (c["priority_score"], -c["space_freed"]))

    # Greedy allocation of swap space
    accumulated_freed = 0.0
    products_moved: List[Dict[str, Any]] = []

    for cand in sorted_candidates:
        if accumulated_freed >= needed_val:
            break

        remaining_needed = needed_val - accumulated_freed
        cand_slots = cand["slots_per_unit"]
        # Units needed from this candidate
        units_needed = math.ceil(remaining_needed / cand_slots)
        actual_units_moved = min(cand["movable_units"], units_needed)
        actual_space_freed = actual_units_moved * cand_slots

        accumulated_freed += actual_space_freed
        products_moved.append({
            "sku_id": cand["sku_id"],
            "units_moved": _format_number(actual_units_moved),
            "space_freed": _format_number(actual_space_freed),
            "destination": cand["destination"],
        })

    is_swap_feasible = accumulated_freed >= needed_val
    infeasibility_reasons: List[str] = []

    if not is_swap_feasible:
        if accumulated_freed == 0:
            reason = "No eligible products can be swapped to free shelf space."
            if ineligibility_notes:
                reason += f" Details: {'; '.join(ineligibility_notes)}"
            infeasibility_reasons.append(reason)
        else:
            infeasibility_reasons.append(
                f"Insufficient swap space: valid swaps free at most {_format_number(accumulated_freed)} units, "
                f"which is less than the required {_format_number(needed_val)} units."
            )

    return {
        "shelf_swap_possible": is_swap_feasible,
        "space_freed": _format_number(accumulated_freed),
        "needed_space": _format_number(needed_val),
        "products_moved": products_moved,
        "infeasibility_reasons": infeasibility_reasons,
    }


def evaluate_shelf_and_transfer_feasibility(
    target_store_id: str = "STORE_007",
    sku_id: str = "SKU_COLD_DRINK_750ML",
    shelf_capacity: Union[int, float] = 20,
    current_occupancy: Union[int, float] = 0,
    proposed_transfer_quantity: Union[int, float] = 0,
    safe_transfer_limit: Optional[Union[int, float]] = None,
    existing_shelf_products: Sequence[Dict[str, Any]] = (),
    slots_per_unit: Union[int, float] = 1,
) -> Dict[str, Any]:
    """
    Combined evaluation of transfer placement against physical shelf constraints and swap feasibility.

    Rules:
    - Never increases transfer quantity beyond Task 4's safe_transfer_limit.
    - Evaluates direct shelf placement first.
    - If direct placement is insufficient, evaluates shelf swaps to create space.
    - Discloses partial placement or explicit infeasibility reasons.
    """
    _validate_non_negative_number(proposed_transfer_quantity, "proposed_transfer_quantity")
    _validate_non_negative_number(safe_transfer_limit, "safe_transfer_limit")

    # Constraint: Never exceed Task 4's safe transferable limit
    effective_proposed_qty = float(proposed_transfer_quantity)
    if safe_transfer_limit is not None:
        effective_proposed_qty = min(effective_proposed_qty, float(safe_transfer_limit))

    # 1. Direct placement evaluation
    direct_eval = validate_direct_placement(
        shelf_capacity=shelf_capacity,
        current_occupancy=current_occupancy,
        proposed_quantity=effective_proposed_qty,
        slots_per_unit=slots_per_unit,
    )

    available_space = direct_eval["available_shelf_capacity"]
    direct_qty = direct_eval["direct_placement_quantity"]
    direct_feasible = direct_eval["direct_placement_feasible"]

    shelf_swap_possible = False
    space_freed_by_swap = 0
    quantity_after_swap = direct_qty
    products_moved: List[Dict[str, Any]] = []
    infeasibility_reasons: List[str] = []

    if direct_feasible:
        # Fits directly without needing a shelf swap
        placement_feasible = True
    else:
        # Direct placement cannot accommodate full transfer; evaluate shelf swap
        space_deficit = max(0.0, effective_proposed_qty - float(direct_qty))

        swap_eval = evaluate_shelf_swap(
            shelf_capacity=shelf_capacity,
            current_occupancy=current_occupancy,
            target_sku_id=sku_id,
            needed_space=space_deficit,
            existing_shelf_products=existing_shelf_products,
        )

        shelf_swap_possible = swap_eval["shelf_swap_possible"]
        space_freed_by_swap = swap_eval["space_freed"]
        products_moved = swap_eval["products_moved"]

        total_space_after_swap = float(available_space) + float(space_freed_by_swap)
        quantity_after_swap = min(effective_proposed_qty, total_space_after_swap)

        if shelf_swap_possible and quantity_after_swap >= effective_proposed_qty:
            placement_feasible = True
        else:
            placement_feasible = False
            infeasibility_reasons.extend(direct_eval["infeasibility_reasons"])
            infeasibility_reasons.extend(swap_eval["infeasibility_reasons"])

    return {
        "store_id": str(target_store_id),
        "sku_id": str(sku_id),
        "shelf_capacity": _format_number(shelf_capacity),
        "current_shelf_occupancy": _format_number(current_occupancy),
        "available_shelf_capacity": _format_number(available_space),
        "proposed_quantity": _format_number(effective_proposed_qty),
        "direct_placement_quantity": _format_number(direct_qty),
        "direct_placement_feasible": direct_feasible,
        "shelf_swap_possible": shelf_swap_possible,
        "space_freed_by_swap": _format_number(space_freed_by_swap),
        "quantity_after_swap": _format_number(quantity_after_swap),
        "placement_feasible": placement_feasible,
        "products_moved": products_moved,
        "safe_transfer_limit_applied": safe_transfer_limit is not None,
        "infeasibility_reasons": infeasibility_reasons,
        "assumptions": {
            "slots_per_unit": _format_number(slots_per_unit),
            "displaced_inventory_rule": "STORED_IN_CONFIRMED_ALTERNATIVE",
            "capacity_unit": "UNITS",
        },
    }
