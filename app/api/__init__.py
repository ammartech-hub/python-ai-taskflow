"""API routes package exports."""

from app.api.auth import router as auth_router
from app.api.tasks import router as tasks_router
from app.api.admin import router as admin_router

__all__ = ["auth_router", "tasks_router", "admin_router"]
