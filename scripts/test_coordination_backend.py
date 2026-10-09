"""
PulseStock AI - Complete Inter-Store Coordination & API Test Suite
Cypher 2026 Challenge 6

Automated test suite verifying authentication, store-level authorization,
workflow transitions, availability checks, cost calculation, notifications,
schema validations, database persistence, and regression tests.
"""

import os
import sys
from datetime import datetime, timedelta

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from fastapi.testclient import TestClient
from backend.main import app

client = TestClient(app)

def run_tests():
    print("==================================================")
    print(" PulseStock AI - Coordination & API Test Suite")
    print("==================================================")

    # Clean up test-generated requests and reset seed data for test isolation
    from backend.database import SessionLocal
    from backend.models.coordination import InterStoreRequest, StockTransferReservation, RiderTransferReservation, RequestApproval
    from scripts.seed_coordination_data import seed_data
    seed_data()
    db = SessionLocal()
    db.query(StockTransferReservation).filter(StockTransferReservation.request_id.like("REQ_202%")).delete(synchronize_session=False)
    db.query(RiderTransferReservation).filter(RiderTransferReservation.request_id.like("REQ_202%")).delete(synchronize_session=False)
    db.query(RequestApproval).filter(RequestApproval.request_id.like("REQ_202%")).delete(synchronize_session=False)
    db.query(InterStoreRequest).filter(InterStoreRequest.request_id.like("REQ_202%")).delete(synchronize_session=False)
    db.commit()
    db.close()

    test_results = []

    def record(name, passed, details=""):
        status = "PASS" if passed else "FAIL"
        test_results.append({"name": name, "status": status, "details": details})
        print(f"[{status}] {name}")
        if details:
            print(f"       Details: {details}")

    # ----------------------------------------------------
    # 1. Manager Login
    # ----------------------------------------------------
    res = client.post("/api/v1/auth/login", json={"username": "manager_store_007", "password": "PulseStock2026!"})
    is_ok = res.status_code == 200 and "access_token" in res.json()
    token_st7 = res.json().get("access_token") if is_ok else ""
    headers_st7 = {"Authorization": f"Bearer {token_st7}"}
    record("1. Manager Login (Store Manager)", is_ok, f"Status: {res.status_code}, Role: {res.json().get('manager', {}).get('role')}")

    res = client.post("/api/v1/auth/login", json={"username": "manager_store_001", "password": "PulseStock2026!"})
    token_st1 = res.json().get("access_token") if res.status_code == 200 else ""
    headers_st1 = {"Authorization": f"Bearer {token_st1}"}

    res = client.post("/api/v1/auth/login", json={"username": "city_manager", "password": "PulseStockCity2026!"})
    is_ok = res.status_code == 200 and res.json().get("manager", {}).get("role") == "CITY_MANAGER"
    token_city = res.json().get("access_token") if is_ok else ""
    headers_city = {"Authorization": f"Bearer {token_city}"}
    record("1b. Manager Login (City Operations Manager)", is_ok, f"Status: {res.status_code}")

    res = client.get("/api/v1/auth/me", headers=headers_st7)
    record("1c. Get Current Manager Profile (/auth/me)", res.status_code == 200 and res.json().get("store_id") == "STORE_007")

    # ----------------------------------------------------
    # 2. Store-Level Authorization
    # ----------------------------------------------------
    res = client.get("/api/v1/coordination/requests?store_id=STORE_012", headers=headers_st7)
    record("2. Store-Level Authorization (Forbidden Store View)", res.status_code == 403, f"Status: {res.status_code}")

    # ----------------------------------------------------
    # 3. Request Creation
    # ----------------------------------------------------
    req_payload = {
        "request_type": "STOCK_TRANSFER",
        "requesting_store_id": "STORE_007",
        "donor_store_id": "STORE_001",
        "sku_id": "SKU_COLD_DRINK_750ML",
        "requested_quantity": 10,
        "reason": "Test inter-store stock request"
    }
    res = client.post("/api/v1/coordination/requests", json=req_payload, headers=headers_st7)
    is_ok = res.status_code == 201 and res.json().get("status") == "REQUESTED"
    created_stock_req_id = res.json().get("request_id") if is_ok else ""
    record("3. Request Creation (Stock Transfer)", is_ok, f"Status: {res.status_code}, Request ID: {created_stock_req_id}")

    # ----------------------------------------------------
    # 4. Donor Acceptance
    # ----------------------------------------------------
    res = client.post(f"/api/v1/coordination/requests/{created_stock_req_id}/donor-accept", json={"notes": "Store 1 manager agrees"}, headers=headers_st1)
    is_ok = res.status_code == 200 and res.json().get("status") == "PENDING_CITY_APPROVAL"
    record("4. Donor Acceptance (Store 1 Manager Accepts)", is_ok, f"Status: {res.status_code}, Status: {res.json().get('status') if is_ok else res.text}")

    # Prevent Requesting Store Manager from acting as donor manager
    res = client.post(f"/api/v1/coordination/requests/{created_stock_req_id}/donor-accept", json={}, headers=headers_st7)
    record("4b. Prevent Requesting Store Manager Self-Approval", res.status_code == 403)

    # ----------------------------------------------------
    # 5. Donor Rejection
    # ----------------------------------------------------
    req_rej_payload = {
        "request_type": "STOCK_TRANSFER",
        "requesting_store_id": "STORE_007",
        "donor_store_id": "STORE_001",
        "sku_id": "SKU_COLD_DRINK_750ML",
        "requested_quantity": 10,
        "reason": "Will be rejected by donor"
    }
    res = client.post("/api/v1/coordination/requests", json=req_rej_payload, headers=headers_st7)
    rej_req_id = res.json().get("request_id")
    res = client.post(f"/api/v1/coordination/requests/{rej_req_id}/donor-reject", json={"reason": "Stock reserved for local promo"}, headers=headers_st1)
    record("5. Donor Rejection (Store 1 Manager Rejects)", res.status_code == 200 and res.json().get("status") == "DONOR_REJECTED")

    # ----------------------------------------------------
    # 6. City Manager Approval
    # ----------------------------------------------------
    res = client.post(f"/api/v1/coordination/requests/{created_stock_req_id}/city-approve", json={"notes": "City approved movement"}, headers=headers_city)
    is_ok = res.status_code == 200 and res.json().get("status") == "APPROVED"
    record("6. City Manager Approval (Final Authorization)", is_ok, f"Status: {res.status_code}, Detail: {res.text if not is_ok else ''}")

    # ----------------------------------------------------
    # 7. City Manager Rejection
    # ----------------------------------------------------
    req_city_rej = {
        "request_type": "STOCK_TRANSFER",
        "requesting_store_id": "STORE_007",
        "donor_store_id": "STORE_001",
        "sku_id": "SKU_COLD_DRINK_750ML",
        "requested_quantity": 10,
        "reason": "Will be rejected by city manager"
    }
    res = client.post("/api/v1/coordination/requests", json=req_city_rej, headers=headers_st7)
    c_rej_id = res.json().get("request_id")
    client.post(f"/api/v1/coordination/requests/{c_rej_id}/donor-accept", json={}, headers=headers_st1)
    res = client.post(f"/api/v1/coordination/requests/{c_rej_id}/city-reject", json={"reason": "Transit cost too high"}, headers=headers_city)
    record("7. City Manager Rejection", res.status_code == 200 and res.json().get("status") == "CITY_REJECTED")

    # ----------------------------------------------------
    # 8. Duplicate Request Approval (Idempotency)
    # ----------------------------------------------------
    res = client.post(f"/api/v1/coordination/requests/{created_stock_req_id}/city-approve", json={}, headers=headers_city)
    record("8. Duplicate Request Approval (Idempotency Check)", res.status_code == 200 and res.json().get("status") == "APPROVED")

    # ----------------------------------------------------
    # 9. Insufficient Stock Validation
    # ----------------------------------------------------
    req_huge_stock = {
        "request_type": "STOCK_TRANSFER",
        "requesting_store_id": "STORE_007",
        "donor_store_id": "STORE_003",
        "sku_id": "SKU_COLD_DRINK_750ML",
        "requested_quantity": 300,
        "reason": "Exceeds donor stock"
    }
    res = client.post("/api/v1/coordination/requests", json=req_huge_stock, headers=headers_st7)
    record("9. Insufficient Stock Validation", res.status_code == 400)

    # ----------------------------------------------------
    # 10. Insufficient Rider Capacity Validation
    # ----------------------------------------------------
    st_t = (datetime.utcnow() + timedelta(days=1)).isoformat() + "Z"
    en_t = (datetime.utcnow() + timedelta(days=1, hours=2)).isoformat() + "Z"
    req_huge_riders = {
        "request_type": "RIDER_TRANSFER",
        "requesting_store_id": "STORE_007",
        "donor_store_id": "STORE_001",
        "requested_riders_count": 999,
        "start_time": st_t,
        "end_time": en_t,
        "reason": "Exceeds total rider fleet"
    }
    res = client.post("/api/v1/coordination/requests", json=req_huge_riders, headers=headers_st7)
    record("10. Insufficient Rider Capacity Validation", res.status_code == 400)

    # ----------------------------------------------------
    # 11. Overlapping Rider Reservations Validation
    # ----------------------------------------------------
    # Step A: Create valid rider transfer for 5 riders (consuming Store 1 riders)
    st_overlap = (datetime.utcnow() + timedelta(days=2)).replace(minute=0, second=0, microsecond=0)
    en_overlap = st_overlap + timedelta(hours=2)

    r1_payload = {
        "request_type": "RIDER_TRANSFER",
        "requesting_store_id": "STORE_007",
        "donor_store_id": "STORE_001",
        "requested_riders_count": 6,
        "start_time": st_overlap.isoformat() + "Z",
        "end_time": en_overlap.isoformat() + "Z",
        "reason": "First rider reservation"
    }
    res1 = client.post("/api/v1/coordination/requests", json=r1_payload, headers=headers_st7)
    r1_id = res1.json().get("request_id")
    client.post(f"/api/v1/coordination/requests/{r1_id}/donor-accept", json={}, headers=headers_st1)

    # Step B: Attempt second overlapping request during same window requiring 5 riders (exceeding remaining 4 riders)
    r2_payload = {
        "request_type": "RIDER_TRANSFER",
        "requesting_store_id": "STORE_008",
        "donor_store_id": "STORE_001",
        "requested_riders_count": 5,
        "start_time": (st_overlap + timedelta(minutes=30)).isoformat() + "Z",
        "end_time": (en_overlap - timedelta(minutes=30)).isoformat() + "Z",
        "reason": "Overlapping rider reservation"
    }
    res2 = client.post("/api/v1/coordination/requests", json=r2_payload, headers=headers_city)
    record("11. Overlapping Rider Reservations Validation", res2.status_code == 400)

    # ----------------------------------------------------
    # 12. Shelf-Capacity Violations
    # ----------------------------------------------------
    req_capacity = {
        "request_type": "STOCK_TRANSFER",
        "requesting_store_id": "STORE_007",
        "donor_store_id": "STORE_001",
        "sku_id": "SKU_COLD_DRINK_750ML",
        "requested_quantity": 5000,
        "reason": "Exceeds shelf capacity limit"
    }
    res = client.post("/api/v1/coordination/requests", json=req_capacity, headers=headers_st7)
    record("12. Shelf-Capacity Violations", res.status_code in (400, 422))

    # ----------------------------------------------------
    # 13. Invalid Status Transitions
    # ----------------------------------------------------
    req_skip = {
        "request_type": "STOCK_TRANSFER",
        "requesting_store_id": "STORE_007",
        "donor_store_id": "STORE_001",
        "sku_id": "SKU_COLD_DRINK_750ML",
        "requested_quantity": 5,
        "reason": "Direct city approve without donor accept"
    }
    res = client.post("/api/v1/coordination/requests", json=req_skip, headers=headers_st7)
    skip_id = res.json().get("request_id")
    res = client.post(f"/api/v1/coordination/requests/{skip_id}/city-approve", json={}, headers=headers_city)
    record("13. Invalid Status Transitions (Skipping Donor Accept)", res.status_code == 400)

    # ----------------------------------------------------
    # 14. Cost Calculation & Breakdown
    # ----------------------------------------------------
    res = client.get("/api/v1/coordination/cost-config")
    is_ok = res.status_code == 200 and res.json().get("base_transport_cost_per_trip") == 100.0
    record("14a. Cost Config Endpoint (/coordination/cost-config)", is_ok)

    res = client.get(f"/api/v1/coordination/requests/{created_stock_req_id}/cost-estimate")
    is_ok = res.status_code == 200 and res.json().get("financial_benefit_status") == "UNAVAILABLE_AWAITING_ENGINE"
    record("14b. Cost Estimate Endpoint (/requests/{id}/cost-estimate)", is_ok, f"Estimated Cost: INR {res.json().get('estimated_cost_inr')}")

    # ----------------------------------------------------
    # 15. Notifications Retrieval & Polling
    # ----------------------------------------------------
    res = client.get("/api/v1/notifications", headers=headers_city)
    is_ok = res.status_code == 200 and len(res.json()) >= 1
    notif_id = res.json()[0]["notification_id"] if is_ok and len(res.json()) > 0 else ""
    record("15a. Notification Retrieval Endpoint (/notifications)", is_ok, f"Count: {len(res.json()) if is_ok else 0}")

    if notif_id:
        res = client.patch(f"/api/v1/notifications/{notif_id}/read", headers=headers_city)
        record("15b. Mark Notification as Read (/notifications/{id}/read)", res.status_code == 200 and res.json().get("is_read") == True)

    # ----------------------------------------------------
    # 16. Database Persistence Verification
    # ----------------------------------------------------
    res = client.get(f"/api/v1/coordination/requests/{created_stock_req_id}", headers=headers_st7)
    is_ok = False
    if res.status_code == 200:
        data = res.json()
        if data.get("status") == "APPROVED" and len(data.get("history", [])) >= 3:
            is_ok = True
    record("16. Database Persistence Verification", is_ok, f"Request Status: {res.json().get('status') if res.status_code == 200 else 'Error'}, History Steps: {len(res.json().get('history', [])) if res.status_code == 200 else 0}")

    # ----------------------------------------------------
    # Full End-to-End Multi-Step Scenario Verification
    # ----------------------------------------------------
    st_e2e = (datetime.utcnow() + timedelta(days=3)).replace(minute=0, second=0, microsecond=0)
    en_e2e = st_e2e + timedelta(hours=2)

    # Step 1: Store X creates rider request
    res = client.post("/api/v1/coordination/requests", json={
        "request_type": "RIDER_TRANSFER",
        "requesting_store_id": "STORE_007",
        "donor_store_id": "STORE_001",
        "requested_riders_count": 3,
        "start_time": st_e2e.isoformat() + "Z",
        "end_time": en_e2e.isoformat() + "Z",
        "reason": "Full scenario test: 3 riders from Store 1 to Store 7"
    }, headers=headers_st7)
    e2e_id = res.json().get("request_id")

    # Step 2: Donor accepts
    client.post(f"/api/v1/coordination/requests/{e2e_id}/donor-accept", json={"notes": "Store 1 manager agrees to lend riders"}, headers=headers_st1)

    # Step 3: City manager approves
    client.post(f"/api/v1/coordination/requests/{e2e_id}/city-approve", json={"notes": "City manager approves rider transfer"}, headers=headers_city)

    # Step 4: Verify both managers see updated APPROVED status
    res_st7 = client.get(f"/api/v1/coordination/requests/{e2e_id}", headers=headers_st7)
    res_st1 = client.get(f"/api/v1/coordination/requests/{e2e_id}", headers=headers_st1)

    e2e_passed = (
        res_st7.status_code == 200 and res_st7.json().get("status") == "APPROVED" and
        res_st1.status_code == 200 and res_st1.json().get("status") == "APPROVED"
    )
    record("FULL SCENARIO: 3 Riders Store X -> Donor Accepts -> City Approves -> Both Managers See Approved", e2e_passed)

    # ----------------------------------------------------
    # 17. Existing API Regression Tests
    # ----------------------------------------------------
    res = client.get("/health")
    record("17a. Regression: /health", res.status_code == 200)

    res = client.get("/docs")
    record("17b. Regression: /docs", res.status_code == 200)

    res = client.get("/api/v1/stores/STORE_007/inventory")
    record("17c. Regression: /stores/STORE_007/inventory", res.status_code == 200)

    res = client.get("/api/v1/events/context?store_id=STORE_007")
    record("17d. Regression: /events/context", res.status_code == 200)

    res = client.get("/api/v1/warehouses/availability?sku_id=SKU_COLD_DRINK_750ML")
    record("17e. Regression: /warehouses/availability", res.status_code == 200)

    res = client.get("/api/v1/logistics/trucks?store_id=STORE_007")
    record("17f. Regression: /logistics/trucks", res.status_code == 200)

    res = client.get("/api/v1/logistics/riders?store_id=STORE_007")
    record("17g. Regression: /logistics/riders", res.status_code == 200)

    res = client.get("/api/v1/alerts/stockouts")
    record("17h. Regression: /alerts/stockouts", res.status_code == 200)

    res = client.get("/api/v1/recommendations?alert_id=ALT_20261009_007_01")
    record("17i. Regression: /recommendations", res.status_code == 200)

    res = client.post("/api/v1/recommendations/REC_007_TRF_01/approve", json={"manager_id": "MGR_STORE_007", "manager_notes": "Approved"})
    record("17j. Regression: /recommendations/{id}/approve", res.status_code == 200)

    res = client.get("/api/v1/actions/history")
    record("17k. Regression: /actions/history", res.status_code == 200)

    passed_count = sum(1 for t in test_results if t["status"] == "PASS")
    total_count = len(test_results)

    print("\n--------------------------------------------------")
    print(f" Coordination Suite Summary: {passed_count} / {total_count} Tests Passed")
    print("--------------------------------------------------")

    return test_results

if __name__ == "__main__":
    run_tests()
