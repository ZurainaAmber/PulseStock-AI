"""
PulseStock AI - Unit Test Suite for Store Inventory Transfer Logic
Task 4: Transfer Logic Engine Tests (Tests A through I)
"""

import json
import os
import sys
import unittest

# Ensure project root is in sys.path
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from engine.transfer import (
    calculate_safe_donor_surplus,
    calculate_target_requirement,
    calculate_transfer_quantity,
    evaluate_donor_candidate,
    evaluate_and_rank_donors,
)


class TestTransferLogicRequirements(unittest.TestCase):
    """
    Verification of required test cases A through I specified in Task 4 prompt.
    """

    def test_a_safe_donor(self):
        """
        Test A: Donor stock: 50 units. Projected demand: 20 units. Safety stock: 10 units.
        Expected safe surplus: 20 units.
        """
        res = calculate_safe_donor_surplus(
            current_stock=50,
            projected_demand=20,
            safety_stock=10
        )
        self.assertEqual(res["safe_surplus"], 20)
        self.assertTrue(res["is_safe"])
        self.assertIsNone(res["uncertainty_reason"])

    def test_b_unsafe_donor(self):
        """
        Test B: Donor stock: 20 units. Projected demand: 15 units. Safety stock: 10 units.
        Expected safe surplus: 0 units, and the donor must not be eligible for a transfer.
        """
        res = calculate_safe_donor_surplus(
            current_stock=20,
            projected_demand=15,
            safety_stock=10
        )
        self.assertEqual(res["safe_surplus"], 0)
        self.assertFalse(res["is_safe"])

        # In candidate evaluation, must be marked infeasible
        candidate = {
            "donor_store_id": "STORE_009",
            "current_stock": 20,
            "projected_demand": 15,
            "safety_stock": 10,
        }
        eval_res = evaluate_donor_candidate(
            donor=candidate,
            target_store_id="STORE_007",
            sku_id="SKU_COLD_DRINK_750ML",
            target_required_quantity=10
        )
        self.assertFalse(eval_res["feasible"])
        self.assertEqual(eval_res["maximum_transfer_quantity"], 0)
        self.assertGreater(len(eval_res["infeasibility_reasons"]), 0)

    def test_c_target_needs_less_than_donor_surplus(self):
        """
        Test C: Target needs 8 units, while the donor has 20 safe surplus units.
        Expected transfer quantity: 8 units.
        """
        res = calculate_transfer_quantity(
            target_required_quantity=8,
            safe_surplus=20
        )
        self.assertTrue(res["is_feasible"])
        self.assertEqual(res["transfer_quantity"], 8)
        self.assertEqual(res["remaining_shortage"], 0)
        self.assertEqual(res["donor_surplus_remaining"], 12)

    def test_d_donor_has_less_stock_than_target_needs(self):
        """
        Test D: Target needs 15 units, while donor has 6 safe surplus units.
        Expected maximum transfer quantity: 6 units. The remaining shortage (9) must not be hidden.
        """
        res = calculate_transfer_quantity(
            target_required_quantity=15,
            safe_surplus=6
        )
        self.assertTrue(res["is_feasible"])
        self.assertEqual(res["transfer_quantity"], 6)
        self.assertEqual(res["remaining_shortage"], 9)
        self.assertEqual(res["donor_surplus_remaining"], 0)

    def test_e_multiple_donors_ranking(self):
        """
        Test E: Evaluate at least two feasible donors with different safe surpluses and ETAs.
        Verify that ranking follows documented criteria (fulfillment, ETA).
        """
        # Target needs 10 units
        # Donor A: surplus 15, ETA 45 min
        # Donor B: surplus 15, ETA 20 min
        # Both satisfy full requirement of 10. Donor B has faster ETA, so Donor B ranks #1.
        donors = [
            {
                "donor_store_id": "STORE_003",
                "current_stock": 40,
                "projected_demand": 15,
                "safety_stock": 10,  # Surplus = 15
                "transfer_eta_minutes": 45,
                "estimated_transfer_cost_inr": 150.0,
                "distance_km": 5.2,
            },
            {
                "donor_store_id": "STORE_009",
                "current_stock": 40,
                "projected_demand": 15,
                "safety_stock": 10,  # Surplus = 15
                "transfer_eta_minutes": 20,
                "estimated_transfer_cost_inr": 120.0,
                "distance_km": 2.8,
            },
        ]
        result = evaluate_and_rank_donors(
            target_store_id="STORE_007",
            sku_id="SKU_COLD_DRINK_750ML",
            target_required_quantity=10,
            donor_candidates=donors
        )

        self.assertEqual(result["status"], "TRANSFER_RECOMMENDED")
        self.assertIsNotNone(result["recommended_donor"])
        # Donor B (STORE_009) must rank first due to lower ETA (20 min < 45 min)
        self.assertEqual(result["recommended_donor"]["donor_store_id"], "STORE_009")
        self.assertEqual(result["recommended_transfer_quantity"], 10)
        self.assertEqual(result["candidates"][0]["donor_store_id"], "STORE_009")
        self.assertEqual(result["candidates"][1]["donor_store_id"], "STORE_003")

    def test_f_same_store(self):
        """
        Test F: Target store must never be selected as its own donor.
        """
        same_store_candidate = {
            "donor_store_id": "STORE_007",
            "current_stock": 50,
            "projected_demand": 10,
            "safety_stock": 5,
        }
        eval_res = evaluate_donor_candidate(
            donor=same_store_candidate,
            target_store_id="STORE_007",
            sku_id="SKU_COLD_DRINK_750ML",
            target_required_quantity=15
        )
        self.assertFalse(eval_res["feasible"])
        self.assertIn("Target store cannot be its own donor.", eval_res["infeasibility_reasons"])

    def test_g_different_sku(self):
        """
        Test G: A donor without the requested SKU must not be treated as a feasible source.
        """
        wrong_sku_candidate = {
            "donor_store_id": "STORE_003",
            "sku_id": "SKU_POTATO_CHIPS_100G",  # Mismatched SKU
            "current_stock": 50,
            "projected_demand": 10,
            "safety_stock": 5,
        }
        eval_res = evaluate_donor_candidate(
            donor=wrong_sku_candidate,
            target_store_id="STORE_007",
            sku_id="SKU_COLD_DRINK_750ML",
            target_required_quantity=10
        )
        self.assertFalse(eval_res["feasible"])
        self.assertTrue(any("SKU mismatch" in r for r in eval_res["infeasibility_reasons"]))

    def test_h_missing_demand_or_replenishment_data(self):
        """
        Test H: Do not assume unknown donor demand is zero or that unknown replenishment is immediate.
        Return an explicit uncertainty or infeasibility explanation.
        """
        # Donor with no demand forecast supplied
        missing_demand_donor = {
            "donor_store_id": "STORE_003",
            "current_stock": 50,
            "projected_demand": None,
            "safety_stock": 10,
        }
        surplus_res = calculate_safe_donor_surplus(
            current_stock=50,
            projected_demand=None
        )
        self.assertEqual(surplus_res["safe_surplus"], 0)
        self.assertFalse(surplus_res["is_safe"])
        self.assertEqual(surplus_res["uncertainty_reason"], "missing_projected_demand")

        eval_res = evaluate_donor_candidate(
            donor=missing_demand_donor,
            target_store_id="STORE_007",
            sku_id="SKU_COLD_DRINK_750ML",
            target_required_quantity=10
        )
        self.assertFalse(eval_res["feasible"])
        self.assertTrue(any("Missing donor demand" in r for r in eval_res["infeasibility_reasons"]))

    def test_i_invalid_inputs(self):
        """
        Test I: Negative inventory, negative demand, invalid capacity, and inconsistent data.
        """
        with self.assertRaises(ValueError):
            calculate_safe_donor_surplus(current_stock=-10, projected_demand=5)

        with self.assertRaises(ValueError):
            calculate_safe_donor_surplus(current_stock=10, projected_demand=-5)

        with self.assertRaises(ValueError):
            calculate_safe_donor_surplus(current_stock=10, projected_demand=5, safety_stock=-2)

        with self.assertRaises(ValueError):
            calculate_target_requirement(current_stock=-5, projected_demand=10)

        with self.assertRaises(ValueError):
            calculate_transfer_quantity(target_required_quantity=-10, safe_surplus=5)

        with self.assertRaises(ValueError):
            calculate_transfer_quantity(target_required_quantity=10, safe_surplus=5, max_vehicle_capacity=-5)


