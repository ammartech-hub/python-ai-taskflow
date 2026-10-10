"""FastAPI Application Entry Point.

Configures routing, middleware, centralized exception handling, OpenAPI docs,
and service health checks.
"""

import logging
from contextlib import asynccontextmanager
from typing import AsyncGenerator
from fastapi import FastAPI, Request, status
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.exc import SQLAlchemyError, IntegrityError

from app.config import settings
from app.database.connection import check_database_connection, check_tables_exist, ensure_database_initialized
from app.api import auth_router, tasks_router, admin_router
from app.ai.gemini_service import AIServiceException

# Configure logging format
logging.basicConfig(
    level=logging.INFO if not settings.DEBUG else logging.DEBUG,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger("taskflow_app")


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """Application lifespan manager for startup and shutdown routines."""
    logger.info("Starting %s v%s in %s mode", settings.APP_NAME, settings.APP_VERSION, settings.ENVIRONMENT)
    db_ok = check_database_connection()
    if db_ok:
        logger.info("Database connection established successfully.")
        # Ensure tables and seed records exist automatically (essential for serverless)
        ensure_database_initialized()
    else:
        logger.warning("Database connection failed or pending configuration. Verify DATABASE_URL.")

    if settings.is_ai_configured:
        logger.info("Google Gemini AI integration enabled with model: %s", settings.GEMINI_MODEL)
    else:
        logger.info("Google Gemini API key not provided. AI endpoints will return configuration error.")

    yield

    logger.info("Shutting down %s.", settings.APP_NAME)


app = FastAPI(
    title=settings.APP_NAME,
    version=settings.APP_VERSION,
    description=(
        "Production-grade RESTful API for an AI-Powered Task Management System. "
        "Includes JWT Bearer authentication, role-based authorization (RBAC), "
        "task lifecycle tracking, and Google Gemini AI assistance."
    ),
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_url="/openapi.json",
    lifespan=lifespan,
)

# CORS configuration for client integration (Bearer tokens work universally with allow_credentials=False)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ==============================================================================
# Centralized Exception Handlers
# ==============================================================================

@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    """Centralized handler for Pydantic validation errors (HTTP 422)."""
    errors = []
    for err in exc.errors():
        loc = " -> ".join(str(l) for l in err.get("loc", []))
        errors.append({
            "field": loc,
            "message": err.get("msg"),
            "type": err.get("type"),
        })
    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        content={
            "detail": "Request validation failed",
            "errors": errors,
        },
    )


@app.exception_handler(AIServiceException)
async def ai_service_exception_handler(request: Request, exc: AIServiceException):
    """Centralized handler for AI provider exceptions."""
    return JSONResponse(
        status_code=exc.status_code,
        content={"detail": exc.message},
    )


@app.exception_handler(IntegrityError)
async def integrity_error_handler(request: Request, exc: IntegrityError):
    """Handle database unique or foreign key constraint collisions (HTTP 409)."""
    logger.warning("Database integrity violation: %s", exc.orig if hasattr(exc, "orig") else exc)
    return JSONResponse(
        status_code=status.HTTP_409_CONFLICT,
        content={"detail": "A database constraint violation occurred (e.g. duplicate key or invalid reference)."},
    )


@app.exception_handler(SQLAlchemyError)
async def sqlalchemy_error_handler(request: Request, exc: SQLAlchemyError):
    """Safely catch unhandled database errors without exposing connection strings or schema."""
    logger.error("Database operation error on %s %s: %s", request.method, request.url.path, exc, exc_info=True)
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={"detail": "An internal database error occurred. The transaction has been aborted."},
    )


@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    """Catch-all unexpected error handler to prevent internal credential leakage."""
    logger.error("Unhandled server exception on %s %s: %s", request.method, request.url.path, exc, exc_info=True)
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={"detail": "An internal server error occurred."},
    )


# ==============================================================================
# Health and Informational Endpoints
# ==============================================================================

import os
from fastapi.responses import JSONResponse, FileResponse
from fastapi.staticfiles import StaticFiles

# Resolve frontend directory path robustly across local dev, Docker, and Vercel Lambda
candidate_dirs = [
    os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "frontend")),
    os.path.abspath(os.path.join(os.getcwd(), "frontend")),
    os.path.abspath("/var/task/frontend"),
]
frontend_dir = next((d for d in candidate_dirs if os.path.isdir(d)), candidate_dirs[0])
if os.path.exists(frontend_dir):
    app.mount("/static", StaticFiles(directory=frontend_dir), name="static")


@app.get(
    "/health",
    tags=["System"],
    summary="Application health check",
    description="Reports API operational status, database connectivity, and AI service readiness.",
)
def health_check():
    """Verify application health and external dependencies."""
    db_alive = check_database_connection()
    tables_ready = check_tables_exist() if db_alive else False
    return {
        "status": "healthy" if (db_alive and tables_ready) else ("degraded" if db_alive else "down"),
        "database_connected": db_alive,
        "tables_initialized": tables_ready,
        "ai_configured": settings.is_ai_configured,
        "environment": settings.ENVIRONMENT,
        "version": settings.APP_VERSION,
    }


@app.get(
    "/",
    tags=["System"],
    summary="Web Application Frontend",
)
def root(request: Request):
    """Serve the modern TaskFlow AI Web Dashboard SPA."""
    index_path = os.path.join(frontend_dir, "index.html")
    if os.path.exists(index_path):
        return FileResponse(index_path)
    return {
        "name": settings.APP_NAME,
        "version": settings.APP_VERSION,
        "docs_url": "/docs",
        "health_url": "/health",
        "message": "Welcome to the AI-Powered Task Management System API.",
    }


# ==============================================================================
# API Routers Registration under /api
# ==============================================================================

app.include_router(auth_router, prefix="/api")
app.include_router(tasks_router, prefix="/api")
app.include_router(admin_router, prefix="/api")
