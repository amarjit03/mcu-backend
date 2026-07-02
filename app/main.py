from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.config import settings
from app.api.v1 import auth, student, staff, head, admin, search, files, reports

app = FastAPI(
    title=settings.PROJECT_NAME,
    description="Backend API for Student Complaint Management System MVP",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
)

# Set up CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_headers=["*"],
    allow_methods=["*"],
)

# Mount API routers (both V1 structured and root aliases for exact requirement matching)

# 1. Auth Routers
app.include_router(auth.router, prefix="/api/v1/auth", tags=["Authentication"])
app.include_router(auth.router, prefix="/auth", tags=["Authentication"])

# 2. Student & Complaint Routers (Student API endpoints like /complaints/...)
app.include_router(student.router, prefix="/api/v1/student", tags=["Student Profile"])
app.include_router(student.router, prefix="/student", tags=["Student Profile"])
app.include_router(student.router, prefix="/api/v1", tags=["Complaints & Interactions"])
app.include_router(student.router, prefix="", tags=["Complaints & Interactions"])

# 3. Staff Routers
app.include_router(staff.router, prefix="/api/v1/staff", tags=["Staff Management"])
app.include_router(staff.router, prefix="/staff", tags=["Staff Management"])

# 4. Department Head Routers
app.include_router(head.router, prefix="/api/v1/department", tags=["Department Head Management"])
app.include_router(head.router, prefix="/department", tags=["Department Head Management"])

# 5. Admin Routers
app.include_router(admin.router, prefix="/api/v1/admin", tags=["Administrator Management"])
app.include_router(admin.router, prefix="/admin", tags=["Administrator Management"])

# 6. Advanced Search Router
app.include_router(search.router, prefix="/api/v1/search", tags=["Search Operations"])
app.include_router(search.router, prefix="/search", tags=["Search Operations"])

# 7. File Upload Router
app.include_router(files.router, prefix="/api/v1", tags=["File Storage Operations"])
app.include_router(files.router, prefix="", tags=["File Storage Operations"])

# 8. Report Export Router
app.include_router(reports.router, prefix="/api/v1/reports", tags=["Export Reports"])
app.include_router(reports.router, prefix="/reports", tags=["Export Reports"])

@app.get("/", tags=["Root"])
def root_status():
    return {
        "status": "online",
        "project": settings.PROJECT_NAME,
        "documentation": "/docs"
    }
