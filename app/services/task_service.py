"""Business logic service for task CRUD operations, filtering, and authorization."""

from typing import List, Optional, Tuple
from fastapi import HTTPException, status
from sqlalchemy.orm import Session
from sqlalchemy import func

from app.models.user import User, UserRole
from app.models.task import Task, TaskStatus
from app.schemas.task import TaskCreateRequest, TaskUpdateRequest


class TaskService:
    """Service encapsulating task operations and fine-grained authorization enforcement."""

    @staticmethod
    def create_task(db: Session, task_in: TaskCreateRequest, current_user: User) -> Task:
        """Create a new task.

        Enforces strict ownership: regular users are never permitted to assign
        tasks to another user ID. Admins may optionally designate a target owner.
        """
        assigned_user_id = current_user.id

        if current_user.role == UserRole.ADMIN and task_in.user_id is not None:
            # Verify target user exists
            target_user = db.query(User).filter(User.id == task_in.user_id).first()
            if not target_user:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail=f"Target user with id {task_in.user_id} does not exist.",
                )
            assigned_user_id = target_user.id

        new_task = Task(
            user_id=assigned_user_id,
            title=task_in.title.strip(),
            description=task_in.description.strip() if task_in.description else None,
            status=TaskStatus.PENDING,
        )

        try:
            db.add(new_task)
            db.commit()
            db.refresh(new_task)
            return new_task
        except Exception:
            db.rollback()
            raise

    @staticmethod
    def get_task(db: Session, task_id: int, current_user: User) -> Task:
        """Retrieve a specific task by ID.

        Enforces security isolation: returns HTTP 404 if the task does not exist
        OR if the current user is not an administrator and does not own the task.
        """
        task = db.query(Task).filter(Task.id == task_id).first()
        if not task:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Task with id {task_id} not found.",
            )

        # Non-admins can only access their own tasks; hide existence from other users
        if current_user.role != UserRole.ADMIN and task.user_id != current_user.id:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Task with id {task_id} not found.",
            )

        return task

    @staticmethod
    def list_tasks(
        db: Session,
        current_user: User,
        status_filter: Optional[TaskStatus] = None,
        page: int = 1,
        limit: int = 10,
    ) -> Tuple[List[Task], int]:
        """List tasks with role scoping, status filtering, and pagination.

        Regular users receive only their own tasks; admins can view all tasks.
        """
        query = db.query(Task)

        # Role-based visibility
        if current_user.role != UserRole.ADMIN:
            query = query.filter(Task.user_id == current_user.id)

        # Status filter
        if status_filter is not None:
            query = query.filter(Task.status == status_filter)

        total = query.count()
        offset = max(0, (page - 1) * limit)
        tasks = query.order_by(Task.created_at.desc()).offset(offset).limit(limit).all()

        return tasks, total

    @staticmethod
    def update_task(
        db: Session,
        task_id: int,
        task_in: TaskUpdateRequest,
        current_user: User,
    ) -> Task:
        """Update task details.

        Regular users can edit title and description of their own tasks.
        Attempting to modify `status` as a non-admin triggers HTTP 403 Forbidden.
        """
        task = TaskService.get_task(db, task_id, current_user)

        # Prevent regular users from modifying task status
        if task_in.status is not None:
            if current_user.role != UserRole.ADMIN:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="Regular users are not permitted to modify task status. Status updates are restricted to administrators.",
                )
            task.status = task_in.status

        if task_in.title is not None:
            task.title = task_in.title.strip()

        if task_in.description is not None:
            task.description = task_in.description.strip()

        try:
            db.commit()
            db.refresh(task)
            return task
        except Exception:
            db.rollback()
            raise

    @staticmethod
    def update_task_status(
        db: Session,
        task_id: int,
        new_status: TaskStatus,
        current_user: User,
    ) -> Task:
        """Admin-only update of task lifecycle status."""
        if current_user.role != UserRole.ADMIN:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Administrative privileges required to modify task status.",
            )

        task = db.query(Task).filter(Task.id == task_id).first()
        if not task:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Task with id {task_id} not found.",
            )

        task.status = new_status
        try:
            db.commit()
            db.refresh(task)
            return task
        except Exception:
            db.rollback()
            raise

    @staticmethod
    def delete_task(db: Session, task_id: int, current_user: User) -> None:
        """Delete task by ID if owned by requester or requester is admin."""
        task = TaskService.get_task(db, task_id, current_user)
        try:
            db.delete(task)
            db.commit()
        except Exception:
            db.rollback()
            raise


task_service = TaskService()
