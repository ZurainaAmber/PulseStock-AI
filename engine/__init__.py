"""
PulseStock AI - Decision Engine Package
Person 1: Decision Engine Core Services
"""

from engine.forecast import (
    HourlyForecastPoint,
    validate_forecast_inputs,
    forecast_hourly_demand,
    calculate_baseline_demand,
    build_hourly_forecast,
)
from engine.stockout import (
    calculate_projected_inventory,
    predict_stockout_time,
    calculate_truck_arrival_impact,
    evaluate_stockout,
)
from engine.diagnosis import (
    diagnose_demand_surge,
    diagnose_low_inventory,
    diagnose_shelf_capacity,
    diagnose_delayed_truck,
    diagnose_rider_shortage,
    diagnose_inventory_problems,
)
from engine.transfer import (
    calculate_safe_donor_surplus,
    calculate_target_requirement,
    calculate_transfer_quantity,
    evaluate_donor_candidate,
    evaluate_and_rank_donors,
)
from engine.constraints import (
    calculate_available_shelf_capacity,
    validate_direct_placement,
    evaluate_shelf_swap,
    evaluate_shelf_and_transfer_feasibility,
)

__all__ = [
    "HourlyForecastPoint",
    "validate_forecast_inputs",
    "forecast_hourly_demand",
    "calculate_baseline_demand",
    "build_hourly_forecast",
    "calculate_projected_inventory",
    "predict_stockout_time",
    "calculate_truck_arrival_impact",
    "evaluate_stockout",
    "diagnose_demand_surge",
    "diagnose_low_inventory",
    "diagnose_shelf_capacity",
    "diagnose_delayed_truck",
    "diagnose_rider_shortage",
    "diagnose_inventory_problems",
    "calculate_safe_donor_surplus",
    "calculate_target_requirement",
    "calculate_transfer_quantity",
    "evaluate_donor_candidate",
    "evaluate_and_rank_donors",
    "calculate_available_shelf_capacity",
    "validate_direct_placement",
    "evaluate_shelf_swap",
    "evaluate_shelf_and_transfer_feasibility",
]
