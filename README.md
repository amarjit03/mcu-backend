# Student Complaint Management System Backend

A production-grade, asynchronous backend API built with **FastAPI**, **SQLAlchemy 2.0**, and **PostgreSQL**, following clean architecture, strict static typing, and automated testing principles.

---

## 🛠 Tech Stack & Tooling

- **Language:** Python 3.12+ (CPython 3.13 supported)
- **Framework:** FastAPI (Asynchronous Router)
- **Database ORM:** SQLAlchemy 2.0 (Declarative Base & Mapped type safety)
- **Migrations:** Alembic
- **Caching & Rate Limiting:** Redis
- **Package Manager:** `uv` (Fastest Python dependency resolver)
- **Testing:** Pytest (Asynchronous fixtures and API testing)
- **Quality Assurance:** Ruff (Linter & Formatter), MyPy (Strict Static Types)

---

## 🚀 Quick Start Guide

### 1. Prerequisites

Ensure you have the following installed on your system:
- **Python 3.12+**
- **uv** (Install via `curl -LsSf https://astral.sh/uv/install.sh | sh`)
- **PostgreSQL** (Or connection string to serverless Neon database)
- **Redis** (For caching and rate limiting)

### 2. Environment Configuration

Clone the repository and create your local environment configuration file:

```bash
# Copy the example environment template
cp .env.example .env
```

Open `.env` and configure your credentials:
```ini
PROJECT_NAME="Student Complaint Management System"
ENV=dev
DEBUG=true

# Database DSN
# Use standard postgresql:// connection string (sync/async protocols are mapped dynamically)
DATABASE_URL="postgresql://user:password@localhost:5432/complaint_system"

# Cache Store
REDIS_URL="redis://localhost:6379/0"

# JWT Secrets (generate via `openssl rand -hex 32`)
SECRET_KEY="your-super-secret-key-hex"
ALGORITHM="HS256"
ACCESS_TOKEN_EXPIRE_MINUTES=30
REFRESH_TOKEN_EXPIRE_DAYS=7
```

### 3. Installation & Virtual Environment

Use `uv` to automatically download the correct Python runtime, create a virtual environment, and sync dependencies:

```bash
# Sync dependencies and build virtual environment
uv sync
```

This installs all dependencies declared in `pyproject.toml` into a local `.venv/` folder.

### 4. Run Database Migrations

Apply database schemas using Alembic:

```bash
# Run migrations to update to the latest schema
uv run alembic upgrade head
```

### 5. Seed Database

Populate the database with default departments, categories, and test user accounts (Super Admin, Admin, Department Head, Staff, and Student):

```bash
# Run the async database seeding script
uv run python -m app.db.seed
```

---

## 🔑 MVP Test Credentials

Once the seeding script completes, the following pre-configured test users are available in the database (all share the password `password123`):

| Role | Email | Permissions / Workflow Role |
| :--- | :--- | :--- |
| **Super Admin** | `superadmin@admin.com` | Global override, system control |
| **Admin** | `admin@admin.com` | Create departments, categories, manage users, view analytics |
| **Department Head** | `hostelhead@admin.com` | Dashboard review, assign staff, escalate priority |
| **Staff Member** | `hostelstaff@admin.com` | Accept complaints, add internal notes, post resolutions |
| **Student** | `student@student.com` | Submit complaints, upload files, chat, reopen, submit ratings |

---

## 🔄 End-to-End MVP Testing Workflow

