"""Unit and integration tests for AI-powered task description generation."""

from unittest.mock import patch
import pytest
from fastapi.testclient import TestClient
from app.ai.gemini_service import (
    GeminiService,
    gemini_service,
    AIServiceNotConfiguredError,
    AIRateLimitError,
    AIServiceUnavailableError,
    AIProviderError,
)


def test_generate_description_requires_auth(client: TestClient):
    """Verify that unauthenticated callers cannot access the AI generation endpoint."""
    response = client.post(
        "/api/tasks/generate-description",
        json={"title": "Prepare monthly sales report"},
    )
    assert response.status_code == 401


def test_generate_description_validation_short_title(client: TestClient, user_headers):
    """Verify that titles shorter than 3 characters fail validation with HTTP 422."""
    response = client.post(
        "/api/tasks/generate-description",
        headers=user_headers,
        json={"title": "Hi"},  # Less than min_length=3
    )
    assert response.status_code == 422


def test_generate_description_success_mocked(client: TestClient, user_headers):
    """Verify that a successful AI generation returns HTTP 200 and formatted response."""
    mock_description = (
        "Compile monthly sales data across all regional divisions. "
        "Calculate revenue growth, identify top-performing products, "
        "and summarize key findings into an executive slide deck."
    )

    with patch.object(gemini_service, "generate_task_description", return_value=mock_description):
        response = client.post(
            "/api/tasks/generate-description",
            headers=user_headers,
            json={"title": "Prepare monthly sales report"},
        )
        assert response.status_code == 200
        data = response.json()
        assert data["title"] == "Prepare monthly sales report"
        assert data["description"] == mock_description


def test_generate_description_unconfigured_api_key(client: TestClient, user_headers):
    """Verify that a missing Gemini API key returns HTTP 503 with a clear configuration message."""
    with patch.object(
        gemini_service,
        "generate_task_description",
        side_effect=AIServiceNotConfiguredError("AI service is not configured. Please set GEMINI_API_KEY in the environment."),
    ):
        response = client.post(
            "/api/tasks/generate-description",
            headers=user_headers,
            json={"title": "Prepare monthly sales report"},
        )
        assert response.status_code == 503
        data = response.json()
        assert "not configured" in data["detail"].lower()
        assert "GEMINI_API_KEY" in data["detail"]


def test_generate_description_rate_limit(client: TestClient, user_headers):
    """Verify that provider rate limits translate to HTTP 429."""
    with patch.object(
        gemini_service,
        "generate_task_description",
        side_effect=AIRateLimitError("AI provider rate limit reached. Please retry after a brief pause."),
    ):
        response = client.post(
            "/api/tasks/generate-description",
            headers=user_headers,
            json={"title": "Prepare monthly sales report"},
        )
        assert response.status_code == 429
        assert "rate limit" in response.json()["detail"].lower()


def test_generate_description_provider_unavailable(client: TestClient, user_headers):
    """Verify that provider timeout / 503 translates to HTTP 503."""
    with patch.object(
        gemini_service,
        "generate_task_description",
        side_effect=AIServiceUnavailableError("AI provider is temporarily unavailable. Please retry later."),
    ):
        response = client.post(
            "/api/tasks/generate-description",
            headers=user_headers,
            json={"title": "Prepare monthly sales report"},
        )
        assert response.status_code == 503
        assert "unavailable" in response.json()["detail"].lower()


def test_generate_description_provider_error(client: TestClient, user_headers):
    """Verify that general provider failures translate to HTTP 502."""
    with patch.object(
        gemini_service,
        "generate_task_description",
        side_effect=AIProviderError("Failed to generate description from AI provider."),
    ):
        response = client.post(
            "/api/tasks/generate-description",
            headers=user_headers,
            json={"title": "Prepare monthly sales report"},
        )
        assert response.status_code == 502
        assert "failed" in response.json()["detail"].lower()
