"""Pytest configuration and isolated fixtures for automated testing."""

from typing import Generator
import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session
from sqlalchemy.pool import StaticPool
from fastapi.testclient import TestClient

from app.main import app
from app.database.base import Base
from app.database.connection import get_db
from app.models.user import User, UserRole
from app.models.task import Task, TaskStatus
from app.auth.password import hash_password
from app.auth.jwt import create_access_token

# Configure isolated in-memory SQLite database for testing
TEST_DATABASE_URL = "sqlite:///:memory:"

test_engine = create_engine(
    TEST_DATABASE_URL,
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)

TestingSessionLocal = sessionmaker(
    autocommit=False,
    autoflush=False,
    bind=test_engine,
)


@pytest.fixture(scope="function")
def db_session() -> Generator[Session, None, None]:
    """Provide a fresh, isolated database session with tables recreated per test."""
    Base.metadata.create_all(bind=test_engine)
    session = TestingSessionLocal()
    try:
        yield session
    finally:
        session.close()
        Base.metadata.drop_all(bind=test_engine)


@pytest.fixture(scope="function")
def client(db_session: Session) -> Generator[TestClient, None, None]:
    """FastAPI TestClient with overridden get_db dependency pointing to the test DB."""
    def override_get_db():
        try:
            yield db_session
        finally:
            pass

    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()


@pytest.fixture
def regular_user(db_session: Session) -> User:
    """Fixture creating a standard user with the USER role."""
    user = User(
        name="Jane Regular",
        email="jane.user@example.com",
        password=hash_password("Password123!"),
        role=UserRole.USER,
    )
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)
    return user


@pytest.fixture
def other_user(db_session: Session) -> User:
    """Fixture creating a second standard user for cross-user permission checks."""
    user = User(
        name="Bob Other",
        email="bob.other@example.com",
        password=hash_password("Password123!"),
        role=UserRole.USER,
    )
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)
    return user


@pytest.fixture
def admin_user(db_session: Session) -> User:
    """Fixture creating an administrator user with the ADMIN role."""
    user = User(
        name="Admin User",
        email="admin.boss@example.com",
        password=hash_password("AdminPass123!"),
        role=UserRole.ADMIN,
    )
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)
    return user


@pytest.fixture
def user_token(regular_user: User) -> str:
    """Valid JWT access token for regular_user."""
    return create_access_token({"sub": str(regular_user.id), "role": regular_user.role.value})


@pytest.fixture
def user_headers(user_token: str) -> dict:
    """Authorization headers for regular_user."""
    return {"Authorization": f"Bearer {user_token}"}


@pytest.fixture
def other_token(other_user: User) -> str:
    """Valid JWT access token for other_user."""
    return create_access_token({"sub": str(other_user.id), "role": other_user.role.value})


@pytest.fixture
def other_headers(other_token: str) -> dict:
    """Authorization headers for other_user."""
    return {"Authorization": f"Bearer {other_token}"}


@pytest.fixture
def admin_token(admin_user: User) -> str:
    """Valid JWT access token for admin_user."""
    return create_access_token({"sub": str(admin_user.id), "role": admin_user.role.value})


@pytest.fixture
def admin_headers(admin_token: str) -> dict:
    """Authorization headers for admin_user."""
    return {"Authorization": f"Bearer {admin_token}"}


@pytest.fixture
def regular_task(db_session: Session, regular_user: User) -> Task:
    """Sample task owned by regular_user."""
    task = Task(
        user_id=regular_user.id,
        title="Regular User Task",
        description="Initial description for regular task.",
        status=TaskStatus.PENDING,
    )
    db_session.add(task)
    db_session.commit()
    db_session.refresh(task)
    return task
