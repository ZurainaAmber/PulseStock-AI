"""
PulseStock AI - Unit Test Suite for Stock-Out Time Prediction
Task 2: Stock-Out Time Prediction Engine Tests (Tests A through G)
"""

import math
import os
import sys
import unittest
from datetime import datetime, timedelta, timezone

# Ensure project root is in sys.path
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from engine.forecast import build_hourly_forecast
from engine.stockout import (
    calculate_projected_inventory,
    predict_stockout_time,
    calculate_truck_arrival_impact,
    evaluate_stockout,
)


class TestStockoutPredictionRequirements(unittest.TestCase):
    """
    Verification of required test cases A through G specified in Task 2 prompt.
    """

    def setUp(self):
        self.start_time = "2026-10-09T18:00:00Z"

    def test_a_stock_runs_out_within_an_hour(self):
        """
        Test A: Initial stock: 6 units. Demand: 12 units/hour.
        Expected stock-out: 30 minutes after interval starts.
        """
        res = predict_stockout_time(
            initial_stock=6,
            hourly_demand=[12],
            start_time=self.start_time
        )
        self.assertTrue(res["stockout_within_horizon"])
        self.assertEqual(res["stockout_time"], "2026-10-09T18:30:00Z")
        self.assertEqual(res["minutes_until_stockout"], 30)

        # Full evaluation check
        eval_res = evaluate_stockout(6, [12], start_time=self.start_time)
        self.assertEqual(eval_res["stockout_time"], "2026-10-09T18:30:00Z")
        self.assertTrue(eval_res["stockout_within_horizon"])

    def test_b_stock_survives_until_the_truck(self):
        """
        Test B: Initial stock: 20 units. Demand: 5 units/hour for two hours.
        Truck arrives after 90 minutes.
        Expected pre-replenishment stock at arrival: 12.5 units.
        """
        truck_time = "2026-10-09T19:30:00Z"  # 90 minutes after 18:00
        impact = calculate_truck_arrival_impact(
            initial_stock=20,
            hourly_demand=[5, 5],
            next_truck_arrival=truck_time,
            start_time=self.start_time
        )
        self.assertFalse(impact["stockout_before_truck"])
        self.assertEqual(impact["stock_at_truck_arrival_before_replenishment"], 12.5)
        self.assertEqual(impact["unmet_demand_before_truck"], 0)

        # Full evaluation check
        eval_res = evaluate_stockout(20, [5, 5], next_truck_arrival=truck_time, start_time=self.start_time)
        self.assertFalse(eval_res["stockout_before_truck"])
        self.assertEqual(eval_res["stock_at_truck_arrival_before_replenishment"], 12.5)
        self.assertEqual(eval_res["unmet_demand_before_truck"], 0)
        self.assertEqual(eval_res["status"], "SAFE_UNTIL_TRUCK")

    def test_c_stockout_before_truck(self):
        """
        Test C: Initial stock: 6 units. Demand: 6 units/hour for two hours.
        Truck arrives after 90 minutes.
        Expected stock-out: 1 hour after forecast starts, with 3 units of unmet demand before truck arrival.
        """
        truck_time = "2026-10-09T19:30:00Z"  # 90 minutes after 18:00
        eval_res = evaluate_stockout(
            initial_stock=6,
            hourly_demand=[6, 6],
            next_truck_arrival=truck_time,
            start_time=self.start_time
        )
        self.assertTrue(eval_res["stockout_within_horizon"])
        self.assertEqual(eval_res["stockout_time"], "2026-10-09T19:00:00Z")  # 1 hour after start
        self.assertTrue(eval_res["stockout_before_truck"])
        self.assertEqual(eval_res["stock_at_truck_arrival_before_replenishment"], 0)
        self.assertEqual(eval_res["unmet_demand_before_truck"], 3)
        self.assertEqual(eval_res["status"], "STOCKOUT_BEFORE_TRUCK")

    def test_d_zero_demand(self):
        """
        Test D: Initial stock: 10 units. Demand: 0.
        No stock-out should be predicted during the forecast horizon.
        """
        eval_res = evaluate_stockout(
            initial_stock=10,
            hourly_demand=[0, 0, 0, 0],
            start_time=self.start_time
        )
        self.assertIsNone(eval_res["stockout_time"])
        self.assertFalse(eval_res["stockout_within_horizon"])
        self.assertEqual(eval_res["status"], "NO_STOCKOUT_WITHIN_HORIZON")

        # Inventory stays 10 across all intervals
        for inv in eval_res["projected_inventory"]:
            self.assertEqual(inv["end_stock"], 10)
            self.assertEqual(inv["unmet_demand"], 0)

    def test_e_exact_boundary(self):
        """
        Test E: Initial stock: 5 units. Demand: 5 units/hour.
        Stock reaches zero exactly at the end of the hour.
        Verify boundary timestamp is returned consistently.
        """
        eval_res = evaluate_stockout(
            initial_stock=5,
            hourly_demand=[5],
            start_time=self.start_time
        )
        self.assertTrue(eval_res["stockout_within_horizon"])
        self.assertEqual(eval_res["stockout_time"], "2026-10-09T19:00:00Z")
        self.assertEqual(eval_res["projected_inventory"][0]["end_stock"], 0)
        self.assertEqual(eval_res["projected_inventory"][0]["unmet_demand"], 0)

    def test_f_invalid_inputs(self):
        """
        Test F: Reject negative inventory, negative demand, invalid timestamps,
        and invalid forecast horizons with meaningful errors.
        """
        # Negative initial stock
        with self.assertRaises(ValueError) as ctx:
            evaluate_stockout(initial_stock=-5, hourly_demand=[10])
        self.assertIn("negative", str(ctx.exception).lower())

        # Negative demand
        with self.assertRaises(ValueError) as ctx:
            evaluate_stockout(initial_stock=10, hourly_demand=[5, -2, 5])
        self.assertIn("negative", str(ctx.exception).lower())

        # Empty demand sequence
        with self.assertRaises(ValueError):
            evaluate_stockout(initial_stock=10, hourly_demand=[])

        # Invalid timestamp
        with self.assertRaises(ValueError):
            evaluate_stockout(initial_stock=10, hourly_demand=[5], start_time="invalid-date")

        with self.assertRaises(ValueError):
            evaluate_stockout(initial_stock=10, hourly_demand=[5], next_truck_arrival="invalid-truck")

        # Truck earlier than start time
        with self.assertRaises(ValueError) as ctx:
            evaluate_stockout(
                initial_stock=10,
                hourly_demand=[5, 5],
                start_time="2026-10-09T18:00:00Z",
                next_truck_arrival="2026-10-09T17:00:00Z"
            )
        self.assertIn("earlier", str(ctx.exception).lower())

        # NaN / Infinite
        with self.assertRaises(ValueError):
            evaluate_stockout(initial_stock=float("nan"), hourly_demand=[5])

        with self.assertRaises(ValueError):
            evaluate_stockout(initial_stock=10, hourly_demand=[float("inf")])

    def test_g_insufficient_horizon(self):
        """
        Test G: Next truck arrives after the supplied forecast ends.
        Do not claim to know inventory or unmet demand at truck arrival.
        """
        # Horizon is 2 hours (18:00 to 20:00). Truck arrives at 21:00 (3 hours after start).
        truck_time = "2026-10-09T21:00:00Z"
        eval_res = evaluate_stockout(
            initial_stock=20,
            hourly_demand=[5, 5],  # 2 hours
            next_truck_arrival=truck_time,
            start_time=self.start_time
        )

        # Stock did not run out during 2 hours (10 units remaining at 20:00)
        # Cannot know if it runs out before truck at 21:00
        self.assertIsNone(eval_res["stockout_before_truck"])
        self.assertIsNone(eval_res["stock_at_truck_arrival_before_replenishment"])
        self.assertIsNone(eval_res["unmet_demand_before_truck"])
        self.assertEqual(eval_res["status"], "INSUFFICIENT_HORIZON_FOR_TRUCK")


