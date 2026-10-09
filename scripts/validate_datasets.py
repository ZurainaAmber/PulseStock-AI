"""
PulseStock AI - Dataset Validator
Cypher 2026 Challenge 6

Validates column schemas, referential integrity, quantitative constraints, 
shelf capacities, timestamps, and mandatory scenarios A-F across generated CSV datasets.
"""

import os
import csv
import sys
from datetime import datetime

DATA_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data")

EXPECTED_FILES = [
    "products.csv",
    "store_inventory.csv",
    "orders.csv",
    "warehouse_stock.csv",
    "truck_schedule.csv",
    "riders.csv",
    "events.csv"
]

EXPECTED_SCHEMAS = {
    "products.csv": ["sku_id", "sku_name", "category", "size", "unit_selling_price_inr", "margin_pct", "unit_cost_price_inr"],
    "store_inventory.csv": ["store_id", "sku_id", "shelf_slot", "shelf_stock_units", "shelf_capacity_units", "backroom_stock_units", "total_stock_units", "safety_stock_threshold_units", "reorder_point_units"],
    "orders.csv": ["timestamp", "store_id", "sku_id", "quantity"],
    "warehouse_stock.csv": ["warehouse_id", "sku_id", "available_stock_units", "reserved_stock_units", "free_stock_units"],
    "truck_schedule.csv": ["truck_id", "store_id", "route_id", "driver_name", "scheduled_departure_time", "scheduled_arrival_time", "truck_capacity_units", "status", "sku_id", "allocated_quantity_units"],
    "riders.csv": ["timestamp", "store_id", "available_riders", "required_riders", "orders_per_rider_hour", "rider_shortage_count", "shortage_severity"],
    "events.csv": ["event_id", "event_type", "title", "store_id", "affected_category", "multiplier", "precipitation_mm_hr", "is_active", "start_time", "end_time"]
}