Follow this standard flow to verify the application via Swagger UI ([http://localhost:8000/docs](http://localhost:8000/docs)):

### Step 1: Authentication & Token Authorization
1. Go to the Swagger UI page.
2. Click the green **Authorize** button in the top right.
3. Enter `student@student.com` as the username and `password123` as the password, then click **Authorize**.
4. Alternatively, use the `POST /api/v1/auth/login` endpoint to obtain a token and pass it in the `Authorization: Bearer <token>` header of your API requests.

### Step 2: Student Submits a Complaint
1. Go to the `POST /api/v1/student/complaints` endpoint.
2. Submit a request body like:
   ```json
   {
     "title": "Wi-Fi not working in room 302",
     "description": "The campus Wi-Fi has been dropping connection frequently since yesterday.",
     "category_id": 1,
     "department_id": 1,
     "priority": "MEDIUM",
     "anonymous": false
   }
   ```
3. Copy the returned complaint `id` (e.g. `1`) and the generated ticket number (e.g. `COMP-YYYYMMDD-0001`).

### Step 3: Department Head Assigns Staff
1. Re-authorize Swagger using the Department Head credentials:
   - Username: `hostelhead@admin.com`
   - Password: `password123`
2. Go to the `POST /api/v1/department/assign` endpoint.
3. Query the `complaint_id` with `1` and set the body `staff_id` to `4` (the hostel staff member id).

### Step 4: Staff Resolves the Complaint
1. Re-authorize Swagger using the Staff credentials:
   - Username: `hostelstaff@admin.com`
   - Password: `password123`
2. Go to the `POST /api/v1/staff/complaints/1/accept` endpoint to mark the status as `IN_PROGRESS`.
3. Go to the `POST /api/v1/staff/complaints/1/resolve` endpoint. Send a resolution comment:
   ```json
   {
     "message": "Replaced the network router on the 3rd floor. The connection is stable now."
   }
   ```

### Step 5: Student Submits Feedback & Closes Complaint
1. Re-authorize Swagger using the Student credentials:
   - Username: `student@student.com`
   - Password: `password123`
2. Go to the `POST /api/v1/student/complaints/1/feedback` endpoint. Submit a rating:
   ```json
   {
     "rating": 5,
     "comment": "Thank you for the quick resolution!"
   }
   ```
3. Verify that the complaint status is now automatically updated to `CLOSED`.

### 6. Run the Application

Start the local Uvicorn development server:

```bash
# Launch FastAPI development server
uv run uvicorn app.main:app --reload --port 8000
```

Once running, you can explore the API documentation at:
- **Swagger UI:** [http://localhost:8000/docs](http://localhost:8000/docs)
- **ReDoc:** [http://localhost:8000/redoc](http://localhost:8000/redoc)

---

## 🧪 Testing Suite

We use **Pytest** with asynchronous engine configurations for integration and unit testing.

### Run Tests

Execute the test suite locally:

```bash
# Run all tests asynchronously
uv run pytest
```

### Coverage Reports

Generate code coverage statistics to verify test path execution:

```bash
# Run tests with coverage tracking
uv run pytest --cov=app tests/
```

---

## 🛡 Code Quality & Type Checks

To maintain enterprise-grade software standards, we enforce strict formatting and static type validations.

### 1. Ruff Linting & Formatting
Verify formatting rules, import ordering, and unused imports:

```bash
# Check code style
uv run ruff check app/ tests/

# Automatically fix linting and formatting issues
uv run ruff check --fix app/ tests/
```

### 2. MyPy Static Type Verification
Check strict type annotations across the workspace:

```bash
# Run strict static type checking
uv run mypy app/ tests/
```

---

## 📁 Project Architecture & Layout

```text
backend/
├── app/
│   ├── api/             # API Router layers (v1 endpoints)
│   │   ├── deps.py      # Dependency injection modules (Auth/DB contexts)
│   │   └── v1/          # Routers (auth, complaints, students, staff, admin, reports)
│   ├── core/            # Config variables, structured JSON logging, constants
│   ├── db/              # Async session manager, declarative base class, seeders
│   ├── models/          # SQLAlchemy 2.0 type-safe declarative models
│   ├── schemas/         # Pydantic validation schemas
│   ├── services/        # Business logic services
│   └── main.py          # Application entrypoint
├── tests/               # Pytest suite (fixtures, unit, integration tests)
├── migrations/          # Alembic migrations history
└── pyproject.toml       # Python package, dependency, and tool configs
```
