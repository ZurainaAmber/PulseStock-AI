# PulseStock AI - REST API Specification

**Version:** 1.0.0  
**Context:** Cypher 2026 Challenge 6 - Store 7 Stock-out Prevention & Decision Engine  
**Target Backend:** Python FastAPI + SQLite  
**Target Frontend:** React + Vite + Tailwind CSS + Recharts  

---

## 1. Overview & General Conventions

This document defines the complete RESTful HTTP API contract between the **PulseStock AI Frontend** (React/Vite) and the **PulseStock AI Backend** (FastAPI).

### 1.1 Base URL
All API requests must be prefixed with:
`http://localhost:8000/api/v1`

### 1.2 Global Naming Conventions
- **JSON Keys:** `snake_case` (e.g., `store_id`, `estimated_stockout_timestamp`)
- **Timestamps:** ISO 8601 UTC strings formatted as `YYYY-MM-DDTHH:mm:ssZ` (e.g., `2026-10-09T18:30:00Z`)
- **Currency:** Explicitly specified in INR (`₹`), field suffix `_inr` or nested currency object.
- **Quantities:** Integer numbers representing physical units (`units`).
- **Percentages:** Decimal numbers between `0.0` and `100.0` or multiplier factors (`1.0` to `5.0`).
- **Identifiers:** String prefixes for clarity:
  - Store: `STORE_xxx` (e.g., `STORE_007`)
  - SKU: `SKU_xxx` (e.g., `SKU_COLD_DRINK_750ML`)
  - Warehouse: `WH_xxx` (e.g., `WH_CENTRAL_01`)
  - Alert: `ALT_xxx` (e.g., `ALT_20261009_007_01`)
  - Recommendation: `REC_xxx` (e.g., `REC_007_TRF_01`)
  - Action / Execution: `ACT_xxx` (e.g., `ACT_20261009_8812`)

### 1.3 Standard Error Format (RFC 7807 compliant)
All non-`2xx` HTTP responses return a structured error body:

```json
{
  "error": {
    "code": "RESOURCE_NOT_FOUND",
    "message": "Store with ID 'STORE_999' was not found.",
    "details": {
      "invalid_parameter": "store_id",
      "suggested_action": "Verify store ID against available store list."
    },
    "timestamp": "2026-10-09T21:30:00Z"
  }
}
```

#### HTTP Status Codes Used:
- `200 OK`: Request succeeded.
- `201 Created`: Action or simulation record created successfully.
- `400 Bad Request`: Invalid parameters or malformed payload.
- `404 Not Found`: Alert, Store, SKU, or Recommendation ID does not exist.
- `422 Unprocessable Entity`: Validation failure in input constraints.
- `500 Internal Server Error`: Unexpected internal error or decision engine failure.

---

## 2. API Endpoints Summary

