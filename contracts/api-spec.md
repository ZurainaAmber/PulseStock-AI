# PulseStock AI — API Specification Contract
**Cypher 2026 · Challenge 6: Before the Match Starts (Zipcart)**  
**Version:** 1.0.0 · **Base URL:** `http://localhost:8000/api/v1`

---

## 1. Overview & Architectural Principles

This API contract enables the **React Frontend** and **FastAPI Backend** to be developed independently with zero ambiguity.

- **Format:** All requests and responses use standard `application/json`.
- **CORS:** Enabled for `http://localhost:5173` (Vite) and `http://localhost:3000`.
- **Error Handling:** Standardized error envelopes with machine-readable error codes.
- **Mocking:** The frontend team can point to `contracts/example-response.json` or use MSW (Mock Service Worker) while the backend is being wired up.

---

## 2. API Endpoints Summary


| Method | Endpoint | Description |
|---|---|---|
| `GET` | `/health` | Service health and DB connection check |
| `GET` | `/dashboard/summary` | Top-level KPI counts, surge status, and margin protected |
| `GET` | `/alerts` | Attention list of all stores and SKUs needing intervention |
| `GET` | `/alerts/{alert_id}` | Complete detail of a single alert (timeline, options, AI rationale) |
| `POST` | `/alerts/{alert_id}/decision` | Manager action: Approve, Edit Quantity, or Reject |
| `GET` | `/stores/{store_id}/timeline` | Hour-by-hour stock curve with event uplift for Recharts |
| `GET` | `/manifest/3-day` | 3-Day event multi-truck replenishment drops |
| `POST` | `/simulation/traffic-block` | Trigger simulated road blockage to demo real-time re-planning |
| `POST` | `/simulation/what-if` | Run what-if scenario with adjusted uplift multipliers |
| `GET` | `/actions/logs` | Immutable audit log of all manager actions taken |
=======
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

## 3. Detailed Endpoint Contracts

### 3.1 `GET /api/v1/health`
Checks server and SQLite database readiness.

#### Response `200 OK`:
```json
{
  "status": "HEALTHY",
  "version": "1.0.0",
  "timestamp": "2026-10-10T17:00:00Z",
  "database": "sqlite:///pulsestock.db",
  "data_loaded": {
    "products_count": 25,
    "stores_count": 10,
    "trucks_scheduled": 14
  }
}
```

---

### 3.2 `GET /api/v1/dashboard/summary`
Powers the top KPI stat cards in the React dashboard.

#### Response `200 OK`:
```json
{
  "total_active_alerts": 4,
  "critical_alerts_count": 2,
  "high_alerts_count": 2,
  "total_net_margin_protected_inr": 5537.00,
  "system_scope_mode": "CITY_WIDE_SURGE",
  "surge_category": "CAT_BEVERAGES",
  "affected_stores_percentage": 60.0,
  "upcoming_event": {
    "event_id": "EVT_IND_VS_PAK_FINAL",
    "name": "Ind vs Pak T20 Final",
    "starts_in_minutes": 150,
    "peak_uplift": 3.0
  }
}
```

---

### 3.3 `GET /api/v1/alerts`
Returns the operational **Attention List**. Sorted by urgency and net margin protected descending.

#### Query Parameters:
- `urgency` (optional, string): Filter by `CRITICAL`, `HIGH`, `MEDIUM`
- `store_id` (optional, string): Filter by store, e.g., `STORE_007`
- `scope_mode` (optional, string): Filter by `LOCAL` or `CITY_WIDE_SURGE`

#### Response `200 OK`:
Returns an array of alert cards matching the format in `example-response.json`:
```json
[
  {
    "alert_id": "ALT-20261010-007-COLD-DRINK",
    "store_id": "STORE_007",
    "store_name": "Koramangala Dark Store 7",
    "sku_id": "SKU_COLD_DRINK_750ML",
    "product_name": "FizzCola Zero 750ml",
    "urgency": "CRITICAL",
    "bottleneck_type": "STOCK_DEFICIT",
    "current_stock": 14,
    "stockout_time": "2026-10-10T20:13:00Z",
    "next_truck_time": "2026-10-10T21:00:00Z",
    "exposure_minutes": 47,
    "projected_lost_units": 7,
    "net_margin_protected": 72.50,
    "recommended_action_title": "Clear Snack Slot & Transfer 10 Units from Store 9",
    "status": "PENDING"
  }
]
```

