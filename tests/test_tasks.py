"""Unit and integration tests for task lifecycle, ownership, and authorization."""

import pytest
from fastapi.testclient import TestClient
from app.models.task import TaskStatus


def test_user_can_create_task(client: TestClient, user_headers, regular_user):
    """Verify that an authenticated user can create a task owned by themselves."""
    response = client.post(
        "/api/tasks/",
        headers=user_headers,
        json={
            "title": "Build unit test suite",
            "description": "Write pytest fixtures and assertion tests.",
        },
    )
    assert response.status_code == 201
    data = response.json()
    assert data["title"] == "Build unit test suite"
    assert data["description"] == "Write pytest fixtures and assertion tests."
    assert data["status"] == "Pending"
    assert data["user_id"] == regular_user.id


def test_regular_user_cannot_spoof_task_ownership(
    client: TestClient, user_headers, regular_user, other_user
):
    """Verify that regular user cannot specify a different user_id."""
    response = client.post(
        "/api/tasks/",
        headers=user_headers,
        json={
            "title": "Attempt ownership takeover",
            "description": "Spoofed user_id attempt",
            "user_id": other_user.id,  # Attempting to assign to someone else
        },
    )
    assert response.status_code == 201
    data = response.json()
    # Must belong to the caller (regular_user), not other_user
    assert data["user_id"] == regular_user.id


def test_admin_can_assign_task_to_another_user(
    client: TestClient, admin_headers, regular_user
):
    """Verify that administrators can create tasks assigned to a specific user."""
    response = client.post(
        "/api/tasks/",
        headers=admin_headers,
        json={
            "title": "Admin Assigned Task",
            "description": "Task created by admin for regular user.",
            "user_id": regular_user.id,
        },
    )
    assert response.status_code == 201
    data = response.json()
    assert data["user_id"] == regular_user.id


def test_user_can_list_only_their_own_tasks(
    client: TestClient, user_headers, other_headers, regular_user, other_user
):
    """Verify that regular users see only their own tasks, never other users' tasks."""
    # User 1 creates a task
    client.post(
        "/api/tasks/",
        headers=user_headers,
        json={"title": "Task of User 1"},
    )
    # User 2 creates two tasks
    client.post(
        "/api/tasks/",
        headers=other_headers,
        json={"title": "Task of User 2 - Alpha"},
    )
    client.post(
        "/api/tasks/",
        headers=other_headers,
        json={"title": "Task of User 2 - Beta"},
    )

    # User 1 lists tasks
    res1 = client.get("/api/tasks/", headers=user_headers)
    assert res1.status_code == 200
    data1 = res1.json()
    assert data1["total"] == 1
    assert data1["items"][0]["title"] == "Task of User 1"
    assert data1["items"][0]["user_id"] == regular_user.id

    # User 2 lists tasks
    res2 = client.get("/api/tasks/", headers=other_headers)
    assert res2.status_code == 200
    data2 = res2.json()
    assert data2["total"] == 2
    for item in data2["items"]:
        assert item["user_id"] == other_user.id


def test_admin_can_view_tasks_across_all_users(
    client: TestClient, admin_headers, user_headers, other_headers
):
    """Verify that administrators can list tasks created by all users."""
    client.post("/api/tasks/", headers=user_headers, json={"title": "User 1 Task"})
    client.post("/api/tasks/", headers=other_headers, json={"title": "User 2 Task"})

    response = client.get("/api/tasks/", headers=admin_headers)
    assert response.status_code == 200
    data = response.json()
    assert data["total"] >= 2
    titles = [t["title"] for t in data["items"]]
    assert "User 1 Task" in titles
    assert "User 2 Task" in titles


def test_user_can_view_own_task(client: TestClient, user_headers, regular_task):
    """Verify that a user can view their own task."""
    response = client.get(f"/api/tasks/{regular_task.id}", headers=user_headers)
    assert response.status_code == 200
    assert response.json()["id"] == regular_task.id
    assert response.json()["title"] == regular_task.title


def test_user_cannot_view_another_users_task(client: TestClient, other_headers, regular_task):
    """Verify that a user cannot view another user's task (returns 404 for isolation)."""
    response = client.get(f"/api/tasks/{regular_task.id}", headers=other_headers)
    assert response.status_code == 404
    assert "not found" in response.json()["detail"].lower()