| Method | Endpoint Path | Description |
| :--- | :--- | :--- |
| `GET` | `/alerts/stockouts` | List active 4-hour stock-out alerts across stores/SKUs |
| `GET` | `/alerts/stockouts/{alert_id}` | Detailed stock-out alert information & breakdown |
| `GET` | `/forecast/hourly` | Fetch 24-hour demand forecast with event uplifts |
| `GET` | `/events/context` | Fetch active demand drivers (Cricket, Rain, Festival) |
| `GET` | `/stores/{store_id}/inventory` | Get store stock, backroom breakdown & shelf capacity |
| `GET` | `/warehouses/availability` | Fetch central warehouse inventory & dispatch slots |
| `GET` | `/logistics/trucks` | Get scheduled truck deliveries & expedited options |
| `GET` | `/logistics/donors` | Find nearby donor stores with surplus stock |
| `GET` | `/logistics/riders` | Get local rider fleet availability & shortage status |
| `GET` | `/recommendations` | Get AI engine decision options for an alert |
| `POST` | `/recommendations/{recommendation_id}/approve` | Manager approves a recommended action |
| `POST` | `/recommendations/{recommendation_id}/reject` | Manager rejects a recommendation with reason |
| `GET` | `/actions/history` | Audit trail of approved/rejected/executed actions |
| `POST` | `/simulation/recalculate` | Perform what-if simulation & recalculate recommendations |
| `POST` | `/auth/login` | Authenticate store manager or city operations manager |
| `GET` | `/auth/me` | Fetch authenticated manager profile details |
| `GET` | `/coordination/requests` | List inter-store stock and rider transfer requests |
| `POST` | `/coordination/requests` | Create a new inter-store stock or rider transfer request |
| `GET` | `/coordination/requests/{request_id}` | Get detailed inter-store request info and audit trail |
| `POST` | `/coordination/requests/{request_id}/donor-accept` | Donor store manager accepts inter-store request |
| `POST` | `/coordination/requests/{request_id}/donor-reject` | Donor store manager declines inter-store request |
| `POST` | `/coordination/requests/{request_id}/city-approve` | City Operations Manager grants final approval |
| `POST` | `/coordination/requests/{request_id}/city-reject` | City Operations Manager declines inter-store request |
| `POST` | `/coordination/requests/{request_id}/cancel` | Requesting store manager or city manager cancels request |
| `GET` | `/coordination/stock-availability` | Check donor stock availability and safe surplus |
| `GET` | `/coordination/rider-availability` | Check donor rider fleet availability for time interval |
| `GET` | `/coordination/cost-config` | Fetch operational cost parameters |
| `GET` | `/coordination/requests/{request_id}/cost-estimate` | Fetch operational cost breakdown for a request |
| `GET` | `/notifications` | Poll manager notifications |
| `PATCH` | `/notifications/{notification_id}/read` | Mark a manager notification as read |

---

## 3. Endpoint Specifications

---

### 3.1 `GET /alerts/stockouts`
Retrieves stock-out risks projected within the next 4 hours across all stores or filtered by `store_id`.

#### Query Parameters:
- `store_id` *(optional, string)*: Filter by store (e.g., `STORE_007`).
- `min_severity` *(optional, string)*: Minimum alert severity (`CRITICAL`, `HIGH`, `MEDIUM`, `LOW`). Default: `LOW`.
- `time_horizon_hours` *(optional, integer)*: Projection window in hours (default: `4`).

#### Response Body (`200 OK`):
```json
{
  "timestamp": "2026-10-09T18:00:00Z",
  "total_alerts": 1,
  "alerts": [
    {
      "alert_id": "ALT_20261009_007_01",
      "store_id": "STORE_007",
      "store_name": "Store 7 - Koramangala Tech Park",
      "sku_id": "SKU_COLD_DRINK_750ML",
      "sku_name": "Sparkling Cola 750ml",
      "category": "Cold Beverages",
      "severity": "CRITICAL",
      "current_total_stock_units": 55,
      "shelf_stock_units": 35,
      "backroom_stock_units": 20,
      "projected_hourly_demand_units": 65,
      "stockout_probability": 0.96,
      "minutes_until_stockout": 42,
      "estimated_stockout_timestamp": "2026-10-09T18:42:00Z",
      "primary_driver": "CRICKET_AND_RAIN_COMBO",
      "status": "PENDING"
    }
  ]
}
```

---

### 3.2 `GET /forecast/hourly`
Fetches hourly baseline vs uplifted demand curve for a specific store and SKU.

#### Query Parameters:
- `store_id` *(required, string)*: Store ID (e.g., `STORE_007`).
- `sku_id` *(required, string)*: SKU ID (e.g., `SKU_COLD_DRINK_750ML`).
- `hours` *(optional, integer)*: Forecast horizon hours (default: `12`, max: `24`).

#### Response Body (`200 OK`):
```json
{
  "store_id": "STORE_007",
  "sku_id": "SKU_COLD_DRINK_750ML",
  "generated_at": "2026-10-09T18:00:00Z",
  "forecast_intervals": [
    {
      "timestamp": "2026-10-09T18:00:00Z",
      "hour_label": "18:00 - 19:00",
      "baseline_demand_units": 15,
      "cricket_uplift_units": 32,
      "rain_uplift_units": 12,
      "festival_uplift_units": 6,
      "final_projected_demand_units": 65,
      "confidence_lower_bound": 58,
      "confidence_upper_bound": 72
    },
    {
      "timestamp": "2026-10-09T19:00:00Z",
      "hour_label": "19:00 - 20:00",
      "baseline_demand_units": 18,
      "cricket_uplift_units": 45,
      "rain_uplift_units": 10,
      "festival_uplift_units": 7,
      "final_projected_demand_units": 80,
      "confidence_lower_bound": 70,
      "confidence_upper_bound": 90
    }
  ]
}
```