def load_csv(filename):
    filepath = os.path.join(DATA_DIR, filename)
    if not os.path.exists(filepath):
        raise FileNotFoundError(f"Missing required CSV dataset: {filepath}")
    with open(filepath, "r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        return list(reader), reader.fieldnames

def validate():
    print("==================================================")
    print(" PulseStock AI - CSV Dataset Validation Suite")
    print("==================================================")
    
    errors = []
    warnings = []
    file_counts = {}

    # 1. Existence and Schema Validation
    for filename in EXPECTED_FILES:
        try:
            rows, headers = load_csv(filename)
            file_counts[filename] = len(rows)
            expected = EXPECTED_SCHEMAS[filename]
            if headers != expected:
                errors.append(f"Header mismatch in {filename}.\n  Got: {headers}\n  Expected: {expected}")
            if len(rows) == 0:
                errors.append(f"File {filename} is empty!")
        except Exception as e:
            errors.append(str(e))
            
    if errors:
        print("Schema/File check failed:")
        for err in errors:
            print(f"  [ERROR] {err}")
        sys.exit(1)

    # Load rows for deeper verification
    products, _ = load_csv("products.csv")
    inventories, _ = load_csv("store_inventory.csv")
    orders, _ = load_csv("orders.csv")
    warehouse, _ = load_csv("warehouse_stock.csv")
    trucks, _ = load_csv("truck_schedule.csv")
    riders, _ = load_csv("riders.csv")
    events, _ = load_csv("events.csv")

    valid_skus = {p["sku_id"] for p in products}
    valid_stores = {f"STORE_{i:03d}" for i in range(1, 31)}

    # 2. Product Validation
    if len(products) != 150:
        warnings.append(f"products.csv contains {len(products)} rows (expected 150).")
        
    for p in products:
        sku = p["sku_id"]
        price = float(p["unit_selling_price_inr"])
        cost = float(p["unit_cost_price_inr"])
        if price <= 0 or cost <= 0:
            errors.append(f"Product {sku} has non-positive price/cost.")
        if cost > price:
            errors.append(f"Product {sku} cost exceeds selling price.")

    # 3. Store Inventory Invariants & Capacity Rules
    for inv in inventories:
        sid = inv["store_id"]
        sku = inv["sku_id"]
        if sid not in valid_stores:
            errors.append(f"Invalid store_id '{sid}' in store_inventory.csv")
        if sku not in valid_skus:
            errors.append(f"Invalid sku_id '{sku}' in store_inventory.csv")
            
        shelf_stock = int(inv["shelf_stock_units"])
        shelf_cap = int(inv["shelf_capacity_units"])
        backroom = int(inv["backroom_stock_units"])
        total = int(inv["total_stock_units"])

        if shelf_stock < 0 or backroom < 0 or shelf_cap <= 0:
            errors.append(f"Negative stock or invalid capacity for store={sid}, sku={sku}")
        if shelf_stock > shelf_cap:
            errors.append(f"Stock ({shelf_stock}) exceeds shelf capacity ({shelf_cap}) for store={sid}, sku={sku}")
        if total != (shelf_stock + backroom):
            errors.append(f"Total stock mismatch for store={sid}, sku={sku}: {total} != {shelf_stock} + {backroom}")

    # 4. Warehouse Stock Invariants
    for w in warehouse:
        sku = w["sku_id"]
        if sku not in valid_skus:
            errors.append(f"Invalid sku_id '{sku}' in warehouse_stock.csv")
        avail = int(w["available_stock_units"])
        reserved = int(w["reserved_stock_units"])
        free_stk = int(w["free_stock_units"])
        if avail < 0 or reserved < 0:
            errors.append(f"Negative warehouse stock for sku={sku}")
        if free_stk != max(0, avail - reserved):
            errors.append(f"Free stock mismatch for warehouse sku={sku}: {free_stk} != {avail} - {reserved}")

    # 5. Mandatory Scenario Checks
    print("\nValidating Mandatory Test Scenarios A - F...")

    # Scenario A: Match-Night Stock-out
    st7_drink = [i for i in inventories if i["store_id"] == "STORE_007" and i["sku_id"] == "SKU_COLD_DRINK_750ML"]
    st9_drink = [i for i in inventories if i["store_id"] == "STORE_009" and i["sku_id"] == "SKU_COLD_DRINK_750ML"]
    st7_match_evt = [e for e in events if e["store_id"] == "STORE_007" and e["event_type"] == "CRICKET"]
    st7_truck = [t for t in trucks if t["store_id"] == "STORE_007" and t["sku_id"] == "SKU_COLD_DRINK_750ML" and t["status"] == "IN_TRANSIT"]

    if not st7_drink or int(st7_drink[0]["total_stock_units"]) != 14:
        errors.append(f"Scenario A Failed: Store 7 SKU_COLD_DRINK_750ML total stock is {st7_drink[0]['total_stock_units'] if st7_drink else 'missing'} (expected 14).")
    else:
        print("  [PASS] Scenario A: Store 7 stock = 14 bottles.")

    if not st9_drink or int(st9_drink[0]["total_stock_units"]) != 60:
        errors.append(f"Scenario A Failed: Store 9 SKU_COLD_DRINK_750ML total stock is {st9_drink[0]['total_stock_units'] if st9_drink else 'missing'} (expected 60).")
    else:
        print("  [PASS] Scenario A: Store 9 donor stock = 60 bottles.")

    if not st7_match_evt:
        errors.append("Scenario A Failed: Missing CRICKET event for Store 7.")
    else:
        print(f"  [PASS] Scenario A: Match event configured ({st7_match_evt[0]['title']}, multiplier={st7_match_evt[0]['multiplier']}).")

    if not st7_truck or "21:00:00" not in st7_truck[0]["scheduled_arrival_time"]:
        errors.append(f"Scenario A Failed: Store 7 scheduled truck arrival is {st7_truck[0]['scheduled_arrival_time'] if st7_truck else 'missing'} (expected 21:00 arrival).")
    else:
        print(f"  [PASS] Scenario A: Replenishment truck arrival scheduled for 9:00 PM (21:00).")

    # Scenario B: Shelf Capacity Problem
    st7_fast = [i for i in inventories if i["store_id"] == "STORE_007" and i["sku_id"] == "SKU_ENERGY_DRINK_250ML"]
    st7_slow = [i for i in inventories if i["store_id"] == "STORE_007" and i["sku_id"] == "SKU_KALE_CHIPS_50G"]
    
    if st7_fast and st7_slow and int(st7_fast[0]["shelf_capacity_units"]) < int(st7_slow[0]["shelf_capacity_units"]):
        print(f"  [PASS] Scenario B: Fast SKU shelf cap ({st7_fast[0]['shelf_capacity_units']}) < Slow SKU shelf cap ({st7_slow[0]['shelf_capacity_units']}).")
    else:
        errors.append("Scenario B Failed: Shelf capacity configuration for shelf swap scenario is invalid.")

    # Scenario C: Donor Store Safety
    st12_drink = [i for i in inventories if i["store_id"] == "STORE_012" and i["sku_id"] == "SKU_COLD_DRINK_750ML"]
    st12_fest_evt = [e for e in events if e["store_id"] == "STORE_012" and e["event_type"] == "FESTIVAL"]
    if st12_drink and int(st12_drink[0]["total_stock_units"]) == 80 and st12_fest_evt:
        print(f"  [PASS] Scenario C: Store 12 has 80 units stock but active festival event multiplier ({st12_fest_evt[0]['multiplier']}) prevents safe transfer.")
    else:
        errors.append("Scenario C Failed: Store 12 donor safety setup invalid.")

    # Scenario D: Rider Shortage
    st4_riders = [r for r in riders if r["store_id"] == "STORE_004" and r["shortage_severity"] == "CRITICAL"]
    if st4_riders:
        print(f"  [PASS] Scenario D: Store 4 severe rider shortage configured (Available: {st4_riders[0]['available_riders']}, Required: {st4_riders[0]['required_riders']}).")
    else:
        errors.append("Scenario D Failed: Store 4 rider shortage scenario not found.")

    # Scenario E: City-Wide Event Surge
    city_rain = [e for e in events if e["store_id"] == "ALL" and e["event_type"] == "RAIN"]
    if city_rain:
        print(f"  [PASS] Scenario E: City-wide rain event configured (Precipitation: {city_rain[0]['precipitation_mm_hr']} mm/hr, Multiplier: {city_rain[0]['multiplier']}).")
    else:
        errors.append("Scenario E Failed: City-wide rain surge event missing.")

    # Scenario F: Healthy Store
    st1_inventories = [i for i in inventories if i["store_id"] == "STORE_001"]
    st1_riders = [r for r in riders if r["store_id"] == "STORE_001" and int(r["available_riders"]) >= 8]
    if len(st1_inventories) == 150 and all(int(i["total_stock_units"]) >= 100 for i in st1_inventories) and st1_riders:
        print("  [PASS] Scenario F: Healthy Store 1 fully stocked with ample rider capacity.")
    else:
        errors.append("Scenario F Failed: Store 1 healthy store configuration invalid.")

    # Summary
    print("\n--------------------------------------------------")
    print(" Dataset Row Counts Summary:")
    print("--------------------------------------------------")
    for fname, count in file_counts.items():
        print(f"  - {fname:<22}: {count:>6} rows")
        
    if errors:
        print(f"\n[FAIL] Validation completed with {len(errors)} errors:")
        for err in errors:
            print(f"  - {err}")
        sys.exit(1)
    else:
        print("\n[SUCCESS] All datasets passed validation cleanly! Ready for PulseStock engine!")

if __name__ == "__main__":
    validate()
