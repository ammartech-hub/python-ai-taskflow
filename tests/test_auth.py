"""Unit and integration tests for authentication and authorization workflows."""

from datetime import timedelta
import pytest
from fastapi.testclient import TestClient
from app.auth.jwt import create_access_token


def test_register_user_success(client: TestClient):
    """Verify that a new user can register successfully with HTTP 201."""
    response = client.post(
        "/api/auth/register",
        json={
            "name": "Alice Developer",
            "email": "alice@example.com",
            "password": "Password123!",
        },
    )
    assert response.status_code == 201
    data = response.json()
    assert data["name"] == "Alice Developer"
    assert data["email"] == "alice@example.com"
    assert data["role"] == "user"
    assert "password" not in data
    assert "id" in data


def test_register_duplicate_email_fails(client: TestClient):
    """Verify that registering with an existing email returns HTTP 409 Conflict."""
    payload = {
        "name": "Duplicate Tester",
        "email": "duplicate@example.com",
        "password": "Password123!",
    }
    # First registration
    res1 = client.post("/api/auth/register", json=payload)
    assert res1.status_code == 201

    # Second registration with identical email
    res2 = client.post("/api/auth/register", json=payload)
    assert res2.status_code == 409
    assert "already exists" in res2.json()["detail"].lower()


def test_public_registration_cannot_grant_admin_role(client: TestClient):
    """Verify that public registration cannot elevate user role to admin."""
    response = client.post(
        "/api/auth/register",
        json={
            "name": "Attacker Admin Attempt",
            "email": "hacker@example.com",
            "password": "Password123!",
            "role": "admin",  # Client attempts to smuggle admin role
        },
    )
    assert response.status_code == 201
    data = response.json()
    assert data["role"] == "user"  # Must strictly remain 'user'


def test_register_validation_short_password(client: TestClient):
    """Verify that passwords shorter than 8 characters fail validation with HTTP 422."""
    response = client.post(
        "/api/auth/register",
        json={
            "name": "Short Pwd",
            "email": "short@example.com",
            "password": "123",
        },
    )
    assert response.status_code == 422


def test_login_success(client: TestClient, regular_user):
    """Verify that valid credentials return a JWT access token and HTTP 200."""
    response = client.post(
        "/api/auth/login",
        json={
            "email": "jane.user@example.com",
            "password": "Password123!",
        },
    )
    assert response.status_code == 200
    data = response.json()
    assert "access_token" in data
    assert data["token_type"] == "bearer"
    assert data["user"]["email"] == "jane.user@example.com"
    assert "password" not in data["user"]


def test_login_invalid_password(client: TestClient, regular_user):
    """Verify that invalid password returns HTTP 401 Unauthorized."""
    response = client.post(
        "/api/auth/login",
        json={
            "email": "jane.user@example.com",
            "password": "WrongPassword999!",
        },
    )
    assert response.status_code == 401
    assert "Invalid email or password" in response.json()["detail"]


def test_login_nonexistent_user(client: TestClient):
    """Verify that nonexistent email returns HTTP 401 Unauthorized."""
    response = client.post(
        "/api/auth/login",
        json={
            "email": "nonexistent@example.com",
            "password": "Password123!",
        },
    )
    assert response.status_code == 401


def test_get_current_user_profile(client: TestClient, user_headers):
    """Verify that GET /api/auth/me returns the caller's safe profile."""
    response = client.get("/api/auth/me", headers=user_headers)
    assert response.status_code == 200
    data = response.json()
    assert data["email"] == "jane.user@example.com"
    assert data["role"] == "user"
    assert "password" not in data


def test_missing_jwt_returns_401(client: TestClient):
    """Verify that accessing protected endpoint without JWT returns HTTP 401."""
    response = client.get("/api/auth/me")
    assert response.status_code == 401
    assert "Authentication required" in response.json()["detail"]


def test_invalid_jwt_returns_401(client: TestClient):
    """Verify that providing a malformed or forged JWT returns HTTP 401."""
    response = client.get(
        "/api/auth/me",
        headers={"Authorization": "Bearer invalid.token.signature"},
    )
    assert response.status_code == 401


def test_expired_jwt_returns_401(client: TestClient, regular_user):
    """Verify that an expired JWT returns HTTP 401."""
    expired_token = create_access_token(
        {"sub": str(regular_user.id), "role": regular_user.role.value},
        expires_delta=timedelta(minutes=-10),  # expired 10 minutes ago
    )
    response = client.get(
        "/api/auth/me",
        headers={"Authorization": f"Bearer {expired_token}"},
    )
    assert response.status_code == 401
    assert "expired" in response.json()["detail"].lower()
