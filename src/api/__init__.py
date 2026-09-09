"""FastAPI APIRouter definitions for water-meter-digitizer."""

from api.routes_health import router as health_router
from api.routes_history import router as history_router
from api.routes_meter import get_meter_data
from api.routes_meter import router as meter_router
from api.routes_services import router as services_router
from api.routes_system import router as system_router

__all__ = [
    "get_meter_data",
    "health_router",
    "history_router",
    "meter_router",
    "services_router",
    "system_router",
]
