"""
PulseStock AI - Decision Engine: Shelf-Space Constraints & Shelf-Swap Feasibility Module
Top-level entry point re-exporting core constraint functions from engine.constraints.
"""

import sys
from pathlib import Path

# Ensure project root is in sys.path for direct imports
_PROJECT_ROOT = Path(__file__).resolve().parent
if str(_PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(_PROJECT_ROOT))

from engine.constraints import (
    calculate_available_shelf_capacity,
    validate_direct_placement,
    evaluate_shelf_swap,
    evaluate_shelf_and_transfer_feasibility,
)

__all__ = [
    "calculate_available_shelf_capacity",
    "validate_direct_placement",
    "evaluate_shelf_swap",
    "evaluate_shelf_and_transfer_feasibility",
]