class TestStockoutAdvancedScenarios(unittest.TestCase):
    """
    Test inventory constraints, fractional rates, and integration with Task 1 forecast output.
    """

    def setUp(self):
        self.start_time = "2026-10-09T18:00:00Z"

    def test_inventory_never_drops_below_zero(self):
        """Physical inventory must strictly remain >= 0, while tracking unmet demand."""
        trajectory = calculate_projected_inventory(
            initial_stock=5,
            hourly_demand=[10, 10, 10],
            start_time=self.start_time
        )
        self.assertEqual(len(trajectory), 3)

        # Hour 0: Starts with 5, demand is 10. Consumed: 5, end: 0, unmet: 5
        self.assertEqual(trajectory[0]["start_stock"], 5)
        self.assertEqual(trajectory[0]["end_stock"], 0)
        self.assertEqual(trajectory[0]["unmet_demand"], 5)
        self.assertEqual(trajectory[0]["cumulative_unmet_demand"], 5)

        # Hour 1: Starts with 0, demand is 10. Consumed: 0, end: 0, unmet: 10
        self.assertEqual(trajectory[1]["start_stock"], 0)
        self.assertEqual(trajectory[1]["end_stock"], 0)
        self.assertEqual(trajectory[1]["unmet_demand"], 10)
        self.assertEqual(trajectory[1]["cumulative_unmet_demand"], 15)

        # Hour 2: Starts with 0, demand is 10. Cumulative unmet: 25
        self.assertEqual(trajectory[2]["end_stock"], 0)
        self.assertEqual(trajectory[2]["cumulative_unmet_demand"], 25)

        for step in trajectory:
            self.assertGreaterEqual(step["end_stock"], 0)

    def test_task1_forecast_integration(self):
        """Verify seamless compatibility with Task 1 build_hourly_forecast output."""
        # Generate Task 1 forecast for 4 hours with 2.0x cricket event
        forecast_points = build_hourly_forecast(
            start_time=self.start_time,
            horizon_hours=4,
            baseline_demand=10,
            events=[{
                "name": "Cricket Match",
                "event_type": "CRICKET",
                "multiplier": 2.0,
                "start_time": "2026-10-09T18:00:00Z",
                "end_time": "2026-10-09T20:00:00Z",
            }]
        )
        # Hour 0 & 1 demand = 20, Hour 2 & 3 demand = 10
        # Initial stock = 30
        # Hour 0: consumes 20, end = 10
        # Hour 1: demand 20, stock 10 -> runs out at 10/20 = 0.5 (30 mins into Hour 1 = 19:30)
        eval_res = evaluate_stockout(
            initial_stock=30,
            hourly_demand=forecast_points,
            next_truck_arrival="2026-10-09T21:00:00Z"
        )
        self.assertTrue(eval_res["stockout_within_horizon"])
        self.assertEqual(eval_res["stockout_time"], "2026-10-09T19:30:00Z")
        self.assertTrue(eval_res["stockout_before_truck"])
        self.assertEqual(eval_res["status"], "STOCKOUT_BEFORE_TRUCK")

    def test_required_output_schema_keys(self):
        """Verify all 11 required fields are present in the output dictionary."""
        eval_res = evaluate_stockout(
            initial_stock=15,
            hourly_demand=[5, 5, 5],
            next_truck_arrival="2026-10-09T20:00:00Z",
            start_time=self.start_time
        )
        expected_keys = [
            "initial_stock",
            "stockout_time",
            "stockout_within_horizon",
            "stockout_before_truck",
            "next_truck_arrival",
            "stock_at_truck_arrival_before_replenishment",
            "unmet_demand_before_truck",
            "projected_inventory",
            "forecast_horizon_end",
            "status",
            "assumptions",
        ]
        for key in expected_keys:
            self.assertIn(key, eval_res, f"Missing required key: {key}")

        # Check assumptions
        self.assertIn("consumption_rate", eval_res["assumptions"])
        self.assertEqual(eval_res["assumptions"]["timezone"], "UTC")


if __name__ == "__main__":
    unittest.main()
