"""
PulseStock AI - Unit Test Suite for Inventory Problem Diagnosis
Task 3: Inventory Problem Diagnosis Engine Tests (Tests A through I)
"""

import json
import os
import sys
import unittest
from datetime import datetime

# Ensure project root is in sys.path
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from engine.diagnosis import (
    diagnose_demand_surge,
    diagnose_low_inventory,
    diagnose_shelf_capacity,
    diagnose_delayed_truck,
    diagnose_rider_shortage,
    diagnose_inventory_problems,
)


class TestDiagnosisRequirements(unittest.TestCase):
    """
    Verification of required test cases A through I specified in Task 3 prompt.
    """

    def test_a_match_night_demand_surge(self):
        """
        Test A: Baseline demand: 3 units/hour. Forecast demand: 9 units/hour. Event uplift: 3.
        Expected: detect DEMAND_SURGE and include the numerical evidence.
        """
        res = diagnose_demand_surge(
            forecast_demand=9,
            baseline_demand=3,
            event_uplift=3,
            time_interval="18:00 - 19:00"
        )
        self.assertIsNotNone(res)
        self.assertEqual(res["code"], "DEMAND_SURGE")
        self.assertEqual(res["category"], "demand")
        self.assertIn(res["severity"], ("high", "critical"))
        self.assertEqual(res["evidence"]["baseline_demand_per_hour"], 3)
        self.assertEqual(res["evidence"]["forecast_demand_per_hour"], 9)
        self.assertEqual(res["evidence"]["event_uplift"], 3)

        # Full orchestrator test
        full_res = diagnose_inventory_problems(
            forecast_demand=9,
            baseline_demand=3,
            event_uplift=3
        )
        codes = [d["code"] for d in full_res["diagnoses"]]
        self.assertIn("DEMAND_SURGE", codes)
        self.assertEqual(full_res["primary_cause"], "DEMAND_SURGE")

    def test_b_low_inventory(self):
        """
        Test B: Current stock is insufficient to cover forecast demand until next truck.
        Expected: detect LOW_INVENTORY, using Task 2's stock-out result when available.
        """
        # Initial stock: 6, Demand: [6, 6] (6/hr for 2h). Truck arrives in 90 min (19:30).
        # Depletes at 60 min (19:00), leading to 3 units unmet demand before truck arrives.
        res = diagnose_low_inventory(
            current_stock=6,
            forecast_demand=[6, 6],
            next_truck_arrival="2026-10-09T19:30:00Z",
            start_time="2026-10-09T18:00:00Z"
        )
        self.assertIsNotNone(res)
        self.assertEqual(res["code"], "LOW_INVENTORY")
        self.assertEqual(res["category"], "inventory")
        self.assertIn(res["severity"], ("high", "critical"))
        self.assertTrue(res["evidence"]["stockout_before_truck"])
        self.assertEqual(res["evidence"]["stockout_time"], "2026-10-09T19:00:00Z")
        self.assertEqual(res["evidence"]["unmet_demand_before_truck"], 3)

        # Full orchestrator check
        full_res = diagnose_inventory_problems(
            current_stock=6,
            forecast_demand=[6, 6],
            next_truck_arrival="2026-10-09T19:30:00Z",
            start_time="2026-10-09T18:00:00Z"
        )
        codes = [d["code"] for d in full_res["diagnoses"]]
        self.assertIn("LOW_INVENTORY", codes)

    def test_c_full_shelf(self):
        """
        Test C: Shelf capacity: 20 units, shelf occupancy: 20 units, additional shelf space unavailable.
        Expected: detect SHELF_CAPACITY_CONSTRAINT.
        """
        res = diagnose_shelf_capacity(
            shelf_capacity_units=20,
            shelf_stock_units=20,
            backroom_stock_units=15
        )
        self.assertIsNotNone(res)
        self.assertEqual(res["code"], "SHELF_CAPACITY_CONSTRAINT")
        self.assertEqual(res["category"], "shelf")
        self.assertEqual(res["evidence"]["shelf_capacity_units"], 20)
        self.assertEqual(res["evidence"]["shelf_stock_units"], 20)
        self.assertEqual(res["evidence"]["available_shelf_capacity"], 0)
        self.assertEqual(res["evidence"]["utilization_pct"], 100.0)

        # Full orchestrator check
        full_res = diagnose_inventory_problems(
            shelf_capacity_units=20,
            shelf_stock_units=20
        )
        codes = [d["code"] for d in full_res["diagnoses"]]
        self.assertIn("SHELF_CAPACITY_CONSTRAINT", codes)

    def test_d_delayed_truck(self):
        """
        Test D: Planned arrival is 8:00 PM and updated estimated arrival is 9:00 PM.
        Expected: detect a delay of 60 minutes.
        """
        planned = "2026-10-09T20:00:00Z"
        updated = "2026-10-09T21:00:00Z"
        res = diagnose_delayed_truck(
            planned_arrival_time=planned,
            estimated_arrival_time=updated,
            truck_id="TRK_CENTRAL_01"
        )
        self.assertIsNotNone(res)
        self.assertEqual(res["code"], "DELAYED_TRUCK")
        self.assertEqual(res["category"], "logistics")
        self.assertEqual(res["evidence"]["delay_minutes"], 60)
        self.assertEqual(res["evidence"]["planned_arrival_time"], planned)
        self.assertEqual(res["evidence"]["estimated_arrival_time"], updated)

        # Full orchestrator check
        full_res = diagnose_inventory_problems(
            planned_truck_arrival=planned,
            next_truck_arrival=updated
        )
        codes = [d["code"] for d in full_res["diagnoses"]]
        self.assertIn("DELAYED_TRUCK", codes)

    def test_e_rider_shortage(self):
        """
        Test E: Required riders: 8. Available riders: 5.
        Expected: detect a shortage of 3 riders.
        """
        res = diagnose_rider_shortage(
            required_riders=8,
            available_riders=5
        )
        self.assertIsNotNone(res)
        self.assertEqual(res["code"], "RIDER_SHORTAGE")
        self.assertEqual(res["category"], "fulfillment")
        self.assertEqual(res["evidence"]["required_riders"], 8)
        self.assertEqual(res["evidence"]["available_riders"], 5)
        self.assertEqual(res["evidence"]["shortage_count"], 3)

        # Full orchestrator check
        full_res = diagnose_inventory_problems(
            required_riders=8,
            available_riders=5
        )
        codes = [d["code"] for d in full_res["diagnoses"]]
        self.assertIn("RIDER_SHORTAGE", codes)

    def test_f_multiple_causes(self):
        """
        Test F: A demand surge and a truck delay occur together.
        Expected: return both diagnoses, not just one.
        """
        full_res = diagnose_inventory_problems(
            forecast_demand=9,
            baseline_demand=3,
            event_uplift=3,
            planned_truck_arrival="2026-10-09T20:00:00Z",
            next_truck_arrival="2026-10-09T21:00:00Z"
        )
        codes = [d["code"] for d in full_res["diagnoses"]]
        self.assertIn("DEMAND_SURGE", codes)
        self.assertIn("DELAYED_TRUCK", codes)
        self.assertEqual(len(codes), 2)
        # Primary cause must be identified
        self.assertIn(full_res["primary_cause"], ("DEMAND_SURGE", "DELAYED_TRUCK"))

    def test_g_healthy_store(self):
        """
        Test G: Stock is sufficient, demand is normal, shelf is not full,
        truck is on schedule, and rider capacity is adequate.
        Expected: return no operational problem diagnoses.
        """
        full_res = diagnose_inventory_problems(
            current_stock=100,
            forecast_demand=[5, 5],
            baseline_demand=5,
            event_uplift=1.0,
            shelf_capacity_units=50,
            shelf_stock_units=20,
            planned_truck_arrival="2026-10-09T20:00:00Z",
            next_truck_arrival="2026-10-09T20:00:00Z",
            required_riders=5,
            available_riders=8
        )
        self.assertEqual(full_res["diagnoses"], [])
        self.assertIsNone(full_res["primary_cause"])

    def test_h_missing_data(self):
        """
        Test H: Important fields such as shelf occupancy or rider capacity are absent.
        Expected: do not invent values or claim unsupported diagnoses. Report relevant data gaps.
        """
        # Store provided with no baseline demand and partial rider capacity
        full_res = diagnose_inventory_problems(
            forecast_demand=10,
            shelf_capacity_units=40,  # missing shelf_stock_units
            available_riders=5        # missing required_riders
        )
        # Diagnoses should NOT include unsupported guesses
        codes = [d["code"] for d in full_res["diagnoses"]]
        self.assertNotIn("DEMAND_SURGE", codes)
        self.assertNotIn("SHELF_CAPACITY_CONSTRAINT", codes)
        self.assertNotIn("RIDER_SHORTAGE", codes)

        # Expected data gaps recorded
        self.assertIn("missing_baseline_demand", full_res["data_gaps"])
        self.assertIn("missing_shelf_stock_occupancy", full_res["data_gaps"])
        self.assertIn("missing_rider_capacity_data", full_res["data_gaps"])

    def test_i_invalid_data(self):
        """
        Test I: Negative quantities, malformed timestamps, and inconsistent capacity values.
        Expected: reject invalid inputs with meaningful ValueError or TypeError.
        """
        # Negative demand
        with self.assertRaises(ValueError):
            diagnose_demand_surge(forecast_demand=-5, baseline_demand=10)

        # Negative current stock
        with self.assertRaises(ValueError):
            diagnose_low_inventory(current_stock=-10)

        # Negative shelf capacity
        with self.assertRaises(ValueError):
            diagnose_shelf_capacity(shelf_capacity_units=-20, shelf_stock_units=10)

        # Negative shelf occupancy
        with self.assertRaises(ValueError):
            diagnose_shelf_capacity(shelf_capacity_units=20, shelf_stock_units=-5)

        # Negative riders
        with self.assertRaises(ValueError):
            diagnose_rider_shortage(required_riders=-4, available_riders=5)

        # Malformed timestamp
        with self.assertRaises(ValueError):
            diagnose_delayed_truck(planned_arrival_time="bad-date", estimated_arrival_time="bad-date")