def test_admin_can_view_any_users_task(client: TestClient, admin_headers, regular_task):
    """Verify that an administrator can view any user's task."""
    response = client.get(f"/api/tasks/{regular_task.id}", headers=admin_headers)
    assert response.status_code == 200
    assert response.json()["id"] == regular_task.id


def test_user_can_edit_own_task_title_and_description(
    client: TestClient, user_headers, regular_task
):
    """Verify that a user can update title and description of their own task."""
    response = client.put(
        f"/api/tasks/{regular_task.id}",
        headers=user_headers,
        json={
            "title": "Updated Task Title",
            "description": "Updated Task Description",
        },
    )
    assert response.status_code == 200
    data = response.json()
    assert data["title"] == "Updated Task Title"
    assert data["description"] == "Updated Task Description"


def test_user_cannot_edit_another_users_task(
    client: TestClient, other_headers, regular_task
):
    """Verify that attempting to edit another user's task returns HTTP 404."""
    response = client.put(
        f"/api/tasks/{regular_task.id}",
        headers=other_headers,
        json={"title": "Hacked Title"},
    )
    assert response.status_code == 404


def test_user_cannot_update_task_status_via_put(
    client: TestClient, user_headers, regular_task
):
    """Verify that regular user cannot modify task status via PUT endpoint."""
    response = client.put(
        f"/api/tasks/{regular_task.id}",
        headers=user_headers,
        json={
            "title": "Updated Title",
            "status": "Completed",  # Forbidden for regular user
        },
    )
    assert response.status_code == 403
    assert "restricted to administrators" in response.json()["detail"].lower()


def test_user_cannot_update_task_status_via_patch(
    client: TestClient, user_headers, regular_task
):
    """Verify that regular user calling PATCH /api/tasks/{id}/status receives HTTP 403."""
    response = client.patch(
        f"/api/tasks/{regular_task.id}/status",
        headers=user_headers,
        json={"status": "Completed"},
    )
    assert response.status_code == 403
    assert "administrative privileges required" in response.json()["detail"].lower()


def test_admin_can_update_task_status_via_patch(
    client: TestClient, admin_headers, regular_task
):
    """Verify that an administrator can update task status via PATCH."""
    response = client.patch(
        f"/api/tasks/{regular_task.id}/status",
        headers=admin_headers,
        json={"status": "In Progress"},
    )
    assert response.status_code == 200
    assert response.json()["status"] == "In Progress"


def test_invalid_task_status_returns_422(
    client: TestClient, admin_headers, regular_task
):
    """Verify that supplying an unrecognized status returns HTTP 422."""
    response = client.patch(
        f"/api/tasks/{regular_task.id}/status",
        headers=admin_headers,
        json={"status": "ArbitraryNonExistentStatus"},
    )
    assert response.status_code == 422


def test_nonexistent_task_returns_404(client: TestClient, user_headers):
    """Verify that requesting a nonexistent task ID returns HTTP 404."""
    response = client.get("/api/tasks/99999", headers=user_headers)
    assert response.status_code == 404


def test_filter_tasks_by_status(client: TestClient, user_headers):
    """Verify filtering tasks by lifecycle status."""
    client.post("/api/tasks/", headers=user_headers, json={"title": "Pending Task 1"})
    client.post("/api/tasks/", headers=user_headers, json={"title": "Pending Task 2"})

    response = client.get("/api/tasks/?status=Pending", headers=user_headers)
    assert response.status_code == 200
    data = response.json()
    for task in data["items"]:
        assert task["status"] == "Pending"


def test_user_can_delete_own_task(client: TestClient, user_headers, regular_task):
    """Verify that a user can delete their own task (HTTP 204)."""
    response = client.delete(f"/api/tasks/{regular_task.id}", headers=user_headers)
    assert response.status_code == 204

    # Verify task is gone
    get_res = client.get(f"/api/tasks/{regular_task.id}", headers=user_headers)
    assert get_res.status_code == 404


def test_user_cannot_delete_another_users_task(
    client: TestClient, other_headers, regular_task
):
    """Verify that a user cannot delete another user's task."""
    response = client.delete(f"/api/tasks/{regular_task.id}", headers=other_headers)
    assert response.status_code == 404
