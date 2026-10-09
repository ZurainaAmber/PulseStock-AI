"""
PulseStock AI - Unit Test Suite for Shelf-Space Constraints & Shelf-Swap Feasibility
Task 5: Shelf-Space Constraints Engine Tests (Tests A through I)
"""

import json
import os
import sys
import unittest

# Ensure project root is in sys.path
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from engine.constraints import (
    calculate_available_shelf_capacity,
    validate_direct_placement,
    evaluate_shelf_swap,
    evaluate_shelf_and_transfer_feasibility,
)


class TestShelfConstraintsRequirements(unittest.TestCase):
    """
    Verification of required test cases A through I specified in Task 5 prompt.
    """

    def test_a_enough_space(self):
        """
        Test A: Capacity: 20 units. Occupancy: 12 units. Proposed quantity: 8 units.
        Expected: direct placement is feasible.
        """
        res = validate_direct_placement(
            shelf_capacity=20,
            current_occupancy=12,
            proposed_quantity=8
        )
        self.assertTrue(res["direct_placement_feasible"])
        self.assertEqual(res["direct_placement_quantity"], 8)
        self.assertEqual(res["available_shelf_capacity"], 8)
        self.assertEqual(res["unplaced_quantity"], 0)

        # Full combined evaluation check
        eval_res = evaluate_shelf_and_transfer_feasibility(
            shelf_capacity=20,
            current_occupancy=12,
            proposed_transfer_quantity=8
        )
        self.assertTrue(eval_res["direct_placement_feasible"])
        self.assertTrue(eval_res["placement_feasible"])
        self.assertEqual(eval_res["direct_placement_quantity"], 8)
        self.assertFalse(eval_res["shelf_swap_possible"])  # Not needed

    def test_b_full_shelf(self):
        """
        Test B: Capacity: 20 units. Occupancy: 20 units. Proposed quantity: 8 units.
        Expected: direct placement is infeasible and available capacity is zero.
        """
        res = validate_direct_placement(
            shelf_capacity=20,
            current_occupancy=20,
            proposed_quantity=8
        )
        self.assertFalse(res["direct_placement_feasible"])
        self.assertEqual(res["available_shelf_capacity"], 0)
        self.assertEqual(res["direct_placement_quantity"], 0)
        self.assertEqual(res["unplaced_quantity"], 8)
        self.assertGreater(len(res["infeasibility_reasons"]), 0)

    def test_c_partial_space(self):
        """
        Test C: Capacity: 20 units. Occupancy: 16 units. Proposed quantity: 8 units.
        Expected: at most 4 units can be placed directly on the shelf. Must not claim all 8 fit.
        """
        res = validate_direct_placement(
            shelf_capacity=20,
            current_occupancy=16,
            proposed_quantity=8
        )
        self.assertFalse(res["direct_placement_feasible"])
        self.assertEqual(res["available_shelf_capacity"], 4)
        self.assertEqual(res["direct_placement_quantity"], 4)
        self.assertEqual(res["unplaced_quantity"], 4)
        self.assertNotEqual(res["direct_placement_quantity"], 8)
        self.assertIn("Partial space available", res["infeasibility_reasons"][0])

    def test_d_feasible_shelf_swap(self):
        """
        Test D: Capacity: 20 units. Occupancy: 20 units.
        A compatible, movable product occupying 6 units can be moved to an alternative location with confirmed capacity.
        Proposed target quantity: 6 units.
        Expected: swap frees 6 units of shelf capacity, making target placement feasible.
        """
        products = [
            {
                "sku_id": "SKU_SLOW_DRINK_500ML",
                "units": 6,
                "is_movable": True,
                "is_compatible_with_alternative": True,
                "alternative_capacity": 10,  # Confirmed capacity
                "priority": "LOW",
                "destination": "BACKROOM_BEVERAGE_BAY_1",
            }
        ]
        swap_res = evaluate_shelf_swap(
            shelf_capacity=20,
            current_occupancy=20,
            target_sku_id="SKU_COLD_DRINK_750ML",
            needed_space=6,
            existing_shelf_products=products
        )
        self.assertTrue(swap_res["shelf_swap_possible"])
        self.assertEqual(swap_res["space_freed"], 6)
        self.assertEqual(len(swap_res["products_moved"]), 1)
        self.assertEqual(swap_res["products_moved"][0]["sku_id"], "SKU_SLOW_DRINK_500ML")
        self.assertEqual(swap_res["products_moved"][0]["units_moved"], 6)

        # Full combined evaluation check
        eval_res = evaluate_shelf_and_transfer_feasibility(
            shelf_capacity=20,
            current_occupancy=20,
            proposed_transfer_quantity=6,
            existing_shelf_products=products
        )
        self.assertFalse(eval_res["direct_placement_feasible"])
        self.assertTrue(eval_res["shelf_swap_possible"])
        self.assertTrue(eval_res["placement_feasible"])
        self.assertEqual(eval_res["space_freed_by_swap"], 6)
        self.assertEqual(eval_res["quantity_after_swap"], 6)

    def test_e_no_alternative_capacity(self):
        """
        Test E: The proposed swap displaces a product, but no suitable alternative capacity is available.
        Expected: swap is infeasible.
        """
        products = [
            {
                "sku_id": "SKU_SLOW_DRINK_500ML",
                "units": 6,
                "is_movable": True,
                "is_compatible_with_alternative": True,
                "alternative_capacity": 0,  # No alternative capacity
            }
        ]
        swap_res = evaluate_shelf_swap(
            shelf_capacity=20,
            current_occupancy=20,
            target_sku_id="SKU_COLD_DRINK_750ML",
            needed_space=6,
            existing_shelf_products=products
        )
        self.assertFalse(swap_res["shelf_swap_possible"])
        self.assertEqual(swap_res["space_freed"], 0)
        self.assertGreater(len(swap_res["infeasibility_reasons"]), 0)

        # Combined check
        eval_res = evaluate_shelf_and_transfer_feasibility(
            shelf_capacity=20,
            current_occupancy=20,
            proposed_transfer_quantity=6,
            existing_shelf_products=products
        )
        self.assertFalse(eval_res["placement_feasible"])
        self.assertFalse(eval_res["shelf_swap_possible"])

    def test_f_insufficient_swap_space(self):
        """
        Test F: Target needs 8 units of space, but the maximum valid swap frees only 5 units.
        Expected: system must not claim all 8 units fit. Return an infeasible / partial result.
        """
        products = [
            {
                "sku_id": "SKU_SLOW_DRINK_500ML",
                "units": 5,  # Only 5 units available to swap
                "is_movable": True,
                "alternative_capacity": 10,
            }
        ]
        swap_res = evaluate_shelf_swap(
            shelf_capacity=20,
            current_occupancy=20,
            target_sku_id="SKU_COLD_DRINK_750ML",
            needed_space=8,
            existing_shelf_products=products
        )
        self.assertFalse(swap_res["shelf_swap_possible"])
        self.assertEqual(swap_res["space_freed"], 5)
        self.assertNotEqual(swap_res["space_freed"], 8)
        self.assertIn("Insufficient swap space", swap_res["infeasibility_reasons"][0])

        # Combined check
        eval_res = evaluate_shelf_and_transfer_feasibility(
            shelf_capacity=20,
            current_occupancy=20,
            proposed_transfer_quantity=8,
            existing_shelf_products=products
        )
        self.assertFalse(eval_res["placement_feasible"])
        self.assertEqual(eval_res["quantity_after_swap"], 5)  # Can place at most 5

    def test_g_invalid_capacity(self):
        """
        Test G: Test negative capacity, negative occupancy, and occupancy exceeding capacity.
        Expected: reject invalid input with meaningful ValueError.
        """
        # Negative capacity
        with self.assertRaises(ValueError):
            calculate_available_shelf_capacity(shelf_capacity=-20, current_occupancy=10)

        # Negative occupancy
        with self.assertRaises(ValueError):
            calculate_available_shelf_capacity(shelf_capacity=20, current_occupancy=-5)

        # Occupancy exceeding capacity
        with self.assertRaises(ValueError) as ctx:
            calculate_available_shelf_capacity(shelf_capacity=20, current_occupancy=25)
        self.assertIn("exceed", str(ctx.exception).lower())

        # Negative proposed quantity
        with self.assertRaises(ValueError):
            validate_direct_placement(shelf_capacity=20, current_occupancy=10, proposed_quantity=-4)

    def test_h_product_compatibility(self):
        """
        Test H: Product cannot be moved to the proposed alternative location because of an explicit
        compatibility restriction (is_compatible_with_alternative = False).
        Expected: reject that swap.
        """
        products = [
            {
                "sku_id": "SKU_COLD_DAIRY_1L",
                "units": 6,
                "is_movable": True,
                "is_compatible_with_alternative": False,  # Incompatible (e.g. ambient backroom for dairy)
                "alternative_capacity": 10,
            }
        ]
        swap_res = evaluate_shelf_swap(
            shelf_capacity=20,
            current_occupancy=20,
            target_sku_id="SKU_COLD_DRINK_750ML",
            needed_space=6,
            existing_shelf_products=products
        )
        self.assertFalse(swap_res["shelf_swap_possible"])
        self.assertEqual(swap_res["space_freed"], 0)

    def test_i_transfer_limit(self):
        """
        Test I: Target needs 10 units, but Task 4 permits only 6 safe transferable units.
        Expected: shelf-space logic must not increase the transferable quantity beyond the safe limit of 6.
        """
        # Even with capacity = 50 and occupancy = 0 (50 units free),
        # safe_transfer_limit = 6 caps the proposed quantity at 6.
        eval_res = evaluate_shelf_and_transfer_feasibility(
            shelf_capacity=50,
            current_occupancy=0,
            proposed_transfer_quantity=10,
            safe_transfer_limit=6
        )
        self.assertEqual(eval_res["proposed_quantity"], 6)
        self.assertEqual(eval_res["direct_placement_quantity"], 6)
        self.assertEqual(eval_res["quantity_after_swap"], 6)
        self.assertTrue(eval_res["safe_transfer_limit_applied"])
        self.assertTrue(eval_res["placement_feasible"])


