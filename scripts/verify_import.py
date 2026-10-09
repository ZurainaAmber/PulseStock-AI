"""
PulseStock AI - Database Verification Suite
Cypher 2026 Challenge 6

Verifies that imported SQLite records are intact, properly linked, and queryable.
"""

import os
import sys

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from backend.database import SessionLocal
from backend.models import (
    Store, SKU, StoreInventory, ExternalEvent,
    Order, WarehouseStock, TruckSchedule, RiderAvailability
)
from sqlalchemy import func

def verify_db():
    print("==================================================")
    print(" PulseStock AI - Database Verification Suite")
    print("==================================================")
    
    db = SessionLocal()
    try:
        # 1. Row counts check
        counts = {
            "stores": db.query(Store).count(),
            "skus": db.query(SKU).count(),
            "store_inventories": db.query(StoreInventory).count(),
            "orders": db.query(Order).count(),
            "warehouse_stock": db.query(WarehouseStock).count(),
            "truck_schedules": db.query(TruckSchedule).count(),
            "rider_availability": db.query(RiderAvailability).count(),
            "external_events": db.query(ExternalEvent).count()
        }
        
        print("\n1. Database Table Row Counts:")
        for table, count in counts.items():
            print(f"  - {table:<20}: {count:>6} records")
            assert count > 0, f"Table {table} is empty!"
            
        # 2. Verify Store linkage & coverage
        stores_with_inv = db.query(StoreInventory.store_id, func.count(StoreInventory.id))\
                            .group_by(StoreInventory.store_id).all()
        print(f"\n2. Store Coverage Check:")
        print(f"  - Total stores with inventory: {len(stores_with_inv)} / 30")
        assert len(stores_with_inv) == 30, "Not all 30 stores have inventory records!"
        for sid, inv_count in stores_with_inv:
            assert inv_count == 150, f"Store {sid} has {inv_count} SKUs (expected 150)!"

        # 3. Product & Order Join Verification
        st7_cola_inv = db.query(StoreInventory, SKU)\
                         .join(SKU, StoreInventory.sku_id == SKU.sku_id)\
                         .filter(StoreInventory.store_id == "STORE_007", SKU.sku_id == "SKU_COLD_DRINK_750ML")\
                         .first()
        
        assert st7_cola_inv is not None, "Store 7 Sparkling Cola inventory record missing!"
        inv_record, sku_record = st7_cola_inv
        print(f"\n3. Product-Inventory Linkage Check:")
        print(f"  - Store 7 SKU: {sku_record.sku_name} ({sku_record.sku_id})")
        print(f"  - Category: {sku_record.category}, Price: INR {sku_record.unit_selling_price_inr}")
        print(f"  - Stock Breakdown: Shelf={inv_record.shelf_stock_units}, Backroom={inv_record.backroom_stock_units}, Total={inv_record.total_stock_units}")

        # 4. Verify Historical Orders for Store 7 & SKU_COLD_DRINK_750ML
        order_count = db.query(Order).filter(Order.store_id == "STORE_007", Order.sku_id == "SKU_COLD_DRINK_750ML").count()
        print(f"\n4. Historical Orders Linkage Check:")
        print(f"  - Total hourly orders for Store 7 Sparkling Cola: {order_count} records")
        assert order_count > 0, "No order records found for Store 7 Sparkling Cola!"

        # 5. Events Retrieval
        events = db.query(ExternalEvent).all()
        print(f"\n5. Events Retrieval Check ({len(events)} active events):")
        for ev in events:
            print(f"  - Event '{ev.title}' ({ev.event_type}) | Store: {ev.store_id or 'ALL'} | Category: {ev.affected_category} | Multiplier: {ev.multiplier}x")

        # 6. Truck Schedules Retrieval
        st7_trucks = db.query(TruckSchedule).filter(TruckSchedule.store_id == "STORE_007").all()
        print(f"\n6. Truck Schedules Check for Store 7 ({len(st7_trucks)} trucks):")
        for trk in st7_trucks:
            print(f"  - Truck {trk.truck_id} ({trk.status}) | Driver: {trk.driver_name} | Arrival: {trk.scheduled_arrival_time} | SKU: {trk.sku_id} ({trk.allocated_quantity_units} units)")

        # 7. Rider Availability Retrieval
        st4_rider = db.query(RiderAvailability).filter(RiderAvailability.store_id == "STORE_004", RiderAvailability.shortage_severity == "CRITICAL").first()
        print(f"\n7. Rider Shortage Retrieval Check:")
        print(f"  - Store 4 Shortage Record: Avail={st4_rider.available_riders}, Req={st4_rider.required_riders}, Severity={st4_rider.shortage_severity}")

        print("\n[SUCCESS] All database verification checks passed cleanly!")
        
    except Exception as e:
        print(f"\n[FAIL] Database verification failed: {e}")
        sys.exit(1)
    finally:
        db.close()

if __name__ == "__main__":
    verify_db()