---

### 3.3 `GET /events/context`
Provides active external context influencing demand algorithms.

#### Query Parameters:
- `store_id` *(optional, string)*: Filter events relevant to store radius.

#### Response Body (`200 OK`):
```json
{
  "store_id": "STORE_007",
  "active_events": {
    "cricket_match": {
      "is_active": true,
      "match_id": "MAT_IND_PAK_2026",
      "title": "India vs Pakistan T20 World Cup Super 8",
      "stadium_name": "Chinnaswamy Stadium",
      "distance_km": 1.4,
      "status": "IN_PROGRESS",
      "current_match_time": "Innings Break",
      "category_uplift_multipliers": {
        "Cold Beverages": 2.5,
        "Snacks & Chips": 2.2,
        "Instant Meals": 1.8
      }
    },
    "weather": {
      "is_active": true,
      "condition": "HEAVY_RAIN",
      "precipitation_mm_per_hr": 22.5,
      "delivery_speed_reduction_pct": 40.0,
      "category_uplift_multipliers": {
        "Cold Beverages": 1.35,
        "Hot Beverages": 1.8
      }
    },
    "festival": {
      "is_active": true,
      "festival_name": "Diwali Pre-Shopping Week",
      "peak_category": "Cold Beverages",
      "category_uplift_multipliers": {
        "Cold Beverages": 1.25,
        "Sweets": 2.0
      }
    }
  }
}
```

---

### 3.4 `GET /stores/{store_id}/inventory`
Retrieves store stock levels, backroom inventory, shelf allocation, and physical capacities.

#### Path Parameters:
- `store_id` *(string)*: e.g., `STORE_007`

#### Query Parameters:
- `sku_id` *(optional, string)*: Filter by single SKU.

#### Response Body (`200 OK`):
```json
{
  "store_id": "STORE_007",
  "store_name": "Store 7 - Koramangala Tech Park",
  "skus": [
    {
      "sku_id": "SKU_COLD_DRINK_750ML",
      "sku_name": "Sparkling Cola 750ml",
      "shelf_stock_units": 35,
      "shelf_capacity_units": 40,
      "backroom_stock_units": 20,
      "total_stock_units": 55,
      "safety_stock_threshold_units": 25,
      "reorder_point_units": 50,
      "holding_cost_per_unit_day_inr": 1.5,
      "unit_selling_price_inr": 90.0,
      "unit_cost_price_inr": 60.0,
      "shelf_replenishment_needed": true
    },
    {
      "sku_id": "SKU_DIET_HERBAL_TEA_250ML",
      "sku_name": "Diet Herbal Green Tea 250ml",
      "shelf_stock_units": 45,
      "shelf_capacity_units": 50,
      "backroom_stock_units": 100,
      "total_stock_units": 145,
      "safety_stock_threshold_units": 10,
      "reorder_point_units": 20,
      "holding_cost_per_unit_day_inr": 1.0,
      "unit_selling_price_inr": 45.0,
      "unit_cost_price_inr": 30.0,
      "shelf_replenishment_needed": false
    }
  ]
}
```

---

### 3.5 `GET /warehouses/availability`
Returns central warehouse stock availability and next scheduled dispatch window.

#### Query Parameters:
- `sku_id` *(required, string)*: SKU to check availability for.

#### Response Body (`200 OK`):
```json
{
  "warehouse_id": "WH_CENTRAL_01",
  "warehouse_name": "Central Distribution Hub West",
  "sku_id": "SKU_COLD_DRINK_750ML",
  "available_stock_units": 2400,
  "reserved_stock_units": 300,
  "free_stock_units": 2100,
  "next_dispatch_window": "2026-10-09T18:30:00Z",
  "standard_transit_time_minutes": 60
}
```

---

### 3.6 `GET /logistics/trucks`
Returns scheduled truck deliveries and expedited delivery options.

#### Query Parameters:
- `store_id` *(required, string)*: e.g., `STORE_007`

