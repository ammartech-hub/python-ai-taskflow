"""Database seed script for local development and integration testing.

Populates initial administrator, regular users, and sample tasks.
Idempotent: safe to run repeatedly without creating duplicate records.
"""

import os
import sys

# Ensure project root is available on sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

# Ensure UTF-8 output encoding on Windows consoles
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

from app.database.connection import SessionLocal, engine
from app.database.base import Base
from app.models.user import User, UserRole
from app.models.task import Task, TaskStatus
from app.auth.password import hash_password
from app.config import settings


def seed_database() -> None:
    """Populate the database with initial users and tasks if not already present."""
    # Ensure tables exist before inserting records
    Base.metadata.create_all(bind=engine)

    db = SessionLocal()

    print("=" * 70)
    print("[*] AI-Powered Task Management System - Database Seeder")
    print("=" * 70)

    try:
        # 1. Define Seed Users
        seed_users = [
            {
                "name": "System Administrator",
                "email": os.getenv("SEED_ADMIN_EMAIL", settings.SEED_ADMIN_EMAIL).lower().strip(),
                "password": os.getenv("SEED_ADMIN_PASSWORD", settings.SEED_ADMIN_PASSWORD),
                "role": UserRole.ADMIN,
            },
            {
                "name": "Jane Developer",
                "email": os.getenv("SEED_USER_EMAIL", settings.SEED_USER_EMAIL).lower().strip(),
                "password": os.getenv("SEED_USER_PASSWORD", settings.SEED_USER_PASSWORD),
                "role": UserRole.USER,
            },
            {
                "name": "Alex Designer",
                "email": os.getenv("SEED_OTHER_EMAIL", "alex@taskflow.dev").lower().strip(),
                "password": os.getenv("SEED_OTHER_PASSWORD", "AlexPass123!"),
                "role": UserRole.USER,
            },
        ]

        created_users = {}

        for user_data in seed_users:
            existing = db.query(User).filter(User.email == user_data["email"]).first()
            if existing:
                print(f"[INFO] User already exists: {user_data['email']} (Role: {existing.role.value})")
                created_users[user_data["email"]] = existing
            else:
                user = User(
                    name=user_data["name"],
                    email=user_data["email"],
                    password=hash_password(user_data["password"]),
                    role=user_data["role"],
                )
                db.add(user)
                db.commit()
                db.refresh(user)
                created_users[user_data["email"]] = user
                print(f"[OK] Created User: {user.name} <{user.email}> [{user.role.value.upper()}] (ID: {user.id})")

        # 2. Define Sample Tasks
        jane = created_users.get("user@taskflow.dev")
        alex = created_users.get("alex@taskflow.dev")
        admin = created_users.get("admin@taskflow.dev")

        seed_tasks = [
            {
                "user": jane,
                "title": "Set up CI/CD pipeline",
                "description": "Configure automated GitHub Actions workflow for linting, pytest suite, and docker image build.",
                "status": TaskStatus.PENDING,
            },
            {
                "user": jane,
                "title": "Implement OAuth2 login flow",
                "description": "Integrate Google OAuth2 authentication provider and verify JWT token exchange flow.",
                "status": TaskStatus.IN_PROGRESS,
            },
            {
                "user": jane,
                "title": "API documentation polish",
                "description": "Ensure all endpoints have comprehensive OpenAPI metadata, tags, and request examples.",
                "status": TaskStatus.COMPLETED,
            },
            {
                "user": alex,
                "title": "Design task dashboard wireframes",
                "description": "Create high-fidelity Figma components with responsive mobile breakpoints and dark mode palette.",
                "status": TaskStatus.TESTING,
            },
            {
                "user": admin,
                "title": "Quarterly security audit",
                "description": "Review RBAC permission boundaries and audit database connection pool configurations.",
                "status": TaskStatus.IN_PROGRESS,
            },
        ]

        tasks_created_count = 0
        for task_def in seed_tasks:
            owner = task_def["user"]
            if not owner:
                continue

            existing_task = (
                db.query(Task)
                .filter(Task.user_id == owner.id, Task.title == task_def["title"])
                .first()
            )
            if existing_task:
                print(f"[INFO] Task already exists: '{task_def['title']}' for user {owner.email}")
            else:
                new_task = Task(
                    user_id=owner.id,
                    title=task_def["title"],
                    description=task_def["description"],
                    status=task_def["status"],
                )
                db.add(new_task)
                db.commit()
                tasks_created_count += 1
                print(f"[OK] Created Task: '{new_task.title}' -> Owner: {owner.email} (Status: {new_task.status.value})")

        print("=" * 70)
        print("[*] Seeding completed successfully!")
        print("\n[*] Local Development Credentials:")
        print(f"  * Administrator: {settings.SEED_ADMIN_EMAIL} / {settings.SEED_ADMIN_PASSWORD}")
        print(f"  * Regular User:  {settings.SEED_USER_EMAIL} / {settings.SEED_USER_PASSWORD}")
        print("  * Second User:   alex@taskflow.dev / AlexPass123!")
        print("=" * 70)

    except Exception as exc:
        db.rollback()
        print(f"[ERROR] Error during database seeding: {exc}")
        raise
    finally:
        db.close()


if __name__ == "__main__":
    seed_database()
