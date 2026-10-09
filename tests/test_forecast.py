"""
PulseStock AI - Unit Test Suite for Hourly Demand Forecasting
Task 1: Hourly Demand Forecasting Engine Tests
"""

import math
import os
import sys
import unittest
from datetime import datetime, timezone

# Ensure project root is in sys.path
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from engine.forecast import (
    HourlyForecastPoint,
    validate_forecast_inputs,
    forecast_hourly_demand,
    calculate_baseline_demand,
    build_hourly_forecast,
)


class TestRequiredCalculations(unittest.TestCase):
    """
    Verify the exact required calculations specified in prompt requirements:
    1. Baseline [3, 3, 3, 3], uplift [1, 1, 1, 1] -> [3, 3, 3, 3]
    2. Baseline [3, 3, 3, 3], uplift [1, 1, 3, 3] -> [3, 3, 9, 9]
    3. Baseline [2, 4, 3, 5], uplift [1, 1.5, 2, 1] -> [2, 6, 6, 5]
    And verify rejection of negative demand and negative uplift.
    """

    def test_required_example_1(self):
        baseline = [3, 3, 3, 3]
        uplift = [1, 1, 1, 1]
        result = forecast_hourly_demand(baseline, uplift)
        self.assertEqual(result, [3, 3, 3, 3])

    def test_required_example_2(self):
        baseline = [3, 3, 3, 3]
        uplift = [1, 1, 3, 3]
        result = forecast_hourly_demand(baseline, uplift)
        self.assertEqual(result, [3, 3, 9, 9])

    def test_required_example_3(self):
        baseline = [2, 4, 3, 5]
        uplift = [1, 1.5, 2, 1]
        result = forecast_hourly_demand(baseline, uplift)
        self.assertEqual(result, [2, 6, 6, 5])

    def test_reject_negative_demand(self):
        with self.assertRaises(ValueError) as ctx:
            forecast_hourly_demand([-1, 3, 3, 3], [1, 1, 1, 1])
        self.assertIn("negative", str(ctx.exception).lower())

    def test_reject_negative_uplift(self):
        with self.assertRaises(ValueError) as ctx:
            forecast_hourly_demand([3, 3, 3, 3], [1, -0.5, 1, 1])
        self.assertIn("negative", str(ctx.exception).lower())


class TestValidateForecastInputs(unittest.TestCase):
    """Test input validation for demand, uplift, timestamps, horizon, and lengths."""

    def test_valid_inputs_pass(self):
        self.assertTrue(validate_forecast_inputs(
            baseline_demand=[10, 20],
            uplift=[1.2, 1.5],
            timestamps=["2026-10-09T18:00:00Z", "2026-10-09T19:00:00Z"],
            horizon=2,
            start_time="2026-10-09T18:00:00Z"
        ))

    def test_reject_negative_demand_in_validation(self):
        with self.assertRaises(ValueError):
            validate_forecast_inputs(baseline_demand=-5)
        with self.assertRaises(ValueError):
            validate_forecast_inputs(baseline_demand=[10, -2, 5])

    def test_reject_negative_uplift_in_validation(self):
        with self.assertRaises(ValueError):
            validate_forecast_inputs(uplift=-1.0)
        with self.assertRaises(ValueError):
            validate_forecast_inputs(uplift=[1.0, -0.2])

    def test_reject_mismatched_lengths(self):
        with self.assertRaises(ValueError) as ctx:
            validate_forecast_inputs(baseline_demand=[1, 2, 3], uplift=[1, 1])
        self.assertIn("mismatch", str(ctx.exception).lower())

    def test_reject_mismatched_timestamps_length(self):
        with self.assertRaises(ValueError) as ctx:
            validate_forecast_inputs(
                baseline_demand=[10, 20],
                timestamps=["2026-10-09T18:00:00Z"]
            )
        self.assertIn("mismatch", str(ctx.exception).lower())

    def test_reject_empty_sequences(self):
        with self.assertRaises(ValueError):
            validate_forecast_inputs(baseline_demand=[])
        with self.assertRaises(ValueError):
            validate_forecast_inputs(uplift=[])

    def test_reject_invalid_horizon(self):
        with self.assertRaises(ValueError):
            validate_forecast_inputs(horizon=0)
        with self.assertRaises(ValueError):
            validate_forecast_inputs(horizon=-4)
        with self.assertRaises(TypeError):
            validate_forecast_inputs(horizon="12")
        with self.assertRaises(TypeError):
            validate_forecast_inputs(horizon=True)

    def test_reject_nan_and_inf(self):
        with self.assertRaises(ValueError):
            validate_forecast_inputs(baseline_demand=[float("nan")])
        with self.assertRaises(ValueError):
            validate_forecast_inputs(uplift=[float("inf")])

    def test_reject_non_numeric_and_bools(self):
        with self.assertRaises(TypeError):
            validate_forecast_inputs(baseline_demand=[True, False])
        with self.assertRaises(TypeError):
            validate_forecast_inputs(baseline_demand=["high", "low"])


