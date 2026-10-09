"""
PulseStock AI - Comprehensive Backend Verification Suite
Cypher 2026 Challenge 6

Tests all FastAPI REST endpoints, SQLite database persistence, 
manager approval/rejection workflows, health, docs, and engine dependencies.
"""

import os
import sys

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from fastapi.testclient import TestClient
from backend.main import app

client = TestClient(app)

def run_all_tests():
    print("==================================================")
    print(" PulseStock AI - Complete Backend Verification Suite")
    print("==================================================")
    
    test_results = []

    def record_test(name, passed, details=""):
        status = "PASS" if passed else "FAIL"
        test_results.append({"name": name, "status": status, "details": details})
        print(f"[{status}] {name}")
        if details:
            print(f"       Details: {details}")

    # 1. Health & Documentation Endpoints
    res = client.get("/health")
    record_test("Health Endpoint (/health)", res.status_code == 200 and res.json().get("status") == "ok", f"Status: {res.status_code}, Payload: {res.json()}")

    res = client.get("/api/v1/health")
    record_test("Health Endpoint (/api/v1/health)", res.status_code == 200 and res.json().get("status") == "ok", f"Status: {res.status_code}")

    res = client.get("/docs")
    record_test("Swagger API Documentation (/docs)", res.status_code == 200, f"Status: {res.status_code}")

    # 2. Store & Inventory Endpoints
    res = client.get("/api/v1/stores/STORE_007/inventory")
    is_ok = False
    details = ""
    if res.status_code == 200:
        data = res.json()
        skus = data.get("skus", [])
        st7_item = next((s for s in skus if s["sku_id"] == "SKU_COLD_DRINK_750ML"), None)
        if st7_item and st7_item["total_stock_units"] == 14:
            is_ok = True
            details = f"Store: {data.get('store_name')}, Total SKUs: {len(skus)}, SKU_COLD_DRINK_750ML Total Stock: {st7_item['total_stock_units']}"
        else:
            details = f"Invalid SKU stock: {st7_item}"
    else:
        details = f"HTTP {res.status_code}"
    record_test("Store Inventory Endpoint (/stores/STORE_007/inventory)", is_ok, details)

    # 3. External Events Context Endpoint
    res = client.get("/api/v1/events/context?store_id=STORE_007")
    is_ok = False
    details = ""
    if res.status_code == 200:
        data = res.json()
        events = data.get("events", [])
        if len(events) >= 3:
            is_ok = True
            details = f"Active Events: {len(events)} (e.g., {events[0]['title']} multiplier={events[0]['multiplier']}x)"
        else:
            details = f"Only {len(events)} events returned."
    else:
        details = f"HTTP {res.status_code}"
    record_test("External Events Endpoint (/events/context)", is_ok, details)

    # 4. Warehouse Stock Availability Endpoint
    res = client.get("/api/v1/warehouses/availability?sku_id=SKU_COLD_DRINK_750ML")
    is_ok = False
    details = ""
    if res.status_code == 200:
        data = res.json()
        if data.get("available_stock_units") == 2400 and data.get("free_stock_units") == 2100:
            is_ok = True
            details = f"Warehouse: {data.get('warehouse_id')}, Available: {data.get('available_stock_units')}, Free: {data.get('free_stock_units')}"
        else:
            details = f"Unexpected stock payload: {data}"
    else:
        details = f"HTTP {res.status_code}"
    record_test("Warehouse Stock Endpoint (/warehouses/availability)", is_ok, details)

    # 5. Truck Schedules Endpoint
    res = client.get("/api/v1/logistics/trucks?store_id=STORE_007")
    is_ok = False
    details = ""
    if res.status_code == 200:
        data = res.json()
        deliveries = data.get("scheduled_deliveries", [])
        expedited = data.get("expedited_option", {})
        if len(deliveries) > 0 and expedited.get("is_available") is True:
            is_ok = True
            details = f"Scheduled Deliveries: {len(deliveries)} (Truck: {deliveries[0]['truck_id']}), Express Option Available: {expedited.get('truck_id')}"
        else:
            details = f"Unexpected deliveries payload: {data}"
    else:
        details = f"HTTP {res.status_code}"
    record_test("Truck Schedules Endpoint (/logistics/trucks)", is_ok, details)

    # 6. Rider Availability Endpoint
    res = client.get("/api/v1/logistics/riders?store_id=STORE_007")
    is_ok = False
    details = ""
    if res.status_code == 200:
        data = res.json()
        if data.get("active_riders") == 3 and data.get("shortage_severity") == "HIGH":
            is_ok = True
            details = f"Active Riders: {data.get('active_riders')}, Required: {data.get('required_riders_for_demand')}, Shortage: {data.get('rider_shortage_count')} ({data.get('shortage_severity')})"
        else:
            details = f"Unexpected rider payload: {data}"
    else:
        details = f"HTTP {res.status_code}"
    record_test("Rider Fleet Endpoint (/logistics/riders)", is_ok, details)

    # 7. Donor Stores Endpoint
    res = client.get("/api/v1/logistics/donors?store_id=STORE_007&sku_id=SKU_COLD_DRINK_750ML")
    is_ok = False
    details = ""
    if res.status_code == 200:
        data = res.json()
        donors = data.get("donor_stores", [])
        st9 = next((d for d in donors if d["donor_store_id"] == "STORE_009"), None)
        if st9 and st9["current_stock_units"] == 60:
            is_ok = True
            details = f"Candidate Donors: {len(donors)}, Store 9 Surplus: {st9['surplus_units']} units"
        else:
            details = f"Store 9 candidate missing or invalid."
    else:
        details = f"HTTP {res.status_code}"
    record_test("Donor Stores Endpoint (/logistics/donors)", is_ok, details)

    # 8. Stockout Alerts Endpoints
    res = client.get("/api/v1/alerts/stockouts")
    is_ok = False
    details = ""
    if res.status_code == 200:
        data = res.json()
        alerts = data.get("alerts", [])
        if len(alerts) >= 1:
            is_ok = True
            details = f"Total Stockout Alerts: {len(alerts)} (Alert ID: {alerts[0]['alert_id']}, Store: {alerts[0]['store_id']})"
        else:
            details = f"No alerts found."
    else:
        details = f"HTTP {res.status_code}"
    record_test("Stockout Alerts List Endpoint (/alerts/stockouts)", is_ok, details)

    res = client.get("/api/v1/alerts/stockouts/ALT_20261009_007_01")
    is_ok = False
    details = ""
    if res.status_code == 200:
        data = res.json()
        if data.get("alert_id") == "ALT_20261009_007_01":
            is_ok = True
            details = f"Alert ID: {data.get('alert_id')}, Severity: {data.get('severity')}, Projected Demand: {data.get('projected_hourly_demand')}"
        else:
            details = f"Invalid alert payload: {data}"
    else:
        details = f"HTTP {res.status_code}"
    record_test("Stockout Alert Detail Endpoint (/alerts/stockouts/ALT_20261009_007_01)", is_ok, details)

    # 9. Recommendations Endpoint
    res = client.get("/api/v1/recommendations?alert_id=ALT_20261009_007_01")
    is_ok = False
    details = ""
    if res.status_code == 200:
        data = res.json()
        recs = data.get("recommendations", [])
        if len(recs) == 4:
            is_ok = True
            details = f"Evaluated Options Count: {len(recs)} (Top Option: {recs[0]['option_type']} - {recs[0]['title']})"
        else:
            details = f"Unexpected recommendations count: {len(recs)}"
    else:
        details = f"HTTP {res.status_code}"
    record_test("Recommendations Endpoint (/recommendations)", is_ok, details)

    # 10. Manager Approval & Rejection Workflow Endpoints
    res = client.post(
        "/api/v1/recommendations/REC_007_TRF_01/approve",
        json={"manager_id": "MGR_KORAMANGALA_07", "manager_notes": "Approved express rider transfer from Store 3."}
    )
    is_ok = False
    details = ""
    if res.status_code == 200:
        data = res.json()
        if data.get("status") == "APPROVED" and data.get("action_id"):
            is_ok = True
            details = f"Action ID: {data.get('action_id')}, Status: {data.get('status')}, Manager: {data.get('manager_id')}"
        else:
            details = f"Unexpected approval payload: {data}"
    else:
        details = f"HTTP {res.status_code}"
    record_test("Manager Approval Endpoint (/recommendations/REC_007_TRF_01/approve)", is_ok, details)

    res = client.post(
        "/api/v1/recommendations/REC_007_TRK_02/reject",
        json={"manager_id": "MGR_KORAMANGALA_07", "notes": "Expedited truck cost is too high."}
    )
    is_ok = False
    details = ""
    if res.status_code == 200:
        data = res.json()
        if data.get("status") == "REJECTED":
            is_ok = True
            details = f"Recommendation ID: {data.get('recommendation_id')}, Status: {data.get('status')}"
        else:
            details = f"Unexpected rejection payload: {data}"
    else:
        details = f"HTTP {res.status_code}"
    record_test("Manager Rejection Endpoint (/recommendations/REC_007_TRK_02/reject)", is_ok, details)

    # 11. Action Audit History Endpoint
    res = client.get("/api/v1/actions/history")
    is_ok = False
    details = ""
    if res.status_code == 200:
        data = res.json()
        actions = data.get("actions", [])
        if len(actions) >= 2:
            is_ok = True
            details = f"Persisted Action Logs Count: {len(actions)} (Latest: {actions[0]['action_id']} - {actions[0]['status']})"
        else:
            details = f"Fewer than 2 action logs persisted."
    else:
        details = f"HTTP {res.status_code}"
    record_test("Action Audit History Endpoint (/actions/history)", is_ok, details)

    # 12. Decision Engine Dependencies Check (Forecast & Simulation Endpoints)
    res = client.get("/api/v1/forecast/hourly?store_id=STORE_007&sku_id=SKU_COLD_DRINK_750ML")
    record_test(
        "Hourly Forecast Endpoint (/forecast/hourly) [Awaiting Decision Engine]",
        res.status_code == 200,
        f"Status: {res.status_code}, intervals={len(res.json().get('forecast_intervals', []))} (Awaiting Python engine calculations)"
    )

    res = client.post("/api/v1/simulation/recalculate", json={"store_id": "STORE_007", "sku_id": "SKU_COLD_DRINK_750ML"})
    record_test(
        "What-if Simulation Endpoint (/simulation/recalculate) [Awaiting Decision Engine]",
        res.status_code == 200,
        f"Status: {res.status_code}, simulation_id={res.json().get('simulation_id')} (Awaiting Python engine simulation)"
    )

    # Summary Report
    passed_count = sum(1 for t in test_results if t["status"] == "PASS")
    total_count = len(test_results)
    
    print("\n--------------------------------------------------")
    print(f" Summary: {passed_count} / {total_count} Endpoint Tests Passed")
    print("--------------------------------------------------")
    
    return test_results

if __name__ == "__main__":
    run_all_tests()