class TestDiagnosisIntegration(unittest.TestCase):
    """Test schema serialization and multi-diagnosis primary cause resolution."""

    def test_json_serializability(self):
        """Verify the full diagnosis output can be serialized to JSON without error."""
        full_res = diagnose_inventory_problems(
            store_id="STORE_007",
            sku_id="SKU_COLD_DRINK_750ML",
            forecast_demand=9,
            baseline_demand=3,
            event_uplift=3,
            current_stock=5,
            next_truck_arrival="2026-10-09T20:00:00Z",
            start_time="2026-10-09T18:00:00Z",
            shelf_capacity_units=20,
            shelf_stock_units=20,
            required_riders=8,
            available_riders=5
        )

        serialized = json.dumps(full_res, indent=2)
        parsed = json.loads(serialized)

        self.assertEqual(parsed["store_id"], "STORE_007")
        self.assertEqual(parsed["sku_id"], "SKU_COLD_DRINK_750ML")
        self.assertIsInstance(parsed["diagnoses"], list)
        self.assertGreaterEqual(len(parsed["diagnoses"]), 3)
        self.assertIsNotNone(parsed["primary_cause"])
        self.assertIsInstance(parsed["data_gaps"], list)

        # Check required diagnosis item schema
        first_diag = parsed["diagnoses"][0]
        self.assertIn("code", first_diag)
        self.assertIn("category", first_diag)
        self.assertIn("severity", first_diag)
        self.assertIn("title", first_diag)
        self.assertIn("description", first_diag)
        self.assertIn("evidence", first_diag)
        self.assertIn("confidence", first_diag)


if __name__ == "__main__":
    unittest.main()