class TestForecastHourlyDemand(unittest.TestCase):
    """Test normal demand, event uplift, scalar vs sequence, and floating-point values."""

    def test_scalar_calculations(self):
        self.assertEqual(forecast_hourly_demand(10, 1.5), 15)
        self.assertEqual(forecast_hourly_demand(10, 1.25), 12.5)

    def test_scalar_baseline_with_sequence_uplift(self):
        result = forecast_hourly_demand(10, [1.0, 1.5, 2.0])
        self.assertEqual(result, [10, 15, 20])

    def test_sequence_baseline_with_scalar_uplift(self):
        result = forecast_hourly_demand([5, 10, 15], 2.0)
        self.assertEqual(result, [10, 20, 30])

    def test_floating_point_values(self):
        result = forecast_hourly_demand([2.5, 3.5], [2.0, 1.0])
        self.assertEqual(result, [5, 3.5])

    def test_zero_baseline_demand(self):
        result = forecast_hourly_demand([0, 0, 0], [1.5, 2.0, 3.0])
        self.assertEqual(result, [0, 0, 0])

    def test_zero_uplift(self):
        result = forecast_hourly_demand([10, 20], [0.0, 0.0])
        self.assertEqual(result, [0, 0])

    def test_cap_multiplier(self):
        # 10 * 5.0 = 50, but capped at 4.5 -> 10 * 4.5 = 45
        result = forecast_hourly_demand([10], [5.0], cap_multiplier=4.5)
        self.assertEqual(result, [45])


class TestCalculateBaselineDemand(unittest.TestCase):
    """Test historical averages, missing observation handling, filtering, and insufficient data."""

    def test_numeric_list_average(self):
        data = [10, 20, 30, 40]
        self.assertEqual(calculate_baseline_demand(data), 25)

    def test_floating_point_average(self):
        data = [2, 5]
        self.assertEqual(calculate_baseline_demand(data), 3.5)

    def test_missing_observations_ignore(self):
        data = [10, None, 20, None, 30]
        self.assertEqual(calculate_baseline_demand(data, missing_strategy="ignore"), 20)

    def test_missing_observations_zero(self):
        # [10, 0.0, 20] -> sum = 30, count = 3, avg = 10.0
        data = [10, None, 20]
        self.assertEqual(calculate_baseline_demand(data, missing_strategy="zero"), 10)

    def test_timestamped_dict_records(self):
        records = [
            {"timestamp": "2026-10-08T18:00:00Z", "quantity": 12},
            {"timestamp": "2026-10-09T18:00:00Z", "quantity": 16},
            {"timestamp": "2026-10-09T19:00:00Z", "quantity": 5},
        ]
        # Average specifically for 18:00
        avg_18 = calculate_baseline_demand(records, target_hour=18)
        self.assertEqual(avg_18, 14)
        # Average overall
        avg_all = calculate_baseline_demand(records)
        self.assertEqual(avg_all, 11)

    def test_tuple_records(self):
        records = [
            ("2026-10-08T14:00:00Z", 20),
            ("2026-10-09T14:00:00Z", 30),
        ]
        self.assertEqual(calculate_baseline_demand(records, target_hour=14), 25)

    def test_insufficient_historical_data_empty(self):
        with self.assertRaises(ValueError) as ctx:
            calculate_baseline_demand([])
        self.assertIn("insufficient", str(ctx.exception).lower())

    def test_insufficient_historical_data_all_none(self):
        with self.assertRaises(ValueError) as ctx:
            calculate_baseline_demand([None, None])
        self.assertIn("insufficient", str(ctx.exception).lower())

    def test_insufficient_data_target_hour_not_found(self):
        records = [{"timestamp": "2026-10-08T10:00:00Z", "quantity": 5}]
        with self.assertRaises(ValueError) as ctx:
            calculate_baseline_demand(records, target_hour=22)
        self.assertIn("no valid observations found", str(ctx.exception).lower())

    def test_default_fallback_on_empty(self):
        self.assertEqual(calculate_baseline_demand([], default=15.0), 15)

    def test_reject_negative_sales(self):
        with self.assertRaises(ValueError):
            calculate_baseline_demand([10, -5, 20])


