"""FastAPI APIRouter definitions for water-meter-digitizer."""

from api.routes_system import router as system_router
from api.routes_health import router as health_router
from api.routes_meter import router as meter_router, get_meter_data
from api.routes_history import router as history_router
from api.routes_services import router as services_router

__all__ = [
    "system_router",
    "health_router",
    "meter_router",
    "history_router",
    "services_router",
    "get_meter_data",
]
