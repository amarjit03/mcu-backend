from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.v1 import admin, auth, files, head, reports, search, staff, student
from app.core.config import settings
from app.core.logging import setup_logging
from app.middleware.logging import LoggingMiddleware

# Setup structured and colorized logging
setup_logging(env=settings.ENV, debug=settings.DEBUG)

@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    # --- STARTUP HANDLER ---
    db_ok = False
    try:
        from sqlalchemy.sql import text

        from app.db.session import engine
        async with engine.connect() as conn:
            await conn.execute(text("SELECT 1"))
        db_ok = True
    except Exception as e:
        print(f"Database connection error: {e}")

    redis_ok = False
    try:
        import redis.asyncio as aioredis
        r = aioredis.from_url(settings.REDIS_URL)
        await r.ping()
        await r.close()
        redis_ok = True
    except Exception as e:
        print(f"Redis connection error: {e}")

    jwt_ok = bool(settings.SECRET_KEY and settings.ALGORITHM)
    logging_ok = True

    env_name = "Production" if settings.ENV.lower() == "prod" else "Development"

    box = (
        "\n"
        "━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
        f"{settings.PROJECT_NAME}\n"
        f"Environment: {env_name}\n"
        "Version: 1.0.0\n\n"
        f"Database {'✓' if db_ok else '✗'}\n"
        f"Redis    {'✓' if redis_ok else '✗'}\n"
        f"JWT      {'✓' if jwt_ok else '✗'}\n"
        f"Logging  {'✓' if logging_ok else '✗'}\n\n"
        "API Docs:\n"
        f"http://localhost:{settings.PORT}/docs\n"
        "━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
    )
    print(box)

    yield

    # --- SHUTDOWN HANDLER ---
    print("Stopping API...")
    print("Closing DB...")
    from app.db.session import engine
    await engine.dispose()
    print("Closing Redis...")
    print("Shutdown complete.")

app = FastAPI(
    title=settings.PROJECT_NAME,
    description="Production-Ready backend API for Student Complaint Management System",
    version="1.0.0",
    docs_url="/docs" if settings.DEBUG else None,
    redoc_url="/redoc" if settings.DEBUG else None,
    lifespan=lifespan,
)

# Set up CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_headers=["*"],
    allow_methods=["*"],
)

# Register request logger middleware (outermost execution)
app.add_middleware(LoggingMiddleware)

# Mount API routers (Deduplicated Prefix Mounts)

# 1. Auth Router
app.include_router(auth.router, prefix="/api/v1/auth", tags=["Authentication"])

# 2. Student & Complaint Router
app.include_router(student.router, prefix="/api/v1/student", tags=["Student Profile & Complaints"])

# 3. Staff Router
app.include_router(staff.router, prefix="/api/v1/staff", tags=["Staff Management"])

# 4. Department Head Router
app.include_router(head.router, prefix="/api/v1/department", tags=["Department Head Management"])

# 5. Admin Router
app.include_router(admin.router, prefix="/api/v1/admin", tags=["Administrator Management"])

# 6. Advanced Search Router
app.include_router(search.router, prefix="/api/v1/search", tags=["Search Operations"])

# 7. File Upload Router
app.include_router(files.router, prefix="/api/v1", tags=["File Storage Operations"])

# 8. Report Router
app.include_router(reports.router, prefix="/api/v1/reports", tags=["Export Reports"])

@app.get("/", tags=["Root"])
def root_status() -> dict[str, str]:
    return {
        "status": "online",
        "project": settings.PROJECT_NAME,
        "documentation": "/docs"
    }

@app.get("/health", tags=["Monitoring"])
def health_check() -> dict[str, str]:
    return {
        "status": "healthy",
        "version": "1.0.0"
    }

