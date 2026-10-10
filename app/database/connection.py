"""Database engine, session factory, and FastAPI dependency."""

import logging
from typing import Generator
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker, Session
from app.config import settings

logger = logging.getLogger(__name__)

import os
from sqlalchemy.pool import NullPool

# Determine connection arguments based on database dialect
connect_args = {}
engine_kwargs = {}

db_url = settings.sync_database_url

if db_url.startswith("sqlite"):
    connect_args["check_same_thread"] = False
elif os.getenv("VERCEL") or os.getenv("AWS_LAMBDA_FUNCTION_NAME") or os.getenv("SERVERLESS"):
    # In serverless lambda environments, avoid holding pool connections across sleep cycles
    engine_kwargs["poolclass"] = NullPool
    engine_kwargs["pool_pre_ping"] = True
else:
    # Production persistent server PostgreSQL connection pool configuration
    engine_kwargs.update({
        "pool_pre_ping": True,
        "pool_size": 10,
        "max_overflow": 20,
        "pool_recycle": 1800,
        "pool_reset_on_return": "rollback",
    })

engine = create_engine(
    db_url,
    connect_args=connect_args,
    **engine_kwargs,
)

SessionLocal = sessionmaker(
    autocommit=False,
    autoflush=False,
    bind=engine,
)


def get_db() -> Generator[Session, None, None]:
    """FastAPI dependency that provides an isolated SQLAlchemy database session.

    Ensures transactions are rolled back upon unhandled exceptions and sessions
    are deterministically closed.
    """
    db: Session = SessionLocal()
    try:
        yield db
    except Exception:
        try:
            db.rollback()
        except Exception:
            pass
        raise
    finally:
        try:
            if db.is_active:
                db.rollback()
        except Exception:
            pass
        db.close()


def check_database_connection() -> bool:
    """Verify active database connectivity for health checks."""
    try:
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        return True
    except Exception as exc:
        logger.warning("Database connectivity check failed: %s", exc)
        return False


def check_tables_exist() -> bool:
    """Verify core database tables exist."""
    try:
        from sqlalchemy import inspect
        inspector = inspect(engine)
        tables = inspector.get_table_names()
        return "users" in tables and "tasks" in tables
    except Exception:
        return False


def ensure_database_initialized() -> bool:
    """Ensure database schema tables and seed data exist (essential for serverless)."""
    try:
        from app.database.base import Base
        import app.models  # noqa: F401
        from app.models.user import User

        # Create tables if not already present
        Base.metadata.create_all(bind=engine)

        # Verify seed records
        with SessionLocal() as db:
            admin = db.query(User).filter(User.email == settings.SEED_ADMIN_EMAIL.lower().strip()).first()
            if not admin:
                logger.info("Initializing database with seed accounts...")
                from scripts.seed import seed_database
                seed_database()

        return True
    except Exception as exc:
        logger.warning("Auto-initialization of schema/seed data skipped or failed: %s", exc)
        return False

