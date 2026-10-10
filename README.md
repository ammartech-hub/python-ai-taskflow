# AI-Powered Task Management System

A production-grade, secure, and modular REST API backend built with **Python 3.12+**, **FastAPI**, **PostgreSQL**, **SQLAlchemy ORM**, **Alembic**, and **Google Gemini AI**.

Designed for enterprise-ready reliability, this system features role-based access control (RBAC), JWT authentication, strict object-level authorization, database migrations, automated testing with pytest, and AI-assisted task workflows.

---

## Table of Contents

1. [Project Overview and Objectives](#1-project-overview-and-objectives)
2. [Key Features](#2-key-features)
3. [Technology Stack](#3-technology-stack)
4. [Python Version Compatibility](#4-python-version-compatibility)
5. [Project Architecture and Folder Structure](#5-project-architecture-and-folder-structure)
6. [Prerequisites](#6-prerequisites)
7. [Virtual Environment Setup (Windows & macOS/Linux)](#7-virtual-environment-setup-windows--macoslinux)
8. [Dependency Installation](#8-dependency-installation)
9. [PostgreSQL Database Setup & Configuration](#9-postgresql-database-setup--configuration)
10. [Environment Variables Configuration](#10-environment-variables-configuration)
11. [Google Gemini API Key Setup](#11-google-gemini-api-key-setup)
12. [Alembic Database Migrations](#12-alembic-database-migrations)
13. [Database Seeding](#13-database-seeding)
14. [Running the Application](#14-running-the-application)
15. [Interactive Swagger & OpenAPI Documentation](#15-interactive-swagger--openapi-documentation)
16. [Complete API Endpoint Reference](#16-complete-api-endpoint-reference)
17. [Local Development Test Credentials](#17-local-development-test-credentials)
18. [Importing and Running the Postman Collection](#18-importing-and-running-the-postman-collection)
19. [Running Automated Tests with Pytest](#19-running-automated-tests-with-pytest)
20. [Implemented AI Feature & Failure Handling](#20-implemented-ai-feature--failure-handling)
21. [Security Architecture & Assumptions](#21-security-architecture--assumptions)
22. [Production Deployment Guidelines](#22-production-deployment-guidelines)

---

## 1. Project Overview and Objectives

The **AI-Powered Task Management System** is built to solve core workflow challenges in modern collaborative environments. It guarantees that:
- **Task Ownership & Isolation**: Regular users can only create, view, and modify tasks they own. Non-existent and unauthorized task accesses consistently return `404 Not Found` to prevent resource enumeration attacks.
- **Role-Based Workflow Governance**: Only administrators have authorization to transition task lifecycle states (`Pending` -> `In Progress` -> `Testing` -> `Completed`). Regular users attempting status tampering are rejected with `403 Forbidden`.
- **Intelligent Assistance**: Integrates Google Gemini Generative AI to generate structured, professional task descriptions directly from titles without blocking system startup when keys are unconfigured.

---

## 2. Key Features

- **JWT Authentication**: Industry-standard Bearer token authentication utilizing `HS256` HMAC signing, configurable expiry, and safe payloads.
- **Bcrypt Password Security**: Native salted hashing with 12 rounds of bcrypt work factor; plain passwords are never stored or returned.
- **Fine-Grained RBAC**: Dedicated permission dependencies enforcing clear separation between `user` and `admin` roles.
- **Database Migrations via Alembic**: Full declarative schema version control, automated tables creation, indexes, and foreign key constraints with cascade rules.
- **Google Gemini AI Integration**: Automated task description synthesis with comprehensive error translation (handling rate limits, timeouts, model unavailability, and unconfigured states gracefully).
- **Automated Pytest Suite**: 100% test isolation using in-memory databases and mocked AI responses, ensuring complete repeatability without external API dependencies.
- **Importable Postman Collection v2.1**: Pre-configured test scripts that auto-capture JWT tokens and task IDs.

---

## 3. Technology Stack

| Layer | Component | Version / Library |
| :--- | :--- | :--- |
| **Language** | Python | `3.10+` / `3.11+` / `3.12+` (Validated on 3.11.9 & 3.12) |
| **Framework** | FastAPI | `0.110.0+` |
| **ASGI Server** | Uvicorn | `0.28.0+` (standard event loop) |
| **Database** | PostgreSQL | `14+` / `15+` / `16+` / `17+` / `18+` (Default: port 5433 or 5432) |
| **DB Driver** | psycopg (v3) | `3.1.18+` (high-performance binary) |
| **ORM** | SQLAlchemy | `2.0.28+` (Mapped Declarative Base) |
| **Migrations** | Alembic | `1.13.1+` |
| **Validation** | Pydantic & Pydantic-Settings | `2.6.4+` |
| **Authentication** | PyJWT | `2.8.0+` |
| **Password Hashing** | Bcrypt & Passlib | `4.1.2+` |
| **AI Integration** | Google Gen AI SDK | `google-genai` / `google-generativeai` |
| **Frontend** | Vanilla JS / Glassmorphism SPA | HTML5, CSS3, ES6+ (Zero external npm framework dependencies) |
| **Testing** | Pytest & HTTPX | `8.1.1+` / `0.27.0+` (40/40 Passing Tests) |

---

## 4. Python Version Compatibility

This application is strictly built and validated across **Python 3.10, 3.11, and 3.12+** on both Windows and Linux/macOS.
- Tested and verified on **Python 3.11.9 (64-bit AMD64)** and Python 3.12.
- Uses modern type hinting syntax (`str | None`, `Mapped[T]`).
- Native bcrypt implementation prevents passlib version inspection conflicts on modern Python releases.
- Fully compatible with Python 3.11 and 3.12 virtual environments.

---

## 5. Project Architecture and Folder Structure

```
task-management-ai/
├── app/
│   ├── api/                     # Route controllers
│   │   ├── __init__.py
│   │   ├── auth.py              # Register, Login, Me endpoints
│   │   ├── tasks.py             # Task CRUD, Status patch, AI generation
│   │   └── admin.py             # User oversight and aggregate statistics
│   ├── auth/                    # Security and token utilities
│   │   ├── __init__.py
│   │   ├── jwt.py               # Token creation and verification
│   │   ├── password.py          # Salted bcrypt hashing
│   │   └── dependencies.py      # get_current_user and role checkers
│   ├── ai/                      # AI integration layer
│   │   ├── __init__.py
│   │   └── gemini_service.py    # Google Gen AI client & error mapping
│   ├── database/                # Database engine & sessions
│   │   ├── __init__.py
│   │   ├── base.py              # DeclarativeBase definition
│   │   └── connection.py        # Engine pool and get_db session dependency
│   ├── models/                  # SQLAlchemy ORM entities
│   │   ├── __init__.py
│   │   ├── user.py              # User model & UserRole enum
│   │   └── task.py              # Task model & TaskStatus enum
│   ├── schemas/                 # Pydantic request/response schemas
│   │   ├── __init__.py
│   │   ├── user.py              # UserRegister, UserLogin, UserResponse
│   │   ├── token.py             # Token & TokenPayload
│   │   └── task.py              # TaskCreate, TaskUpdate, AI schemas
│   ├── services/                # Business logic separation
│   │   ├── __init__.py
│   │   ├── auth_service.py      # Registration & credential checks
│   │   └── task_service.py      # Task ownership & state management
│   ├── config.py                # Environment configuration loader
│   └── main.py                  # FastAPI initialization & error handlers
├── alembic/                     # Database migrations
│   ├── versions/
│   │   └── 001_initial_schema.py# Initial migration for users and tasks
│   ├── env.py                   # Alembic environment runner
│   ├── script.py.mako           # Migration template
│   └── README
├── tests/                       # Automated test suite
│   ├── __init__.py
│   ├── conftest.py              # Test database engine and fixtures
│   ├── test_auth.py             # Authentication & token tests
│   ├── test_tasks.py            # RBAC and task CRUD tests
│   └── test_ai.py               # Mocked Gemini AI tests
├── scripts/                     # Operational scripts
│   ├── __init__.py
│   └── seed.py                  # Idempotent database seeder
├── postman/                     # Postman integration
│   └── task-management-collection.json # Ready-to-import v2.1 collection
├── .env.example                 # Environment configuration template
├── .gitignore                   # Ignore rules for git
├── alembic.ini                  # Alembic CLI configuration
├── requirements.txt             # Production dependencies
└── README.md                    # Comprehensive documentation
```

---

## 6. Prerequisites

Before installing the application, ensure your environment has:
1. **Python 3.12 or newer**: [Download Python](https://www.python.org/downloads/)
2. **PostgreSQL 14+** (Optional for local testing if using SQLite fallback): [Download PostgreSQL](https://www.postgresql.org/download/)
3. **Git**: [Download Git](https://git-scm.com/)
4. A Google AI Studio account for generating a **Gemini API Key**: [Google AI Studio](https://aistudio.google.com/)

---

## 7. Virtual Environment Setup (Windows & macOS/Linux)

### Windows (PowerShell)

```powershell
# Navigate to the project root directory
cd c:\Users\Ammar\OneDrive\Documents\Python_AI

# Create a virtual environment named .venv
python -m venv .venv

# Activate the virtual environment
.\.venv\Scripts\Activate.ps1
```

*Note: If PowerShell displays an execution policy error, run:*
```powershell
Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser
```

### macOS / Linux (Bash or Zsh)

```bash
# Navigate to the project root directory
cd task-management-ai

# Create a virtual environment named .venv
python3 -m venv .venv

# Activate the virtual environment
source .venv/bin/activate
```

---

## 8. Dependency Installation

With your virtual environment active, install all required dependencies:

```bash
pip install --upgrade pip
pip install -r requirements.txt
```

---

## 9. PostgreSQL Database Setup & Configuration

### Create Database in PostgreSQL

1. Open PostgreSQL command shell (`psql`):
   ```bash
   psql -U postgres
   ```
2. Create the application database:
   ```sql
   CREATE DATABASE task_management;
   ```
3. (Optional) Create a dedicated database user:
   ```sql
   CREATE USER task_user WITH PASSWORD 'SecureDbPass123!';
   GRANT ALL PRIVILEGES ON DATABASE task_management TO task_user;
   ```
4. Exit psql:
   ```sql
   \q
   ```

*Note on SQLite fallback: If PostgreSQL is not installed locally, you can change `DATABASE_URL` in `.env` to `sqlite:///./task_management.db` for instant local development without installing a database server.*

---

## 10. Environment Variables Configuration

Copy `.env.example` to create your active `.env` file:

### Windows:
```powershell
Copy-Item .env.example .env
```

### macOS/Linux:
```bash
cp .env.example .env
```

Open `.env` and configure your settings:

```ini
# ==============================================================================
# Database Configuration
# ==============================================================================
DATABASE_URL=postgresql+psycopg://postgres:your_password@localhost:5432/task_management
# Or SQLite fallback:
# DATABASE_URL=sqlite:///./task_management.db

# ==============================================================================
# Security & JWT Authentication
# ==============================================================================
# Generate a secure key: python -c "import secrets; print(secrets.token_hex(32))"
JWT_SECRET_KEY=9b47e2a4c68d19e0f31c2d8b5a4e6f7a8b9c0d1e2f3a4b5c6d7e8f9a0b1c2d3e
JWT_ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=60

# ==============================================================================
# Google Gemini AI Integration
# ==============================================================================
GEMINI_API_KEY=your_actual_gemini_api_key_here
GEMINI_MODEL=gemini-2.5-flash

# ==============================================================================
# Application Settings
# ==============================================================================
ENVIRONMENT=development
DEBUG=true
HOST=0.0.0.0
PORT=8000
```

---

## 11. Google Gemini API Key Setup

1. Visit [Google AI Studio](https://aistudio.google.com/app/apikey).
2. Sign in with your Google account.
3. Click **"Create API key"** and select a Google Cloud project (or generate one automatically).
4. Copy the generated key.
5. Paste it into your `.env` file:
   ```ini
   GEMINI_API_KEY=AIzaSy...your_actual_key...
   ```
6. The application defaults to `gemini-2.5-flash`. You may also specify `gemini-1.5-flash` or `gemini-1.5-pro` via `GEMINI_MODEL`.

> **Note**: The backend starts cleanly even if `GEMINI_API_KEY` is omitted. The AI endpoint will return an informative HTTP 503 error prompting the user to configure the key, without crashing or exposing errors.

---

## 12. Alembic Database Migrations

Apply the database schema without manual SQL scripts:

```bash
# Run migrations up to latest version
alembic upgrade head
```

To roll back a migration if ever needed:
```bash
alembic downgrade -1
```

To generate new migrations in the future after modifying models:
```bash
alembic revision --autogenerate -m "describe_changes"
```

---

## 13. Database Seeding

Populate the database with sample users and tasks:

```bash
python scripts/seed.py
```

### Seeder Guarantees:
- **Idempotent**: Safe to run multiple times without creating duplicate records.
- **Passwords are securely hashed**: Generates salted bcrypt hashes.
- **Sets up sample records**: Creates 1 Administrator, 2 Regular Users, and 5 Sample Tasks in different lifecycle states.

---

## 14. Running the Application

Launch the development server using Uvicorn:

```bash
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

The server will be reachable at:
- **Base URL**: `http://localhost:8000`
- **Health Check**: `http://localhost:8000/health`

---

## 15. Interactive Swagger & OpenAPI Documentation

FastAPI automatically generates interactive API documentation with Bearer token authentication support:

- **Swagger UI**: [http://localhost:8000/docs](http://localhost:8000/docs)
- **ReDoc UI**: [http://localhost:8000/redoc](http://localhost:8000/redoc)
- **OpenAPI JSON**: [http://localhost:8000/openapi.json](http://localhost:8000/openapi.json)

To authorize requests in Swagger UI:
1. Click the green **Authorize** button at the top right.
2. In the `HTTPBearer` input, paste your `access_token` (without the word "Bearer").
3. Click **Authorize** and test any endpoint interactively.

---

## 16. Complete API Endpoint Reference

### Authentication Endpoints (`/api/auth`)

| Method | Endpoint | Description | Access | Status Codes |
| :--- | :--- | :--- | :--- | :--- |
| `POST` | `/api/auth/register` | Register a new user (`name`, `email`, `password`) | Public | `201`, `409`, `422` |
| `POST` | `/api/auth/login` | Authenticate user credentials and receive JWT | Public | `200`, `401`, `422` |
| `GET` | `/api/auth/me` | Retrieve profile of the currently logged-in user | Authenticated | `200`, `401` |

### Task Management Endpoints (`/api/tasks`)

| Method | Endpoint | Description | Access | Status Codes |
| :--- | :--- | :--- | :--- | :--- |
| `POST` | `/api/tasks/` | Create a new task (`title`, `description`) | Authenticated | `201`, `401`, `422` |
| `GET` | `/api/tasks/` | List tasks (pagination: `page`, `limit`; filter: `status`) | Authenticated | `200`, `401` |
| `POST` | `/api/tasks/generate-description` | Generate AI task description using Gemini | Authenticated | `200`, `401`, `422`, `429`, `502`, `503` |
| `GET` | `/api/tasks/{task_id}` | Retrieve task by ID (isolated: owner or admin only) | Owner / Admin | `200`, `401`, `404` |
| `PUT` | `/api/tasks/{task_id}` | Update task title and description | Owner / Admin | `200`, `401`, `403`, `404`, `422` |
| `PATCH`| `/api/tasks/{task_id}/status` | Advance task status (`Pending`, `In Progress`, `Testing`, `Completed`) | Admin Only | `200`, `401`, `403`, `404`, `422` |
| `DELETE`| `/api/tasks/{task_id}`| Delete a task by ID | Owner / Admin | `204`, `401`, `404` |

### Admin Management Endpoints (`/api/admin`)

| Method | Endpoint | Description | Access | Status Codes |
| :--- | :--- | :--- | :--- | :--- |
| `GET` | `/api/admin/users` | List all registered user accounts | Admin Only | `200`, `401`, `403` |
| `PATCH`| `/api/admin/users/{id}/role` | Promote user or alter system role | Admin Only | `200`, `401`, `403`, `404` |
| `GET` | `/api/admin/stats` | View aggregate statistics & task status breakdown | Admin Only | `200`, `401`, `403` |

### System Endpoints

| Method | Endpoint | Description | Access | Status Codes |
| :--- | :--- | :--- | :--- | :--- |
| `GET` | `/health` | Application status, database connection, and AI flag | Public | `200` |
| `GET` | `/` | API welcome message and documentation links | Public | `200` |

---

## 17. Local Development Test Credentials

The database seeder (`scripts/seed.py`) creates these development accounts:

| Role | Name | Email | Password |
| :--- | :--- | :--- | :--- |
| **Administrator** | System Administrator | `admin@taskflow.dev` | `AdminPass123!` |
| **Regular User** | Jane Developer | `user@taskflow.dev` | `UserPass123!` |
| **Second User** | Alex Designer | `alex@taskflow.dev` | `AlexPass123!` |

> **Warning**: These credentials are for local development and assessment evaluation only. Never use these credentials in a public or production deployment.

---

## 18. Importing and Running the Postman Collection

The file `postman/task-management-collection.json` contains a Postman Collection v2.1.0 ready for import.

### Import Instructions:
1. Open Postman.
2. Click **File -> Import** (or drag and drop).
3. Select `postman/task-management-collection.json`.
4. The collection will appear in your sidebar as **AI-Powered Task Management System API**.

### Automated Tests Included:
The collection includes automated JavaScript test scripts:
- **Auto-captures tokens**: Logging in as user or admin saves `user_token` and `admin_token` variables automatically.
- **Auto-captures task IDs**: Creating a task saves `task_id` for downstream requests.
- **Verifies RBAC rules**:
  - `Attempt Status Update as Regular User` checks that the server returns `403 Forbidden`.
  - `Attempt Access Another User's Task` checks that the server returns `404 Not Found`.

---

## 19. Running Automated Tests with Pytest

Run the comprehensive test suite:

```bash
pytest
```

For verbose output with test names and execution times:
```bash
pytest -v
```

To run with coverage (if `pytest-cov` is installed):
```bash
pytest --cov=app --cov-report=term-missing
```

### Covered Test Cases:
- `test_auth.py`:
  - User registration with default `user` role
  - Rejection of duplicate email with HTTP 409
  - Prevention of privilege escalation during public registration
  - Password minimum length validation (HTTP 422)
  - Successful login returning JWT access token
  - Rejection of invalid credentials (HTTP 401)
  - Access to safe user profile via `/api/auth/me`
  - Rejection of missing, malformed, or expired JWTs
- `test_tasks.py`:
  - Authenticated task creation with enforced user ownership
  - Neutralization of spoofed client-supplied `user_id`
  - Admin task creation for designated user IDs
  - Strict user task list isolation (users only see their own tasks)
  - Admin global task visibility
  - Task status filtering and pagination
  - Owner task retrieval and update
  - Rejection of cross-user task access with HTTP 404
  - Rejection of regular user attempts to modify status (HTTP 403)
  - Admin-only status modification via `PATCH /api/tasks/{task_id}/status`
  - Unrecognized status validation error (HTTP 422)
  - Task deletion by owner (HTTP 204)
- `test_ai.py`:
  - Authentication requirement for AI generation (HTTP 401)
  - Validation of title length (minimum 3 characters)
  - Successful description generation with mocked Gemini SDK
  - Unconfigured API key handling (HTTP 503)
  - Provider rate limit handling (HTTP 429)
  - Provider unavailability and timeouts (HTTP 503 / 502)
- `test_database_rollback.py`:
  - Rollback on unhandled exception in route dependency lifecycle
  - Immediate session and connection recovery for subsequent operations
  - IntegrityError rollback verification during duplicate registrations
  - Generator lifecycle cleanup ensuring active transactions are aborted before connection release

---

## 20. Implemented AI Feature & Failure Handling

### Endpoint
`POST /api/tasks/generate-description`

### Request Payload
```json
{
  "title": "Prepare monthly sales report"
}
```

### Response Payload
```json
{
  "title": "Prepare monthly sales report",
  "description": "Compile quarterly regional sales figures, analyze month-over-month variance, and draft an executive summary deck highlighting key growth drivers."
}
```

### Error Classification & Security:
1. **Unconfigured Key**: Returns `HTTP 503 Service Unavailable` with message: *"AI service is not configured. Please set GEMINI_API_KEY in the environment."*
2. **Rate Limit / Quota Exceeded**: Returns `HTTP 429 Too Many Requests` with message: *"AI provider rate limit reached. Please retry after a brief pause."*
3. **Provider Timeout / Unreachable**: Returns `HTTP 503 Service Unavailable` with message: *"AI provider is temporarily unavailable. Please retry later."*
4. **Credential Safety**: Internal exception handlers strip API keys, connection details, and stack traces before returning responses to the caller.

---

## 21. Security Architecture & Assumptions

1. **Client Untrust Principle**: Any `user_id` supplied by regular users during task creation is discarded; tasks are always bound to `current_user.id`.
2. **Enumeration Protection**: Unauthorized attempts to access tasks owned by other users return `HTTP 404 Not Found` rather than `403 Forbidden`. This prevents attackers from enumerating valid IDs.
3. **Role Lockdown**: Public registration does not expose or accept a `role` parameter. The system unconditionally initializes accounts with the `user` role.
4. **Status Tampering Defense**: Even if a regular user crafts a manual `PUT` body containing `"status": "Completed"`, the service intercepts the field and rejects the request with `403 Forbidden`.
5. **Safe Serializers**: Pydantic schemas explicitly omit the `password` field from all response models.

---

## 22. Production Deployment Guidelines

To deploy this backend to production platforms (e.g., Render, Railway, AWS ECS, Fly.io, or DigitalOcean):

1. **Set Environment Variables**:
   - Set `ENVIRONMENT=production`
   - Set `DEBUG=false`
   - Set a strong, randomly generated `JWT_SECRET_KEY` (minimum 32 bytes)
   - Configure managed PostgreSQL connection string in `DATABASE_URL`
   - Set `GEMINI_API_KEY`
2. **Execute Migrations on Release**:
   Configure your deployment pipeline or Docker entrypoint to run:
   ```bash
   alembic upgrade head
   ```
3. **Run Production Server**:
   Launch with multiple Uvicorn workers behind a reverse proxy (Nginx or Cloudflare):
   ```bash
   uvicorn app.main:app --host 0.0.0.0 --port 8000 --workers 4 --proxy-headers --forwarded-allow-ips='*'
   ```
