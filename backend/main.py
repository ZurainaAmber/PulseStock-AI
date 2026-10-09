from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager

try:
    from backend.config import settings
    from backend.database import init_db
    from backend.routers import (
        health_router,
        alerts_router,
        forecast_router,
        events_router,
        stores_router,
        warehouses_router,
        logistics_router,
        recommendations_router,
        actions_router,
        simulation_router,
    )
except ImportError:
    from config import settings
    from database import init_db
    from routers import (
        health_router,
        alerts_router,
        forecast_router,
        events_router,
        stores_router,
        warehouses_router,
        logistics_router,
        recommendations_router,
        actions_router,
        simulation_router,
    )

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Lifecycle manager to initialize database tables on server startup."""
    init_db()
    yield

app = FastAPI(
    title="PulseStock AI Backend",
    version="1.0.0",
    description="Backend API for Cypher 2026 Challenge 6 - Store 7 Stock-out Prevention & Decision Engine",
    lifespan=lifespan,
    docs_url="/docs",
    redoc_url="/redoc"
)

# CORS Configuration for local React frontend development
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mount Routers
app.include_router(health_router)
app.include_router(alerts_router)
app.include_router(forecast_router)
app.include_router(events_router)
app.include_router(stores_router)
app.include_router(warehouses_router)
app.include_router(logistics_router)
app.include_router(recommendations_router)
app.include_router(actions_router)
app.include_router(simulation_router)

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("backend.main:app", host=settings.HOST, port=settings.PORT, reload=True)
