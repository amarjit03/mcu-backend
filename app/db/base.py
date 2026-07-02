# Import all models so that Base.metadata has them loaded before Alembic reads it
from app.db.base_class import Base  # noqa
from app.models.user import User, UserRole  # noqa
from app.models.department import Department, ComplaintCategory  # noqa
from app.models.complaint import (  # noqa
    Complaint,
    ComplaintAssignment,
    ComplaintComment,
    ComplaintFile,
    ComplaintPriority,
    ComplaintStatus,
)
from app.models.history import ComplaintHistory  # noqa
