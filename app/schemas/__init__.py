from app.schemas.analytics import AdminDashboard, DepartmentDashboard, StudentDashboard
from app.schemas.auth import LoginRequest, RefreshRequest, Token, TokenPayload
from app.schemas.complaint import (
    ComplaintAssignmentCreate,
    ComplaintAssignmentOut,
    ComplaintCommentCreate,
    ComplaintCommentOut,
    ComplaintCreate,
    ComplaintDetailOut,
    ComplaintFeedbackCreate,
    ComplaintFileOut,
    ComplaintHistoryOut,
    ComplaintOut,
    ComplaintStatusUpdate,
    ComplaintUpdate,
)
from app.schemas.department import (
    ComplaintCategoryCreate,
    ComplaintCategoryOut,
    ComplaintCategoryUpdate,
    DepartmentCreate,
    DepartmentOut,
    DepartmentUpdate,
)
from app.schemas.user import UserCreate, UserOut, UserUpdate, UserUpdateMe