class TestShelfConstraintsAdvanced(unittest.TestCase):
    """Test multi-product swap priority, slots-per-unit, and JSON schema compliance."""

    def test_multiple_products_swap_with_priority(self):
        """Support swapping multiple products, moving lower-priority products first."""
        products = [
            {
                "sku_id": "SKU_HIGH_PRIO_WATER",
                "units": 4,
                "priority": "HIGH",
                "is_movable": True,
                "alternative_capacity": 10,
            },
            {
                "sku_id": "SKU_LOW_PRIO_CANDY",
                "units": 4,
                "priority": "LOW",
                "is_movable": True,
                "alternative_capacity": 10,
            },
            {
                "sku_id": "SKU_MED_PRIO_GUM",
                "units": 4,
                "priority": "MEDIUM",
                "is_movable": True,
                "alternative_capacity": 10,
            },
        ]
        # Needed space = 6. Should move all 4 units of LOW prio, then 2 units of MED prio.
        swap_res = evaluate_shelf_swap(
            shelf_capacity=20,
            current_occupancy=20,
            target_sku_id="SKU_COLD_DRINK_750ML",
            needed_space=6,
            existing_shelf_products=products
        )
        self.assertTrue(swap_res["shelf_swap_possible"])
        self.assertEqual(swap_res["space_freed"], 6)
        moved_skus = [p["sku_id"] for p in swap_res["products_moved"]]
        self.assertEqual(moved_skus[0], "SKU_LOW_PRIO_CANDY")
        self.assertEqual(moved_skus[1], "SKU_MED_PRIO_GUM")
        self.assertNotIn("SKU_HIGH_PRIO_WATER", moved_skus)

    def test_slots_per_unit_consumption(self):
        """Large items consume multiple shelf slots per unit."""
        # Shelf capacity = 20 slots. Occupancy = 10 slots. Available = 10 slots.
        # Target item consumes 2 slots per unit.
        # Max units that fit = floor(10 / 2) = 5 units.
        cap_info = calculate_available_shelf_capacity(
            shelf_capacity=20,
            current_occupancy=10,
            slots_per_unit=2
        )
        self.assertEqual(cap_info["available_shelf_capacity"], 10)
        self.assertEqual(cap_info["available_units"], 5)

    def test_json_serializability_and_schema_keys(self):
        """Verify output dictionary contains all required fields and serializes to JSON."""
        res = evaluate_shelf_and_transfer_feasibility(
            target_store_id="STORE_007",
            sku_id="SKU_COLD_DRINK_750ML",
            shelf_capacity=20,
            current_occupancy=16,
            proposed_transfer_quantity=8,
            existing_shelf_products=[{
                "sku_id": "SKU_SLOW_DRINK",
                "units": 4,
                "alternative_capacity": 10,
            }]
        )
        serialized = json.dumps(res, indent=2)
        parsed = json.loads(serialized)

        expected_keys = [
            "store_id",
            "sku_id",
            "shelf_capacity",
            "current_shelf_occupancy",
            "available_shelf_capacity",
            "proposed_quantity",
            "direct_placement_quantity",
            "direct_placement_feasible",
            "shelf_swap_possible",
            "space_freed_by_swap",
            "quantity_after_swap",
            "placement_feasible",
            "infeasibility_reasons",
            "assumptions",
        ]
        for key in expected_keys:
            self.assertIn(key, parsed, f"Missing required key: {key}")


if __name__ == "__main__":
    unittest.main()