class TestEventHandlingAndBoundaries(unittest.TestCase):
    """Test event start/end boundaries, time zones, overlapping events, and multiplier caps."""

    def setUp(self):
        self.start_time = "2026-10-09T17:00:00Z"

    def test_event_boundaries(self):
        # Event runs from 18:00 to 20:00 (2 hours)
        events = [
            {
                "name": "Cricket Match",
                "event_type": "CRICKET",
                "multiplier": 2.0,
                "start_time": "2026-10-09T18:00:00Z",
                "end_time": "2026-10-09T20:00:00Z",
            }
        ]
        # Horizon = 4 hours (17:00-18:00, 18:00-19:00, 19:00-20:00, 20:00-21:00)
        forecast = build_hourly_forecast(
            start_time=self.start_time,
            horizon_hours=4,
            baseline_demand=10,
            events=events
        )

        self.assertEqual(len(forecast), 4)

        # Hour 0: 17:00 - 18:00 -> BEFORE event start -> multiplier 1.0 -> demand 10
        self.assertEqual(forecast[0].hour_label, "17:00 - 18:00")
        self.assertEqual(forecast[0].final_projected_demand_units, 10)
        self.assertEqual(forecast[0].cricket_uplift_units, 0)
        self.assertEqual(forecast[0].applied_multiplier, 1.0)

        # Hour 1: 18:00 - 19:00 -> INSIDE event -> multiplier 2.0 -> demand 20
        self.assertEqual(forecast[1].hour_label, "18:00 - 19:00")
        self.assertEqual(forecast[1].final_projected_demand_units, 20)
        self.assertEqual(forecast[1].cricket_uplift_units, 10)
        self.assertEqual(forecast[1].applied_multiplier, 2.0)

        # Hour 2: 19:00 - 20:00 -> INSIDE event -> multiplier 2.0 -> demand 20
        self.assertEqual(forecast[2].hour_label, "19:00 - 20:00")
        self.assertEqual(forecast[2].final_projected_demand_units, 20)
        self.assertEqual(forecast[2].cricket_uplift_units, 10)

        # Hour 3: 20:00 - 21:00 -> AFTER event end -> multiplier 1.0 -> demand 10
        self.assertEqual(forecast[3].hour_label, "20:00 - 21:00")
        self.assertEqual(forecast[3].final_projected_demand_units, 10)
        self.assertEqual(forecast[3].cricket_uplift_units, 0)
        self.assertEqual(forecast[3].applied_multiplier, 1.0)

    def test_overlapping_multiplicative_events(self):
        # Cricket (2.0x) and Rain (1.5x) overlapping at 18:00-19:00
        # Combined multiplier = 2.0 * 1.5 = 3.0x -> baseline 10 * 3.0 = 30
        events = [
            {
                "name": "Cricket Match",
                "event_type": "CRICKET",
                "multiplier": 2.0,
                "start_time": "2026-10-09T18:00:00Z",
                "end_time": "2026-10-09T20:00:00Z",
            },
            {
                "name": "Heavy Rain",
                "event_type": "RAIN",
                "multiplier": 1.5,
                "start_time": "2026-10-09T18:00:00Z",
                "end_time": "2026-10-09T19:00:00Z",
            },
        ]
        forecast = build_hourly_forecast(
            start_time="2026-10-09T18:00:00Z",
            horizon_hours=2,
            baseline_demand=10,
            events=events
        )

        # Hour 0: Cricket + Rain active -> 10 * 3.0 = 30
        self.assertEqual(forecast[0].final_projected_demand_units, 30)
        self.assertEqual(forecast[0].applied_multiplier, 3.0)
        self.assertGreater(forecast[0].cricket_uplift_units, 0)
        self.assertGreater(forecast[0].rain_uplift_units, 0)

        # Hour 1: Rain ended, only Cricket active -> 10 * 2.0 = 20
        self.assertEqual(forecast[1].final_projected_demand_units, 20)
        self.assertEqual(forecast[1].applied_multiplier, 2.0)
        self.assertEqual(forecast[1].rain_uplift_units, 0)

    def test_event_cap_multiplier(self):
        # Cricket 3.0x * Festival 2.0x = 6.0x -> capped at 4.5x
        events = [
            {"event_type": "CRICKET", "multiplier": 3.0, "start_time": "2026-10-09T18:00:00Z", "end_time": "2026-10-09T19:00:00Z"},
            {"event_type": "FESTIVAL", "multiplier": 2.0, "start_time": "2026-10-09T18:00:00Z", "end_time": "2026-10-09T19:00:00Z"},
        ]
        forecast = build_hourly_forecast(
            start_time="2026-10-09T18:00:00Z",
            horizon_hours=1,
            baseline_demand=10,
            events=events,
            cap_multiplier=4.5
        )
        self.assertEqual(forecast[0].final_projected_demand_units, 45)
        self.assertEqual(forecast[0].applied_multiplier, 4.5)

    def test_invalid_event_time_window(self):
        events = [
            {"start_time": "2026-10-09T20:00:00Z", "end_time": "2026-10-09T18:00:00Z", "multiplier": 1.5}
        ]
        with self.assertRaises(ValueError):
            build_hourly_forecast("2026-10-09T18:00:00Z", 2, events=events)


