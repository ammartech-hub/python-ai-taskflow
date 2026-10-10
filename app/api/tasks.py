"""Task management API routes for CRUD operations, status management, and AI generation."""

import math
from typing import Optional
from fastapi import APIRouter, Depends, Query, HTTPException, status
from sqlalchemy.orm import Session

from app.database.connection import get_db
from app.models.user import User, UserRole
from app.models.task import TaskStatus
from app.schemas.task import (
    TaskCreateRequest,
    TaskUpdateRequest,
    TaskStatusUpdateRequest,
    TaskResponse,
    TaskListResponse,
    GenerateDescriptionRequest,
    GenerateDescriptionResponse,
)
from app.services.task_service import task_service
from app.auth.dependencies import get_current_user, get_current_admin
from app.ai.gemini_service import gemini_service, AIServiceException

router = APIRouter(prefix="/tasks", tags=["Tasks"])


@router.post(
    "/",
    response_model=TaskResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create a new task",
    description=(
        "Creates a new task. Regular users can create tasks only for themselves (client-supplied "
        "user_id is ignored). Administrators can designate a task owner."
    ),
)
def create_task(
    request: TaskCreateRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> TaskResponse:
    """Create task and assign ownership safely."""
    task = task_service.create_task(db, request, current_user)
    return TaskResponse.model_validate(task)


@router.get(
    "/",
    response_model=TaskListResponse,
    status_code=status.HTTP_200_OK,
    summary="List tasks",
    description=(
        "Retrieves tasks with pagination and optional status filter. Regular users see only their own tasks; "
        "administrators can view all tasks across the system."
    ),
)
def list_tasks(
    status_filter: Optional[TaskStatus] = Query(None, alias="status", description="Filter by task status"),
    page: int = Query(1, ge=1, description="Page number (1-indexed)"),
    limit: int = Query(10, ge=1, le=100, description="Items per page"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> TaskListResponse:
    """List tasks scoped to caller authorization."""
    tasks, total = task_service.list_tasks(
        db=db,
        current_user=current_user,
        status_filter=status_filter,
        page=page,
        limit=limit,
    )
    total_pages = math.ceil(total / limit) if total > 0 else 1

    return TaskListResponse(
        items=[TaskResponse.model_validate(t) for t in tasks],
        total=total,
        page=page,
        limit=limit,
        total_pages=total_pages,
    )


@router.post(
    "/generate-description",
    response_model=GenerateDescriptionResponse,
    status_code=status.HTTP_200_OK,
    summary="Generate task description using Gemini AI",
    description=(
        "Generates a professional, concise task description from a given title using Google Gemini AI. "
        "Requires authenticated user. Returns clear error if AI service is not configured or fails."
    ),
)
def generate_task_description(
    request: GenerateDescriptionRequest,
    current_user: User = Depends(get_current_user),
) -> GenerateDescriptionResponse:
    """Invoke Gemini AI to generate task description."""
    try:
        description = gemini_service.generate_task_description(request.title)
        return GenerateDescriptionResponse(
            title=request.title.strip(),
            description=description,
        )
    except AIServiceException as exc:
        raise HTTPException(status_code=exc.status_code, detail=exc.message)
    except Exception:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Unexpected failure communicating with AI service provider.",
        )


@router.get(
    "/{task_id}",
    response_model=TaskResponse,
    status_code=status.HTTP_200_OK,
    summary="Get task by ID",
    description=(
        "Retrieves task details. Accessible only if requester owns the task or is an administrator. "
        "Returns HTTP 404 if the task does not exist or is not accessible to the requester."
    ),
)
def get_task(
    task_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> TaskResponse:
    """Retrieve single task with ownership isolation."""
    task = task_service.get_task(db, task_id, current_user)
    return TaskResponse.model_validate(task)


@router.put(
    "/{task_id}",
    response_model=TaskResponse,
    status_code=status.HTTP_200_OK,
    summary="Update task details",
    description=(
        "Updates title and description. Regular users cannot modify task status; attempting to do so "
        "returns HTTP 403 Forbidden. Administrators can modify title, description, and status."
    ),
)
def update_task(
    task_id: int,
    request: TaskUpdateRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> TaskResponse:
    """Update task attributes with status change permission enforcement."""
    task = task_service.update_task(db, task_id, request, current_user)
    return TaskResponse.model_validate(task)


@router.patch(
    "/{task_id}/status",
    response_model=TaskResponse,
    status_code=status.HTTP_200_OK,
    summary="Update task lifecycle status (Admin only)",
    description=(
        "Dedicated administrator endpoint to advance task status ('Pending', 'In Progress', 'Testing', 'Completed'). "
        "Non-admin users receive HTTP 403 Forbidden."
    ),
)
def update_task_status(
    task_id: int,
    request: TaskStatusUpdateRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_admin),
) -> TaskResponse:
    """Admin-only status transition."""
    task = task_service.update_task_status(db, task_id, request.status, current_user)
    return TaskResponse.model_validate(task)


@router.delete(
    "/{task_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete a task",
    description="Deletes a task if owned by the requester or if requester is an administrator.",
)
def delete_task(
    task_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> None:
    """Delete task by ID."""
    task_service.delete_task(db, task_id, current_user)
