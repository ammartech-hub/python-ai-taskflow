"""Administrator management API routes for user oversight and platform metrics."""

from typing import Dict, List
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from sqlalchemy import func

from app.database.connection import get_db
from app.models.user import User, UserRole
from app.models.task import Task, TaskStatus
from app.schemas.user import UserResponse, UserRoleUpdateRequest
from app.auth.dependencies import get_current_admin

router = APIRouter(prefix="/admin", tags=["Admin"])


@router.get(
    "/users",
    response_model=List[UserResponse],
    status_code=status.HTTP_200_OK,
    summary="List all registered users (Admin only)",
    description="Retrieves a list of all registered accounts. Restricted to administrators.",
)
def list_all_users(
    db: Session = Depends(get_db),
    admin_user: User = Depends(get_current_admin),
) -> List[UserResponse]:
    """List all user accounts."""
    users = db.query(User).order_by(User.id.asc()).all()
    return [UserResponse.model_validate(u) for u in users]


@router.patch(
    "/users/{user_id}/role",
    response_model=UserResponse,
    status_code=status.HTTP_200_OK,
    summary="Update user role (Admin only)",
    description="Allows administrators to promote a user to admin or reassign to user role.",
)
def update_user_role(
    user_id: int,
    request: UserRoleUpdateRequest,
    db: Session = Depends(get_db),
    admin_user: User = Depends(get_current_admin),
) -> UserResponse:
    """Modify user role."""
    target_user = db.query(User).filter(User.id == user_id).first()
    if not target_user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"User with id {user_id} not found.",
        )

    target_user.role = request.role
    db.commit()
    db.refresh(target_user)
    return UserResponse.model_validate(target_user)


@router.get(
    "/stats",
    status_code=status.HTTP_200_OK,
    summary="Retrieve system overview statistics (Admin only)",
    description="Returns aggregate counts of users, total tasks, and distribution by lifecycle status.",
)
def get_system_stats(
    db: Session = Depends(get_db),
    admin_user: User = Depends(get_current_admin),
) -> Dict:
    """Aggregate system analytics for administrative dashboard."""
    total_users = db.query(User).count()
    total_tasks = db.query(Task).count()

    status_counts = {}
    for st in TaskStatus:
        status_counts[st.value] = db.query(Task).filter(Task.status == st).count()

    return {
        "total_users": total_users,
        "total_tasks": total_tasks,
        "tasks_by_status": status_counts,
    }