---

### 3.4 `GET /api/v1/alerts/{alert_id}`
Returns full inspection payload for the manager approval drawer/modal.

#### Path Parameter:
- `alert_id` (string): ID of alert, e.g., `ALT-20261010-007-COLD-DRINK`

#### Response `200 OK`:
Returns full JSON object matching Section 2 of `contracts/example-response.json` (includes `demand_timeline`, `recommendations.primary`, `recommendations.fallback`, and `agent_explanation`).

#### Response `404 Not Found`:
```json
{
  "error": {
    "code": "ALERT_NOT_FOUND",
    "message": "Alert 'ALT-999' was not found or has expired.",
    "status": 404
  }
}
```

---

### 3.5 `POST /api/v1/alerts/{alert_id}/decision`
Records manager interaction (Approval, Edit Quantity, or Rejection).

#### Request Body:
```json
{
  "manager_id": "MGR_ROHIT_S",
  "decision": "APPROVED",
  "chosen_option": "PRIMARY",
  "edited_quantity": null,
  "manager_notes": "Approved swap and transfer. Instructed floor picker to clear shelf SLOT_SNACK_B2 immediately."
}
```
*Allowed `decision` values:* `"APPROVED"`, `"EDITED_AND_APPROVED"`, `"REJECTED"`  
*Allowed `chosen_option` values:* `"PRIMARY"`, `"FALLBACK"`  
*`edited_quantity`:* Optional integer if manager adjusts the quantity slider.

#### Response `200 OK`:
```json
{
  "status": "SUCCESS",
  "alert_id": "ALT-20261010-007-COLD-DRINK",
  "decision": "APPROVED",
  "log_id": 104,
  "executed_action": "COMBINED_SWAP_AND_TRANSFER",
  "executed_quantity": 10,
  "re_plan_triggered": false,
  "message": "Transfer order #XFER-709 dispatched. Shelf swap instruction sent to Store 7 handheld."
}
```

#### If `decision: "REJECTED"`:
The backend automatically executes the Re-Planning Engine (`trigger_replan`):
```json
{
  "status": "SUCCESS",
  "alert_id": "ALT-20261010-007-COLD-DRINK",
  "decision": "REJECTED",
  "log_id": 105,
  "re_plan_triggered": true,
  "message": "Primary action rejected. Fallback (Early Truck TRUCK_NORTH_101) promoted to active recommendation.",
  "new_recommendation": {
    "action_type": "EARLY_TRUCK",
    "title": "Pull Scheduled Truck TRUCK_NORTH_101 Forward by 45 Minutes",
    "net_margin_protected": 49.50
  }
}
```

---

### 3.6 `GET /api/v1/stores/{store_id}/timeline`
Used directly by Recharts `<ResponsiveContainer>` to plot the interactive hour-by-hour stock depletion curve.

#### Query Parameters:
- `sku_id` (required, string): e.g., `SKU_COLD_DRINK_750ML`

#### Response `200 OK`:
```json
{
  "store_id": "STORE_007",
  "sku_id": "SKU_COLD_DRINK_750ML",
  "product_name": "FizzCola Zero 750ml",
  "truck_arrival_hour": "21:00",
  "stockout_hour": "20:13",
  "points": [
    {
      "time": "17:00",
      "baseline_demand": 3.0,
      "event_multiplier": 1.0,
      "projected_demand": 3.0,
      "projected_stock": 11.0,
      "shelf_capacity": 25,
      "is_stockout": false
    },
    {
      "time": "18:00",
      "baseline_demand": 3.0,
      "event_multiplier": 1.0,
      "projected_demand": 3.0,
      "projected_stock": 8.0,
      "shelf_capacity": 25,
      "is_stockout": false
    },
    {
      "time": "19:00",
      "baseline_demand": 3.0,
      "event_multiplier": 2.0,
      "projected_demand": 6.0,
      "projected_stock": 2.0,
      "shelf_capacity": 25,
      "is_stockout": false
    },
    {
      "time": "20:00",
      "baseline_demand": 3.0,
      "event_multiplier": 3.0,
      "projected_demand": 9.0,
      "projected_stock": 0.0,
      "shelf_capacity": 25,
      "is_stockout": true
    },
    {
      "time": "21:00",
      "baseline_demand": 3.0,
      "event_multiplier": 3.0,
      "projected_demand": 9.0,
      "projected_stock": 0.0,
      "shelf_capacity": 25,
      "is_stockout": true
    }
  ]
}
```

