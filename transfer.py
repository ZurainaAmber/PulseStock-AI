"""
PulseStock AI - Decision Engine: Store Inventory Transfer Logic Module
Top-level entry point re-exporting core transfer functions from engine.transfer.
"""

import sys
from pathlib import Path

# Ensure project root is in sys.path for direct imports
_PROJECT_ROOT = Path(__file__).resolve().parent
if str(_PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(_PROJECT_ROOT))

from engine.transfer import (
    calculate_safe_donor_surplus,
    calculate_target_requirement,
    calculate_transfer_quantity,
    evaluate_donor_candidate,
    evaluate_and_rank_donors,
)

__all__ = [
    "calculate_safe_donor_surplus",
    "calculate_target_requirement",
    "calculate_transfer_quantity",
    "evaluate_donor_candidate",
    "evaluate_and_rank_donors",
]
