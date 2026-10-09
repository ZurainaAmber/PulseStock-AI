"""
PulseStock AI - Demo Seed Data Generator for Inter-Store Coordination
Cypher 2026 Challenge 6

Seeds 30 Store Manager accounts, 1 City Operations Manager account,
operational cost configurations, demo inter-store requests, rider reservations,
and notifications. Rerunning this script is idempotent.
"""

import os
import sys
from datetime import datetime, timedelta

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from backend.database import SessionLocal, init_db
from backend.models.manager import Manager
from backend.models.store import Store
from backend.models.cost_config import OperationalCostConfig
from backend.models.coordination import (
    InterStoreRequest,
    RiderTransferReservation,
    StockTransferReservation,
    RequestApproval,
)
from backend.models.notification import ManagerNotification
from backend.auth import hash_password
from backend.config import settings

def seed_data():
    print("==================================================")
    print(" PulseStock AI - Seeding Coordination Demo Data")
    print("==================================================")

    init_db()
    db = SessionLocal()

    try:
        # 1. Seed Operational Cost Config
        cost_cfg = db.query(OperationalCostConfig).first()
        if not cost_cfg:
            cost_cfg = OperationalCostConfig(
                base_transport_cost_per_trip=100.0,
                var_transport_cost_per_km=15.0,
                loading_unloading_cost=30.0,
                shelf_swap_labor_cost=50.0,
                additional_rider_cost_per_hour=80.0,
                rider_relocation_cost=40.0,
                extra_truck_dispatch_cost=350.0,
                updated_at=datetime.utcnow()
            )
            db.add(cost_cfg)
            print("[+] Seeded Operational Cost Config.")

        # 2. Seed City Operations Manager Account
        city_mgr = db.query(Manager).filter(Manager.manager_id == "MGR_CITY_OPS").first()
        city_pass_hash = hash_password(settings.DEMO_CITY_MANAGER_PASSWORD)
        if not city_mgr:
            city_mgr = Manager(
                manager_id="MGR_CITY_OPS",
                username="city_manager",
                password_hash=city_pass_hash,
                full_name="City Operations Manager",
                role="CITY_MANAGER",
                store_id=None,
                created_at=datetime.utcnow()
            )
            db.add(city_mgr)
            print("[+] Seeded City Operations Manager account ('city_manager').")
        else:
            city_mgr.password_hash = city_pass_hash

        # 3. Seed 30 Store Manager Accounts
        store_pass_hash = hash_password(settings.DEMO_STORE_MANAGER_PASSWORD)
        stores = db.query(Store).all()
        store_count = 0
        for i in range(1, 31):
            s_id = f"STORE_{i:03d}"
            m_id = f"MGR_STORE_{i:03d}"
            uname = f"manager_store_{i:03d}"
            
            existing = db.query(Manager).filter(Manager.manager_id == m_id).first()
            if not existing:
                st_obj = next((s for s in stores if s.store_id == s_id), None)
                st_name = st_obj.store_name if st_obj else f"Store {i}"
                new_mgr = Manager(
                    manager_id=m_id,
                    username=uname,
                    password_hash=store_pass_hash,
                    full_name=f"Manager - {st_name}",
                    role="STORE_MANAGER",
                    store_id=s_id,
                    created_at=datetime.utcnow()
                )
                db.add(new_mgr)
                store_count += 1
            else:
                existing.password_hash = store_pass_hash

        if store_count > 0:
            print(f"[+] Seeded {store_count} Store Manager accounts ('manager_store_001' to 'manager_store_030').")

        db.commit()

        # 4. Seed Demo Inter-Store Requests
        now = datetime.utcnow()

        # Scenario A: Store 7 requests 3 riders from Store 3
        req_rider_id = "REQ_DEMO_RIDER_01"
        req_rider = db.query(InterStoreRequest).filter(InterStoreRequest.request_id == req_rider_id).first()
        st_time = now.replace(minute=0, second=0, microsecond=0) + timedelta(hours=1)
        en_time = st_time + timedelta(hours=2)

        if not req_rider:
            req_rider = InterStoreRequest(
                request_id=req_rider_id,
                request_type="RIDER_TRANSFER",
                requesting_store_id="STORE_007",
                donor_store_id="STORE_003",
                sku_id=None,
                requested_quantity=None,
                requested_riders_count=3,
                start_time=st_time,
                end_time=en_time,
                status="PENDING_CITY_APPROVAL",
                created_by_manager_id="MGR_STORE_007",
                reason="Match crowd surge expected; 6 rider shortage at Store 7.",
                estimated_cost_inr=600.0,
                estimated_net_benefit_inr=None,
                created_at=now,
                updated_at=now
            )
            db.add(req_rider)

            # Rider Reservation
            rdr_res = RiderTransferReservation(
                reservation_id="RES_DEMO_RDR_01",
                request_id=req_rider_id,
                donor_store_id="STORE_003",
                requesting_store_id="STORE_007",
                riders_count=3,
                start_time=st_time,
                end_time=en_time,
                status="RESERVED",
                created_at=now
            )
            db.add(rdr_res)

            # Approvals history
            app1 = RequestApproval(
                approval_id="APP_DEMO_01",
                request_id=req_rider_id,
                actor_manager_id="MGR_STORE_007",
                actor_role="STORE_MANAGER",
                action="CREATE",
                from_status="NONE",
                to_status="REQUESTED",
                reason="Match demand surge expected",
                timestamp=now - timedelta(minutes=15)
            )
            app2 = RequestApproval(
                approval_id="APP_DEMO_02",
                request_id=req_rider_id,
                actor_manager_id="MGR_STORE_003",
                actor_role="STORE_MANAGER",
                action="DONOR_ACCEPT",
                from_status="REQUESTED",
                to_status="PENDING_CITY_APPROVAL",
                reason="Store 3 has 5 rider surplus",
                timestamp=now - timedelta(minutes=5)
            )
            db.add_all([app1, app2])
            print("[+] Seeded Rider Transfer request ('REQ_DEMO_RIDER_01').")

        # Scenario B: Store 7 requests 50 units of Cold Drink from Store 3
        req_stock_id = "REQ_DEMO_STOCK_01"
        req_stock = db.query(InterStoreRequest).filter(InterStoreRequest.request_id == req_stock_id).first()
        if not req_stock:
            req_stock = InterStoreRequest(
                request_id=req_stock_id,
                request_type="STOCK_TRANSFER",
                requesting_store_id="STORE_007",
                donor_store_id="STORE_003",
                sku_id="SKU_COLD_DRINK_750ML",
                requested_quantity=50,
                requested_riders_count=None,
                start_time=None,
                end_time=None,
                status="REQUESTED",
                created_by_manager_id="MGR_STORE_007",
                reason="Koramangala match stockout prevention.",
                estimated_cost_inr=181.0,
                estimated_net_benefit_inr=None,
                created_at=now,
                updated_at=now
            )
            db.add(req_stock)

            app3 = RequestApproval(
                approval_id="APP_DEMO_03",
                request_id=req_stock_id,
                actor_manager_id="MGR_STORE_007",
                actor_role="STORE_MANAGER",
                action="CREATE",
                from_status="NONE",
                to_status="REQUESTED",
                reason="Cold drink stockout risk",
                timestamp=now - timedelta(minutes=10)
            )
            db.add(app3)
            print("[+] Seeded Stock Transfer request ('REQ_DEMO_STOCK_01').")

        # 5. Seed Sample Notifications
        notif1 = db.query(ManagerNotification).filter(ManagerNotification.notification_id == "NOTIF_DEMO_01").first()
        if not notif1:
            n1 = ManagerNotification(
                notification_id="NOTIF_DEMO_01",
                manager_id="MGR_CITY_OPS",
                title="Rider Transfer Request Accepted by Donor",
                message="Store 3 accepted request REQ_DEMO_RIDER_01 for 3 riders to Store 7. Awaiting your approval.",
                type="DONOR_ACCEPTED",
                request_id=req_rider_id,
                is_read=0,
                created_at=now - timedelta(minutes=5)
            )
            n2 = ManagerNotification(
                notification_id="NOTIF_DEMO_02",
                manager_id="MGR_STORE_003",
                title="New Stock Transfer Request",
                message="Store 7 requested 50 units of Sparkling Cola 750ml from your store.",
                type="REQUEST_CREATED",
                request_id=req_stock_id,
                is_read=0,
                created_at=now - timedelta(minutes=10)
            )
            db.add_all([n1, n2])
            print("[+] Seeded demo notifications.")

        db.commit()
        print("\n[SUCCESS] Seed data completed successfully!")

    except Exception as e:
        db.rollback()
        print(f"[ERROR] Seeding failed: {e}")
        raise e
    finally:
        db.close()

if __name__ == "__main__":
    seed_data()