---

### 3.7 `GET /api/v1/manifest/3-day`
Powers the **3-Day Event Manifest Table** (Differentiator).

#### Query Parameters:
- `store_id` (required, string): e.g., `STORE_007`
- `event_id` (required, string): e.g., `EVT_IND_VS_PAK_FINAL`

#### Response `200 OK`:
```json
{
  "store_id": "STORE_007",
  "event_id": "EVT_IND_VS_PAK_FINAL",
  "manifest_summary": "Sequenced replenishment top-ups respecting hard shelf limits.",
  "drops": [
    {
      "phase": "DAY_BEFORE (Fri)",
      "truck_id": "TRUCK_N10",
      "arrival_time": "2026-10-09T18:00:00Z",
      "sku_id": "SKU_COLD_DRINK_750ML",
      "drop_quantity": 25,
      "binding_constraint": "limited by shelf slot: 25 units",
      "margin_density": 13.50,
      "status": "CONFIRMED"
    },
    {
      "phase": "EVENT_DAY PEAK (Sat)",
      "truck_id": "TRUCK_N12",
      "arrival_time": "2026-10-10T16:00:00Z",
      "sku_id": "SKU_COLD_DRINK_750ML",
      "drop_quantity": 30,
      "binding_constraint": "limited by truck capacity: 30 units",
      "margin_density": 13.50,
      "status": "RECOMMENDED"
    },
    {
      "phase": "DAY_AFTER TAPER (Sun)",
      "truck_id": "TRUCK_N15",
      "arrival_time": "2026-10-11T10:00:00Z",
      "sku_id": "SKU_COLD_DRINK_750ML",
      "drop_quantity": 8,
      "binding_constraint": "demand taper floor (prevents overstock)",
      "margin_density": 13.50,
      "status": "PLANNED"
    }
  ]
}
```

---

### 3.8 `POST /api/v1/simulation/traffic-block`
Simulates a live traffic blockage to show judge panel real-time re-planning.

#### Request Body:
```json
{
  "origin_store_id": "STORE_009",
  "destination_store_id": "STORE_007",
  "is_blocked": true,
  "incident_description": "Water logging / severe jam on 100ft Road"
}
```

#### Response `200 OK`:
```json
{
  "status": "INCIDENT_INJECTED",
  "route": "STORE_009 -> STORE_007",
  "previous_eta_minutes": 32,
  "new_status": "ARRIVES_TOO_LATE",
  "re_plan_triggered": true,
  "message": "Transfer from Store 9 cancelled due to blockage. Fallback promoted: Pulling Truck TRUCK_NORTH_101 forward."
}
```

---

### 3.9 `GET /api/v1/actions/logs`
Returns the immutable audit log table.

#### Response `200 OK`:
```json
[
  {
    "log_id": 104,
    "timestamp": "2026-10-10T17:05:12Z",
    "alert_id": "ALT-20261010-007-COLD-DRINK",
    "store_id": "STORE_007",
    "sku_id": "SKU_COLD_DRINK_750ML",
    "manager_id": "MGR_ROHIT_S",
    "decision": "APPROVED",
    "action_type": "COMBINED_SWAP_AND_TRANSFER",
    "final_quantity": 10,
    "execution_status": "SIMULATED_SUCCESS",
    "manager_notes": "Approved swap and transfer."
  }
]
```

---

## 4. Error Responses

All error responses adhere to standard HTTP status codes with this consistent body structure:

```json
{
  "error": {
    "code": "INVALID_DECISION_PAYLOAD",
    "message": "Quantity cannot exceed slot capacity of 25 units.",
    "field": "edited_quantity",
    "status": 422
  }
}
```


### Common Error Codes:
- `400 BAD_REQUEST`: Malformed request syntax.
- `404 NOT_FOUND`: Resource (Store, SKU, Alert) does not exist.
- `422 UNPROCESSABLE_ENTITY`: Business rule validation error (e.g., negative quantity, capacity overflow).
- `500 INTERNAL_ERROR`: Unexpected backend exception.
=======
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