#### Response Body (`200 OK`):
```json
{
  "store_id": "STORE_007",
  "scheduled_deliveries": [
    {
      "truck_id": "TRK_STANDARD_404",
      "route_id": "ROUTE_WEST_02",
      "driver_name": "Rajesh Kumar",
      "status": "IN_TRANSIT",
      "scheduled_departure_time": "2026-10-09T17:00:00Z",
      "estimated_arrival_time": "2026-10-09T20:00:00Z",
      "manifest": [
        {
          "sku_id": "SKU_COLD_DRINK_750ML",
          "allocated_quantity_units": 100
        }
      ]
    }
  ],
  "expedited_option": {
    "is_available": true,
    "truck_id": "TRK_EXPRESS_109",
    "earliest_departure_time": "2026-10-09T18:10:00Z",
    "expedited_arrival_time": "2026-10-09T18:35:00Z",
    "transit_duration_minutes": 25,
    "additional_expedited_cost_inr": 350.0
  }
}
```

---

### 3.7 `GET /logistics/donors`
Queries nearby stores with surplus stock that can act as inventory donors.

#### Query Parameters:
- `store_id` *(required, string)*: Receiver store (e.g., `STORE_007`).
- `sku_id` *(required, string)*: Required SKU ID.
- `required_units` *(optional, integer)*: Desired quantity (default: `50`).

#### Response Body (`200 OK`):
```json
{
  "target_store_id": "STORE_007",
  "sku_id": "SKU_COLD_DRINK_750ML",
  "donor_stores": [
    {
      "donor_store_id": "STORE_003",
      "donor_store_name": "Store 3 - Indiranagar",
      "distance_km": 3.4,
      "current_stock_units": 210,
      "surplus_units": 140,
      "transfer_eta_minutes": 28,
      "estimated_transfer_cost_inr": 150.0,
      "feasibility_score": 0.92
    },
    {
      "donor_store_id": "STORE_012",
      "donor_store_name": "Store 12 - HSR Layout",
      "distance_km": 5.1,
      "current_stock_units": 180,
      "surplus_units": 90,
      "transfer_eta_minutes": 40,
      "estimated_transfer_cost_inr": 220.0,
      "feasibility_score": 0.78
    }
  ]
}
```

---

### 3.8 `GET /logistics/riders`
Returns hyper-local rider availability for inter-store stock transfers.

#### Query Parameters:
- `store_id` *(required, string)*: e.g., `STORE_007`

#### Response Body (`200 OK`):
```json
{
  "store_id": "STORE_007",
  "active_riders": 3,
  "required_riders_for_demand": 9,
  "rider_shortage_count": 6,
  "shortage_severity": "HIGH",
  "rider_surge_multiplier": 1.35,
  "transfer_rider_available": true,
  "assigned_rider_id": "RIDER_DEV_88",
  "notes": "Rider availability impacted by heavy rain in zone."
}
```

---

### 3.9 `GET /recommendations`
Invokes the decision engine to get evaluated resolution options for a given stockout alert.

#### Query Parameters:
- `alert_id` *(required, string)*: e.g., `ALT_20261009_007_01`

