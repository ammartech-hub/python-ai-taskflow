"""Pydantic schemas for task lifecycle, filtering, and AI generation."""

from datetime import datetime
from typing import List, Optional
from pydantic import BaseModel, Field, ConfigDict
from app.models.task import TaskStatus


class TaskCreateRequest(BaseModel):
    """Schema for creating a new task."""
    title: str = Field(
        ...,
        min_length=1,
        max_length=200,
        description="Concise task title",
        examples=["Implement OAuth2 login flow"],
    )
    description: Optional[str] = Field(
        default=None,
        max_length=5000,
        description="Detailed task description",
        examples=["Add Google OAuth2 integration with secure callback verification."],
    )
    # Optional field that only admins may specify; regular users' input will be disregarded
    user_id: Optional[int] = Field(
        default=None,
        description="Target user ID (admin-only assignment; ignored for regular users)",
    )


class TaskUpdateRequest(BaseModel):
    """Schema for updating task details.

    Note: Regular users are strictly restricted to updating title and description.
    Supplying `status` as a non-admin will trigger an authorization rejection.
    """
    title: Optional[str] = Field(
        default=None,
        min_length=1,
        max_length=200,
        description="Updated task title",
    )
    description: Optional[str] = Field(
        default=None,
        max_length=5000,
        description="Updated task description",
    )
    status: Optional[TaskStatus] = Field(
        default=None,
        description="Target status (admin-only modification)",
    )


class TaskStatusUpdateRequest(BaseModel):
    """Schema for dedicated admin status update endpoint."""
    status: TaskStatus = Field(
        ...,
        description="New lifecycle status: 'Pending', 'In Progress', 'Testing', or 'Completed'",
        examples=[TaskStatus.IN_PROGRESS],
    )


class TaskResponse(BaseModel):
    """Safe serialization schema for task records."""
    model_config = ConfigDict(from_attributes=True)

    id: int = Field(..., description="Unique task identifier")
    user_id: int = Field(..., description="ID of the user who owns this task")
    title: str = Field(..., description="Task title")
    description: Optional[str] = Field(default=None, description="Task description")
    status: TaskStatus = Field(..., description="Current task lifecycle status")
    created_at: datetime = Field(..., description="Timestamp of task creation")
    updated_at: datetime = Field(..., description="Timestamp of last task update")


class TaskListResponse(BaseModel):
    """Paginated collection of task records."""
    items: List[TaskResponse] = Field(..., description="List of tasks on the current page")
    total: int = Field(..., description="Total count of matching tasks")
    page: int = Field(..., description="Current page number (1-indexed)")
    limit: int = Field(..., description="Number of items per page")
    total_pages: int = Field(..., description="Total available pages")


class GenerateDescriptionRequest(BaseModel):
    """Schema for requesting AI-generated task descriptions."""
    title: str = Field(
        ...,
        min_length=3,
        max_length=200,
        description="Task title to generate a professional description for",
        examples=["Prepare monthly sales report"],
    )


class GenerateDescriptionResponse(BaseModel):
    """Schema for AI task description generation output."""
    title: str = Field(..., description="Original validated task title")
    description: str = Field(..., description="AI-generated concise, professional task description")