class TestBuildHourlyForecast(unittest.TestCase):
    """Test multi-hour forecasts, confidence intervals, and data formatting."""

    def test_multi_hour_forecast_24_hours(self):
        forecast = build_hourly_forecast(
            start_time="2026-10-09T00:00:00Z",
            horizon_hours=24,
            baseline_demand=15
        )
        self.assertEqual(len(forecast), 24)
        for pt in forecast:
            self.assertEqual(pt.baseline_demand_units, 15)
            self.assertEqual(pt.final_projected_demand_units, 15)
            self.assertTrue(pt.confidence_lower_bound <= pt.final_projected_demand_units <= pt.confidence_upper_bound)

    def test_sequence_baseline_demand(self):
        baseline = [10, 12, 14, 16]
        forecast = build_hourly_forecast(
            start_time="2026-10-09T18:00:00Z",
            horizon_hours=4,
            baseline_demand=baseline
        )
        self.assertEqual([pt.baseline_demand_units for pt in forecast], [10, 12, 14, 16])

    def test_mismatched_baseline_sequence_and_horizon(self):
        with self.assertRaises(ValueError):
            build_hourly_forecast(
                start_time="2026-10-09T18:00:00Z",
                horizon_hours=4,
                baseline_demand=[10, 12]  # length 2 != 4
            )

    def test_confidence_interval_bounds(self):
        forecast = build_hourly_forecast(
            start_time="2026-10-09T18:00:00Z",
            horizon_hours=1,
            baseline_demand=100,
            confidence_interval_pct=0.15
        )
        # 100 * (1 - 0.15) = 85, 100 * (1 + 0.15) = 115
        self.assertEqual(forecast[0].confidence_lower_bound, 85)
        self.assertEqual(forecast[0].confidence_upper_bound, 115)

    def test_dict_and_attribute_access(self):
        forecast = build_hourly_forecast(
            start_time="2026-10-09T18:00:00Z",
            horizon_hours=1,
            baseline_demand=20
        )
        pt = forecast[0]
        # Dict access
        self.assertEqual(pt["final_projected_demand_units"], 20)
        # Attribute access
        self.assertEqual(pt.final_projected_demand_units, 20)
        self.assertIn("timestamp", pt)
        self.assertIn("hour_label", pt)


if __name__ == "__main__":
    unittest.main()