#### Response Body (`200 OK`):
```json
{
  "alert_id": "ALT_20261009_007_01",
  "store_id": "STORE_007",
  "sku_id": "SKU_COLD_DRINK_750ML",
  "evaluated_at": "2026-10-09T18:00:00Z",
  "recommendations": [
    {
      "recommendation_id": "REC_007_TRF_01",
      "option_type": "TRANSFER",
      "rank": 1,
      "title": "Inter-Store Transfer from Store 3",
      "summary": "Transfer 50 units of Cold Drink 750ml from Store 3 via express rider.",
      "confidence_score": 0.94,
      "stockout_prevented": true,
      "action_parameters": {
        "source_type": "STORE",
        "source_id": "STORE_003",
        "transfer_quantity_units": 50,
        "eta_minutes": 28,
        "estimated_arrival_timestamp": "2026-10-09T18:28:00Z"
      },
      "financial_impact": {
        "execution_cost_inr": 150.0,
        "revenue_saved_inr": 4500.0,
        "net_gain_inr": 4350.0
      },
      "tradeoff_analysis": {
        "pros": ["Arrives before projected stockout (42 mins)", "Low execution cost"],
        "cons": ["Depletes Store 3 surplus by 35%"]
      },
      "is_recommended": true
    },
    {
      "recommendation_id": "REC_007_TRK_02",
      "option_type": "EARLIER_TRUCK",
      "rank": 2,
      "title": "Expedite Warehouse Truck Delivery",
      "summary": "Dispatch express warehouse truck 109 with 100 units.",
      "confidence_score": 0.88,
      "stockout_prevented": true,
      "action_parameters": {
        "source_type": "WAREHOUSE",
        "source_id": "WH_CENTRAL_01",
        "truck_id": "TRK_EXPRESS_109",
        "transfer_quantity_units": 100,
        "eta_minutes": 35,
        "estimated_arrival_timestamp": "2026-10-09T18:35:00Z"
      },
      "financial_impact": {
        "execution_cost_inr": 350.0,
        "revenue_saved_inr": 4500.0,
        "net_gain_inr": 4150.0
      },
      "tradeoff_analysis": {
        "pros": ["Brings full 100 units replenishment"],
        "cons": ["Higher expedited freight fee (₹350)"]
      },
      "is_recommended": false
    },
    {
      "recommendation_id": "REC_007_SWP_03",
      "option_type": "SHELF_SWAP",
      "rank": 3,
      "title": "Shelf Space Swap with Diet Herbal Tea",
      "summary": "Reallocate 25 shelf slots from slow-moving Diet Herbal Tea to Cold Drink 750ml.",
      "confidence_score": 0.75,
      "stockout_prevented": false,
      "action_parameters": {
        "source_sku_id": "SKU_DIET_HERBAL_TEA_250ML",
        "target_sku_id": "SKU_COLD_DRINK_750ML",
        "slots_reallocated": 25,
        "execution_time_minutes": 10
      },
      "financial_impact": {
        "execution_cost_inr": 0.0,
        "revenue_saved_inr": 1800.0,
        "net_gain_inr": 1800.0
      },
      "tradeoff_analysis": {
        "pros": ["Immediate internal fix", "Zero transport cost"],
        "cons": ["Does not add new stock; backroom runs empty faster"]
      },
      "is_recommended": false
    },
    {
      "recommendation_id": "REC_007_WAT_04",
      "option_type": "WAIT",
      "rank": 4,
      "title": "Wait for Standard Scheduled Truck",
      "summary": "Do nothing and await scheduled delivery truck arrival at 20:00.",
      "confidence_score": 0.40,
      "stockout_prevented": false,
      "action_parameters": {
        "expected_stockout_duration_minutes": 78,
        "scheduled_arrival_timestamp": "2026-10-09T20:00:00Z"
      },
      "financial_impact": {
        "execution_cost_inr": 0.0,
        "revenue_saved_inr": 0.0,
        "net_gain_inr": -4500.0
      },
      "tradeoff_analysis": {
        "pros": ["No intervention cost"],
        "cons": ["Results in 78-minute stockout and 50 lost customer orders"]
      },
      "is_recommended": false
    }
  ]
}
```

---

### 3.10 `POST /recommendations/{recommendation_id}/approve`
Submits manager approval for a recommended option.

#### Path Parameters:
- `recommendation_id` *(string)*: e.g., `REC_007_TRF_01`

#### Request Body (`application/json`):
```json
{
  "manager_id": "MGR_KORAMANGALA_07",
  "manager_notes": "Approved express rider transfer from Store 3 due to incoming match crowd.",
  "override_quantity_units": null
}
```

#### Response Body (`200 OK`):
```json
{
  "action_id": "ACT_20261009_8812",
  "alert_id": "ALT_20261009_007_01",
  "recommendation_id": "REC_007_TRF_01",
  "status": "APPROVED",
  "executed_at": "2026-10-09T18:02:00Z",
  "manager_id": "MGR_KORAMANGALA_07",
  "action_summary": "Initiated inter-store transfer of 50 units from STORE_003 to STORE_007.",
  "simulated_outcome": {
    "new_projected_stockout_minutes": null,
    "stockout_prevented": true,
    "expected_arrival_time": "2026-10-09T18:30:00Z"
  }
}
```

