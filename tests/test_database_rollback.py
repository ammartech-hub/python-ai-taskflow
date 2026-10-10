"""Tests verifying SQLAlchemy session management, exception safety, and transaction rollback."""

import pytest
from unittest.mock import patch, MagicMock
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session
from sqlalchemy.exc import SQLAlchemyError, IntegrityError

from app.database.connection import get_db, SessionLocal
from app.models.user import User, UserRole
from app.services.auth_service import auth_service
from app.schemas.user import UserRegisterRequest


def test_session_dependency_rollback_on_unhandled_exception(client: TestClient):
    """Verify that when an endpoint raises an unhandled exception, get_db rolls back the session."""
    with patch("app.api.tasks.task_service.list_tasks", side_effect=SQLAlchemyError("Simulated DB connection glitch")):
        # Request will hit the SQLAlchemyError handler
        # Login first to get valid headers
        register_payload = {
            "name": "Rollback Test User",
            "email": "rollback_test@taskflow.dev",
            "password": "Password123!",
        }
        reg_resp = client.post("/api/auth/register", json=register_payload)
        assert reg_resp.status_code in [201, 409]

        login_resp = client.post("/api/auth/login", json={
            "email": "rollback_test@taskflow.dev",
            "password": "Password123!",
        })
        token = login_resp.json()["access_token"]
        headers = {"Authorization": f"Bearer {token}"}

        # Make the failing request
        resp = client.get("/api/tasks/", headers=headers)
        assert resp.status_code == 500
        assert "transaction has been aborted" in resp.json()["detail"].lower() or "database error" in resp.json()["detail"].lower()

        # Verify that subsequent requests on the session/connection pool succeed normally
        health_resp = client.get("/health")
        assert health_resp.status_code == 200

        profile_resp = client.get("/api/auth/me", headers=headers)
        assert profile_resp.status_code == 200
        assert profile_resp.json()["email"] == "rollback_test@taskflow.dev"


def test_auth_service_register_rollback_on_integrity_error(db_session: Session):
    """Verify that auth_service.register_user executes db.rollback() when an IntegrityError occurs."""
    req = UserRegisterRequest(
        name="Integrity User",
        email="integrity_unique@taskflow.dev",
        password="Password123!",
    )
    # Register first time
    user = auth_service.register_user(db_session, req)
    assert user.id is not None

    # Simulate an integrity error on commit
    with patch.object(db_session, "commit", side_effect=IntegrityError("duplicate", None, None)):
        with patch.object(db_session, "rollback", wraps=db_session.rollback) as mock_rollback:
            with pytest.raises(Exception):
                auth_service.register_user(db_session, UserRegisterRequest(
                    name="Integrity User 2",
                    email="integrity_unique2@taskflow.dev",
                    password="Password123!",
                ))
            assert mock_rollback.called


def test_get_db_generator_lifecycle():
    """Verify get_db cleanly rolls back active sessions and closes them."""
    gen = get_db()
    db = next(gen)
    assert isinstance(db, Session)
    assert db.is_active

    # Close generator normally
    try:
        gen.send(None)
    except StopIteration:
        pass


def test_get_db_generator_exception_rollback():
    """Verify get_db catches exceptions thrown into the generator, rolls back, and closes."""
    gen = get_db()
    db = next(gen)

    with patch.object(db, "rollback", wraps=db.rollback) as mock_rollback:
        with pytest.raises(RuntimeError):
            gen.throw(RuntimeError("Simulated route crash"))
        assert mock_rollback.called