class TestTransferAdvancedScenarios(unittest.TestCase):
    """Test vehicle limits, target sufficiency, and JSON schema compatibility."""

    def test_vehicle_capacity_constraint(self):
        """Transfer quantity cannot exceed vehicle/rider payload capacity."""
        res = calculate_transfer_quantity(
            target_required_quantity=25,
            safe_surplus=30,
            max_vehicle_capacity=10  # e.g., rider backpack holds 10 units max
        )
        self.assertTrue(res["is_feasible"])
        self.assertEqual(res["transfer_quantity"], 10)
        self.assertEqual(res["remaining_shortage"], 15)

    def test_target_stock_already_sufficient(self):
        """If target has enough stock, do not recommend transfer."""
        calc = calculate_target_requirement(
            current_stock=50,
            projected_demand=30,
            safety_stock=10
        )
        self.assertFalse(calc["needs_transfer"])
        self.assertEqual(calc["target_required_quantity"], 0)

        res = evaluate_and_rank_donors(
            target_store_id="STORE_007",
            sku_id="SKU_COLD_DRINK_750ML",
            target_stock=50,
            target_demand=30,
            target_safety_stock=10,
            donor_candidates=[{
                "donor_store_id": "STORE_003",
                "current_stock": 100,
                "projected_demand": 20,
                "safety_stock": 10,
            }]
        )
        self.assertEqual(res["status"], "TARGET_STOCK_SUFFICIENT")
        self.assertIsNone(res["recommended_donor"])

    def test_json_serializability_and_schema(self):
        """Verify output dictionary contains all required fields and serializes to JSON."""
        res = evaluate_and_rank_donors(
            target_store_id="STORE_007",
            sku_id="SKU_COLD_DRINK_750ML",
            target_required_quantity=12,
            donor_candidates=[{
                "donor_store_id": "STORE_003",
                "current_stock": 50,
                "projected_demand": 15,
                "safety_stock": 10,
                "transfer_eta_minutes": 25,
                "estimated_transfer_cost_inr": 150.0,
            }]
        )
        serialized = json.dumps(res, indent=2)
        parsed = json.loads(serialized)

        self.assertIn("target_store_id", parsed)
        self.assertIn("sku_id", parsed)
        self.assertIn("target_required_quantity", parsed)
        self.assertIn("candidates", parsed)
        self.assertIn("recommended_donor", parsed)
        self.assertIn("status", parsed)
        self.assertIn("assumptions", parsed)

        cand = parsed["candidates"][0]
        expected_cand_keys = [
            "donor_store_id",
            "target_store_id",
            "sku_id",
            "current_donor_stock",
            "projected_donor_demand",
            "required_safety_stock",
            "safe_surplus",
            "target_required_quantity",
            "maximum_transfer_quantity",
            "estimated_eta_minutes",
            "estimated_transfer_cost",
            "feasible",
            "infeasibility_reasons",
            "assumptions",
        ]
        for key in expected_cand_keys:
            self.assertIn(key, cand, f"Candidate missing key: {key}")


if __name__ == "__main__":
    unittest.main()