---

### 3.11 `POST /recommendations/{recommendation_id}/reject`
Rejects a recommendation with mandatory feedback.

#### Request Body (`application/json`):
```json
{
  "manager_id": "MGR_KORAMANGALA_07",
  "rejection_reason": "STORE_3_RIDER_UNAVAILABLE",
  "notes": "Rider stuck in flood zone near Store 3."
}
```

#### Response Body (`200 OK`):
```json
{
  "recommendation_id": "REC_007_TRF_01",
  "status": "REJECTED",
  "rejected_at": "2026-10-09T18:03:00Z",
  "remaining_pending_recommendations": ["REC_007_TRK_02", "REC_007_SWP_03"]
}
```

---

### 3.12 `GET /actions/history`
Queries past approved, rejected, and simulated actions for audit and analytics.

#### Query Parameters:
- `store_id` *(optional, string)*: Filter by store.
- `limit` *(optional, integer)*: Results limit (default: `20`).

#### Response Body (`200 OK`):
```json
{
  "total_records": 1,
  "actions": [
    {
      "action_id": "ACT_20261009_8812",
      "alert_id": "ALT_20261009_007_01",
      "store_id": "STORE_007",
      "sku_id": "SKU_COLD_DRINK_750ML",
      "action_type": "TRANSFER",
      "status": "EXECUTED",
      "manager_id": "MGR_KORAMANGALA_07",
      "created_at": "2026-10-09T18:02:00Z",
      "cost_inr": 150.0,
      "revenue_saved_inr": 4500.0,
      "notes": "Approved express rider transfer from Store 3 due to incoming match crowd."
    }
  ]
}
```

---

### 3.13 `POST /simulation/recalculate`
Runs what-if scenario simulations with custom dynamic parameters without modifying DB state.

#### Request Body (`application/json`):
```json
{
  "store_id": "STORE_007",
  "sku_id": "SKU_COLD_DRINK_750ML",
  "simulated_parameters": {
    "cricket_match_multiplier": 3.0,
    "rain_intensity_mm_hr": 35.0,
    "available_riders": 1,
    "custom_transfer_quantity_units": 75
  }
}
```

#### Response Body (`200 OK`):
```json
{
  "simulation_id": "SIM_20261009_9941",
  "simulated_at": "2026-10-09T18:05:00Z",
  "recalculated_demand_peak_units": 95,
  "recalculated_stockout_minutes": 28,
  "simulated_recommendations": [
    {
      "recommendation_id": "REC_SIM_01",
      "option_type": "EARLIER_TRUCK",
      "rank": 1,
      "summary": "Transfer from Store 3 delayed due to rider shortage (1 rider). Expedited truck recommended instead.",
      "confidence_score": 0.91,
      "stockout_prevented": true
    }
  ]
}
```

---

## 4. Inter-Store Coordination & Authentication API Specifications

### 4.1 `POST /auth/login`
Authenticates a Store Manager or City Operations Manager and issues a Bearer JWT access token.

#### Request Body (`application/json`):
```json
{
  "username": "manager_store_007",
  "password": "PulseStock2026!"
}
```

#### Response Body (`200 OK`):
```json
{
  "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "token_type": "bearer",
  "manager": {
    "manager_id": "MGR_STORE_007",
    "username": "manager_store_007",
    "full_name": "Manager - Store 7 - Koramangala Tech Park",
    "role": "STORE_MANAGER",
    "store_id": "STORE_007"
  }
}
```

---

### 4.2 `GET /auth/me`
Retrieves authenticated manager profile details from Bearer token.

#### Request Headers:
`Authorization: Bearer <access_token>`

#### Response Body (`200 OK`):
```json
{
  "manager_id": "MGR_STORE_007",
  "username": "manager_store_007",
  "full_name": "Manager - Store 7 - Koramangala Tech Park",
  "role": "STORE_MANAGER",
  "store_id": "STORE_007"
}
```

---

### 4.3 `GET /coordination/requests`
Lists inter-store stock and rider transfer requests for the manager's store or city wide.

#### Headers:
`Authorization: Bearer <access_token>`

