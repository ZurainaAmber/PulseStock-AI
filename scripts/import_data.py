"""
PulseStock AI - Database Data Importer
Cypher 2026 Challenge 6

Imports all 7 CSV datasets from data/ into the SQLite database backend/pulsestock.db
using backend database models and configurations.
Idempotent and safe to re-run multiple times without data duplication.
"""

import os
import csv
import sys
from datetime import datetime

# Add project root to sys.path
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

try:
    from backend.database import SessionLocal, init_db, Base, engine
    from backend.models import (
        Store, SKU, StoreInventory, ExternalEvent,
        StockoutAlert, Recommendation, ActionLog,
        Order, WarehouseStock, TruckSchedule, RiderAvailability
    )
    from scripts.generate_datasets import STORES
except ImportError as e:
    print(f"Import error: {e}")
    sys.exit(1)

DATA_DIR = os.path.join(PROJECT_ROOT, "data")

def parse_datetime(dt_str):
    if not dt_str:
        return None
    try:
        # Handle ISO strings with timezone or space
        return datetime.fromisoformat(dt_str.replace("Z", "+00:00"))
    except ValueError:
        return datetime.strptime(dt_str[:19], "%Y-%m-%d %H:%M:%S")

def import_all():
    print("==================================================")
    print(" PulseStock AI - Database Import Engine")
    print("==================================================")

    # Recreate tables to ensure SQLite schema matches updated models
    print("Synchronizing database table schemas...")
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()

    try:
        # 2. Import Stores
        print("Importing Stores (30 dark stores master)...")
        store_objs = []
        for s in STORES:
            store_objs.append(Store(
                store_id=s["store_id"],
                store_name=s["store_name"],
                location_zone=s["location_zone"],
                stadium_proximity_km=float(s["stadium_proximity_km"]),
                created_at=datetime.utcnow()
            ))
        db.bulk_save_objects(store_objs)
        db.commit()
        print(f"  -> Imported {len(store_objs)} store records.")


        # 3. Import SKUs (products.csv)
        products_path = os.path.join(DATA_DIR, "products.csv")
        sku_objs = []
        with open(products_path, "r", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            for row in reader:
                sku_objs.append(SKU(
                    sku_id=row["sku_id"],
                    sku_name=row["sku_name"],
                    category=row["category"],
                    size=row.get("size"),
                    unit_selling_price_inr=float(row["unit_selling_price_inr"]),
                    margin_pct=float(row["margin_pct"]) if row.get("margin_pct") else None,
                    unit_cost_price_inr=float(row["unit_cost_price_inr"]),
                    created_at=datetime.utcnow()
                ))
        db.bulk_save_objects(sku_objs)
        db.commit()
        print(f"  -> Imported {len(sku_objs)} SKU records.")

        # 4. Import Store Inventory (store_inventory.csv)
        inventory_path = os.path.join(DATA_DIR, "store_inventory.csv")
        inv_objs = []
        with open(inventory_path, "r", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            for row in reader:
                inv_objs.append(StoreInventory(
                    store_id=row["store_id"],
                    sku_id=row["sku_id"],
                    shelf_slot=row.get("shelf_slot"),
                    shelf_stock_units=int(row["shelf_stock_units"]),
                    shelf_capacity_units=int(row["shelf_capacity_units"]),
                    backroom_stock_units=int(row["backroom_stock_units"]),
                    total_stock_units=int(row["total_stock_units"]),
                    safety_stock_threshold_units=int(row["safety_stock_threshold_units"]),
                    reorder_point_units=int(row["reorder_point_units"]),
                    updated_at=datetime.utcnow()
                ))
        db.bulk_save_objects(inv_objs)
        db.commit()
        print(f"  -> Imported {len(inv_objs)} StoreInventory records.")

        # 5. Import Warehouse Stock (warehouse_stock.csv)
        wh_path = os.path.join(DATA_DIR, "warehouse_stock.csv")
        wh_objs = []
        with open(wh_path, "r", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            for row in reader:
                wh_objs.append(WarehouseStock(
                    warehouse_id=row["warehouse_id"],
                    sku_id=row["sku_id"],
                    available_stock_units=int(row["available_stock_units"]),
                    reserved_stock_units=int(row["reserved_stock_units"]),
                    free_stock_units=int(row["free_stock_units"])
                ))
        db.bulk_save_objects(wh_objs)
        db.commit()
        print(f"  -> Imported {len(wh_objs)} WarehouseStock records.")

        # 6. Import Truck Schedules (truck_schedule.csv)
        truck_path = os.path.join(DATA_DIR, "truck_schedule.csv")
        truck_objs = []
        with open(truck_path, "r", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            for row in reader:
                truck_objs.append(TruckSchedule(
                    truck_id=row["truck_id"],
                    store_id=row["store_id"],
                    route_id=row["route_id"],
                    driver_name=row["driver_name"],
                    scheduled_departure_time=parse_datetime(row["scheduled_departure_time"]),
                    scheduled_arrival_time=parse_datetime(row["scheduled_arrival_time"]),
                    truck_capacity_units=int(row["truck_capacity_units"]),
                    status=row["status"],
                    sku_id=row["sku_id"],
                    allocated_quantity_units=int(row["allocated_quantity_units"])
                ))
        db.bulk_save_objects(truck_objs)
        db.commit()
        print(f"  -> Imported {len(truck_objs)} TruckSchedule records.")

        # 7. Import Riders Availability (riders.csv)
        riders_path = os.path.join(DATA_DIR, "riders.csv")
        rider_objs = []
        with open(riders_path, "r", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            for row in reader:
                rider_objs.append(RiderAvailability(
                    timestamp=parse_datetime(row["timestamp"]),
                    store_id=row["store_id"],
                    available_riders=int(row["available_riders"]),
                    required_riders=int(row["required_riders"]),
                    orders_per_rider_hour=float(row["orders_per_rider_hour"]),
                    rider_shortage_count=int(row["rider_shortage_count"]),
                    shortage_severity=row["shortage_severity"]
                ))
        db.bulk_save_objects(rider_objs)
        db.commit()
        print(f"  -> Imported {len(rider_objs)} RiderAvailability records.")

        # 8. Import External Events (events.csv)
        events_path = os.path.join(DATA_DIR, "events.csv")
        event_objs = []
        with open(events_path, "r", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            for row in reader:
                event_objs.append(ExternalEvent(
                    event_id=row["event_id"],
                    event_type=row["event_type"],
                    title=row["title"],
                    store_id=row["store_id"] if row["store_id"] != "ALL" else None,
                    affected_category=row.get("affected_category"),
                    multiplier=float(row["multiplier"]),
                    precipitation_mm_hr=float(row["precipitation_mm_hr"]),
                    is_active=int(row["is_active"]),
                    start_time=parse_datetime(row["start_time"]),
                    end_time=parse_datetime(row["end_time"])
                ))
        db.bulk_save_objects(event_objs)
        db.commit()
        print(f"  -> Imported {len(event_objs)} ExternalEvent records.")

        # 9. Import Orders (orders.csv) - Chunked for high performance
        orders_path = os.path.join(DATA_DIR, "orders.csv")
        order_objs = []
        count = 0
        with open(orders_path, "r", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            for row in reader:
                order_objs.append(Order(
                    timestamp=parse_datetime(row["timestamp"]),
                    store_id=row["store_id"],
                    sku_id=row["sku_id"],
                    quantity=int(row["quantity"])
                ))
                if len(order_objs) >= 10000:
                    db.bulk_save_objects(order_objs)
                    db.commit()
                    count += len(order_objs)
                    order_objs = []
            if order_objs:
                db.bulk_save_objects(order_objs)
                db.commit()
                count += len(order_objs)
        print(f"  -> Imported {count} Order records.")

        # 10. Seed Initial StockoutAlert & Recommendations (Scenario A)
        alert_obj = StockoutAlert(
            alert_id="ALT_20261009_007_01",
            store_id="STORE_007",
            sku_id="SKU_COLD_DRINK_750ML",
            severity="CRITICAL",
            current_total_stock=14,
            projected_hourly_demand=9,
            stockout_probability=0.96,
            minutes_until_stockout=53,
            estimated_stockout_time=datetime(2026, 10, 9, 20, 23, 0),
            status="PENDING",
            created_at=datetime(2026, 10, 9, 17, 0, 0)
        )
        db.add(alert_obj)

        rec_objs = [
            Recommendation(
                recommendation_id="REC_007_TRF_01",
                alert_id="ALT_20261009_007_01",
                option_type="TRANSFER",
                rank=1,
                title="Inter-Store Transfer from Store 3",
                confidence_score=0.94,
                stockout_prevented=1,
                action_params_json='{"source_type": "STORE", "source_id": "STORE_003", "transfer_quantity_units": 50, "eta_minutes": 28, "estimated_arrival_timestamp": "2026-10-09T17:28:00Z"}',
                execution_cost_inr=150.0,
                revenue_saved_inr=4500.0,
                is_recommended=1,
                created_at=datetime(2026, 10, 9, 17, 0, 0)
            ),
            Recommendation(
                recommendation_id="REC_007_TRK_02",
                alert_id="ALT_20261009_007_01",
                option_type="EARLIER_TRUCK",
                rank=2,
                title="Expedite Warehouse Truck Delivery",
                confidence_score=0.88,
                stockout_prevented=1,
                action_params_json='{"source_type": "WAREHOUSE", "source_id": "WH_CENTRAL_01", "truck_id": "TRK_EXPRESS_109", "transfer_quantity_units": 100, "eta_minutes": 35, "estimated_arrival_timestamp": "2026-10-09T17:35:00Z"}',
                execution_cost_inr=350.0,
                revenue_saved_inr=4500.0,
                is_recommended=0,
                created_at=datetime(2026, 10, 9, 17, 0, 0)
            ),
            Recommendation(
                recommendation_id="REC_007_SWP_03",
                alert_id="ALT_20261009_007_01",
                option_type="SHELF_SWAP",
                rank=3,
                title="Shelf Space Swap with Diet Herbal Tea",
                confidence_score=0.75,
                stockout_prevented=0,
                action_params_json='{"source_sku_id": "SKU_DIET_HERBAL_TEA_250ML", "target_sku_id": "SKU_COLD_DRINK_750ML", "slots_reallocated": 25, "execution_time_minutes": 10}',
                execution_cost_inr=0.0,
                revenue_saved_inr=1800.0,
                is_recommended=0,
                created_at=datetime(2026, 10, 9, 17, 0, 0)
            ),
            Recommendation(
                recommendation_id="REC_007_WAT_04",
                alert_id="ALT_20261009_007_01",
                option_type="WAIT",
                rank=4,
                title="Wait for Standard Scheduled Truck",
                confidence_score=0.40,
                stockout_prevented=0,
                action_params_json='{"expected_stockout_duration_minutes": 78, "scheduled_arrival_timestamp": "2026-10-09T21:00:00Z"}',
                execution_cost_inr=0.0,
                revenue_saved_inr=0.0,
                is_recommended=0,
                created_at=datetime(2026, 10, 9, 17, 0, 0)
            )
        ]
        db.bulk_save_objects(rec_objs)
        db.commit()
        print("  -> Seeded initial StockoutAlert & Recommendation records.")


        print("\n[SUCCESS] SQLite Database successfully populated with all CSV datasets!")

    except Exception as e:
        db.rollback()
        print(f"\n[ERROR] Database import failed: {e}")
        sys.exit(1)
    finally:
        db.close()

if __name__ == "__main__":
    import_all()
