from app.schemas.auth import Token, TokenPayload, LoginRequest, RefreshRequest
from app.schemas.user import UserCreate, UserUpdate, UserOut, UserUpdateMe
from app.schemas.department import (
    DepartmentCreate,
    DepartmentUpdate,
    DepartmentOut,
    ComplaintCategoryCreate,
    ComplaintCategoryUpdate,
    ComplaintCategoryOut,
)
from app.schemas.complaint import (
    ComplaintCreate,
    ComplaintUpdate,
    ComplaintOut,
    ComplaintDetailOut,
    ComplaintCommentCreate,
    ComplaintCommentOut,
    ComplaintFileOut,
    ComplaintAssignmentCreate,
    ComplaintAssignmentOut,
    ComplaintHistoryOut,
    ComplaintFeedbackCreate,
    ComplaintStatusUpdate,
)
from app.schemas.analytics import StudentDashboard, DepartmentDashboard, AdminDashboard
