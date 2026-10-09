"""
PulseStock AI - Decision Engine: Inventory Problem Diagnosis Module
Top-level entry point re-exporting core diagnosis functions from engine.diagnosis.
"""

import sys
from pathlib import Path

# Ensure project root is in sys.path for direct imports
_PROJECT_ROOT = Path(__file__).resolve().parent
if str(_PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(_PROJECT_ROOT))

from engine.diagnosis import (
    diagnose_demand_surge,
    diagnose_low_inventory,
    diagnose_shelf_capacity,
    diagnose_delayed_truck,
    diagnose_rider_shortage,
    diagnose_inventory_problems,
)

__all__ = [
    "diagnose_demand_surge",
    "diagnose_low_inventory",
    "diagnose_shelf_capacity",
    "diagnose_delayed_truck",
    "diagnose_rider_shortage",
    "diagnose_inventory_problems",
]
