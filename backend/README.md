# PulseStock AI - Backend Service

**Technology Stack:** Python 3.10+ | FastAPI | SQLite | SQLAlchemy  
**Context:** Cypher 2026 Challenge 6 - Store 7 Stock-out Prevention & Decision Engine  

---

## 🚀 Beginner Quick Start Guide

### 1. Prerequisites
- Python 3.10 or higher installed on your computer.

### 2. Set Up Virtual Environment (Recommended)

Open your terminal in the workspace root directory:

```bash
# Move into the backend folder (if running commands directly)
cd backend

# Create virtual environment
python -m venv venv

# Activate virtual environment:
# On Windows (Command Prompt):
venv\Scripts\activate
# On Windows (PowerShell):
.\venv\Scripts\Activate.ps1
# On macOS / Linux:
source venv/bin/activate
```

### 3. Install Dependencies

```bash
pip install -r requirements.txt
```

### 4. Configuration (Optional)
A default `.env.example` is provided. Copy it to `.env` if custom host/port settings are required:

```bash
cp .env.example .env
```

### 5. Start Local Backend Server

Run from the repository root:

```bash
python -m uvicorn backend.main:app --reload --host 0.0.0.0 --port 8000
```

The backend server will start at:
👉 **Local API URL:** `http://localhost:8000`  
👉 **Swagger API Interactive Docs:** `http://localhost:8000/docs`  
👉 **ReDoc Documentation:** `http://localhost:8000/redoc`  

---

## 🧪 Testing Server Health

To verify the backend and SQLite database connection, send a GET request to `/health`:

### Using cURL:
```bash
curl http://localhost:8000/health
```

### Expected Response:
```json
{
  "status": "ok",
  "service": "PulseStock AI Backend",
  "database": "connected",
  "timestamp": "2026-10-09T21:45:00Z"
}
```

---

## 📁 Directory Architecture

```
backend/
├── .env.example        # Sample environment variables
├── .gitignore          # Git ignore rules for DB, venv, pycache
├── requirements.txt    # Python dependencies
├── README.md           # Beginner friendly quick start guide
├── main.py             # FastAPI app initialization & CORS setup
├── config.py           # Application configuration settings
├── database.py         # SQLAlchemy engine & SQLite session setup
├── models/             # SQLAlchemy ORM Database models (7 tables)
│   ├── store.py
│   ├── sku.py
│   ├── inventory.py
│   ├── event.py
│   ├── alert.py
│   ├── recommendation.py
│   └── action_log.py
├── schemas/            # Pydantic validation & response schemas
│   ├── health.py
│   └── error.py
└── routers/            # API endpoint routers
    ├── health.py
    ├── alerts.py
    ├── forecast.py
    ├── events.py
    ├── stores.py
    ├── warehouses.py
    ├── logistics.py
    ├── recommendations.py
    ├── actions.py
    └── simulation.py
```
