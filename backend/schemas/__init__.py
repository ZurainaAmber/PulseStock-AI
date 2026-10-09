try:
    from backend.schemas.health import HealthResponse
    from backend.schemas.error import ErrorResponse, ErrorDetail
except ImportError:
    from schemas.health import HealthResponse
    from schemas.error import ErrorResponse, ErrorDetail

__all__ = ["HealthResponse", "ErrorResponse", "ErrorDetail"]
