try:
    from backend.routers.health import router as health_router
    from backend.routers.alerts import router as alerts_router
    from backend.routers.forecast import router as forecast_router
    from backend.routers.events import router as events_router
    from backend.routers.stores import router as stores_router
    from backend.routers.warehouses import router as warehouses_router
    from backend.routers.logistics import router as logistics_router
    from backend.routers.recommendations import router as recommendations_router
    from backend.routers.actions import router as actions_router
    from backend.routers.simulation import router as simulation_router
    from backend.routers.auth import router as auth_router
    from backend.routers.coordination import router as coordination_router
    from backend.routers.notifications import router as notifications_router
except ImportError:
    from routers.health import router as health_router
    from routers.alerts import router as alerts_router
    from routers.forecast import router as forecast_router
    from routers.events import router as events_router
    from routers.stores import router as stores_router
    from routers.warehouses import router as warehouses_router
    from routers.logistics import router as logistics_router
    from routers.recommendations import router as recommendations_router
    from routers.actions import router as actions_router
    from routers.simulation import router as simulation_router
    from routers.auth import router as auth_router
    from routers.coordination import router as coordination_router
    from routers.notifications import router as notifications_router

__all__ = [
    "health_router",
    "alerts_router",
    "forecast_router",
    "events_router",
    "stores_router",
    "warehouses_router",
    "logistics_router",
    "recommendations_router",
    "actions_router",
    "simulation_router",
    "auth_router",
    "coordination_router",
    "notifications_router",
]
