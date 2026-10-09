"""
PulseStock AI - Decision Engine: Hourly Demand Forecasting Module
Top-level entry point re-exporting core forecasting functions from engine.forecast.
"""

import sys
from pathlib import Path

# Ensure project root is in sys.path for direct imports
_PROJECT_ROOT = Path(__file__).resolve().parent
if str(_PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(_PROJECT_ROOT))

from engine.forecast import (
    HourlyForecastPoint,
    validate_forecast_inputs,
    forecast_hourly_demand,
    calculate_baseline_demand,
    build_hourly_forecast,
)

__all__ = [
    "HourlyForecastPoint",
    "validate_forecast_inputs",
    "forecast_hourly_demand",
    "calculate_baseline_demand",
    "build_hourly_forecast",
]
