"""
PulseStock AI - Decision Engine: Stock-Out Time Prediction Module
Top-level entry point re-exporting core stock-out functions from engine.stockout.
"""

import sys
from pathlib import Path

# Ensure project root is in sys.path for direct imports
_PROJECT_ROOT = Path(__file__).resolve().parent
if str(_PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(_PROJECT_ROOT))

from engine.stockout import (
    calculate_projected_inventory,
    predict_stockout_time,
    calculate_truck_arrival_impact,
    evaluate_stockout,
)

__all__ = [
    "calculate_projected_inventory",
    "predict_stockout_time",
    "calculate_truck_arrival_impact",
    "evaluate_stockout",
]