#### Query Parameters:
- `store_id` *(optional, string)*: Filter by store (e.g. `STORE_007`).
- `role` *(optional, string)*: `REQUESTING`, `DONOR`, or `ALL`.
- `status` *(optional, string)*: Filter by status (`REQUESTED`, `PENDING_CITY_APPROVAL`, `APPROVED`, etc.).
- `request_type` *(optional, string)*: `STOCK_TRANSFER` or `RIDER_TRANSFER`.

#### Response Body (`200 OK`):
```json
[
  {
    "request_id": "REQ_20261010_4142C5",
    "request_type": "STOCK_TRANSFER",
    "requesting_store_id": "STORE_007",
    "requesting_store_name": "Store 7 - Koramangala Tech Park",
    "donor_store_id": "STORE_003",
    "donor_store_name": "Store 3 - Indiranagar",
    "sku_id": "SKU_COLD_DRINK_750ML",
    "sku_name": "Sparkling Cola 750ml",
    "requested_quantity": 50,
    "requested_riders_count": null,
    "start_time": null,
    "end_time": null,
    "status": "APPROVED",
    "created_by_manager_id": "MGR_STORE_007",
    "reason": "Cold drink stockout prevention",
    "estimated_cost_inr": 181.0,
    "estimated_net_benefit_inr": null,
    "financial_benefit_status": "UNAVAILABLE_AWAITING_ENGINE",
    "created_at": "2026-10-10T18:00:00Z",
    "updated_at": "2026-10-10T18:05:00Z",
    "history": [
      {
        "approval_id": "APP_001",
        "actor_manager_id": "MGR_STORE_007",
        "actor_role": "STORE_MANAGER",
        "action": "CREATE",
        "from_status": "NONE",
        "to_status": "REQUESTED",
        "reason": "Cold drink stockout prevention",
        "timestamp": "2026-10-10T18:00:00Z"
      }
    ]
  }
]
```

---

### 4.4 `POST /coordination/requests`
Creates a new inter-store stock or rider transfer request.

#### Headers:
`Authorization: Bearer <access_token>`

#### Request Body (`application/json`):
```json
{
  "request_type": "RIDER_TRANSFER",
  "requesting_store_id": "STORE_007",
  "donor_store_id": "STORE_003",
  "requested_riders_count": 3,
  "start_time": "2026-10-10T18:00:00Z",
  "end_time": "2026-10-10T20:00:00Z",
  "reason": "Match crowd surge expected; 6 rider shortage at Store 7."
}
```

---

### 4.5 `POST /coordination/requests/{request_id}/donor-accept`
Donor store manager accepts request and creates temporary stock/rider reservation.

#### Request Body:
```json
{
  "notes": "Store 3 manager agrees to lend 3 riders for 2 hours."
}
```

---

### 4.6 `POST /coordination/requests/{request_id}/city-approve`
City Operations Manager grants final approval and applies simulated movement.

#### Request Body:
```json
{
  "notes": "City Ops authorization granted."
}
```

---

### 4.7 `GET /coordination/stock-availability`
Checks donor stock availability, unreserved inventory, and safe surplus.

#### Query Parameters:
- `store_id` *(required, string)*: `STORE_003`
- `sku_id` *(required, string)*: `SKU_COLD_DRINK_750ML`
- `required_units` *(optional, int)*: `50`

---

### 4.8 `GET /coordination/rider-availability`
Checks donor rider fleet availability for specified time window.

#### Query Parameters:
- `store_id` *(required, string)*: `STORE_003`
- `start_time` *(optional, datetime)*
- `end_time` *(optional, datetime)*
- `required_riders` *(optional, int)*: `3`

---

### 4.9 `GET /notifications`
Polls notifications for the authenticated manager.

#### Headers:
`Authorization: Bearer <access_token>`

#### Response Body (`200 OK`):
```json
[
  {
    "notification_id": "NOTIF_001",
    "manager_id": "MGR_CITY_OPS",
    "title": "Inter-Store Request Created",
    "message": "Store 7 requested transfer from Store 3.",
    "type": "REQUEST_CREATED",
    "request_id": "REQ_20261010_4142C5",
    "is_read": false,
    "created_at": "2026-10-10T18:00:00Z"
  }
]
```

