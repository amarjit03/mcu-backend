import enum
from datetime import datetime
from typing import TYPE_CHECKING, Optional

from sqlalchemy import DateTime, ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.sql import func

from app.db.base_class import Base

if TYPE_CHECKING:
    from app.models.complaint import Complaint, ComplaintAssignment, ComplaintComment, ComplaintFile
    from app.models.department import Department
    from app.models.history import ComplaintHistory


class UserRole(enum.StrEnum):
    STUDENT = "STUDENT"
    STAFF = "STAFF"
    HEAD = "HEAD"
    ADMIN = "ADMIN"
    SUPERADMIN = "SUPERADMIN"


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    name: Mapped[str] = mapped_column(String, nullable=False)
    email: Mapped[str] = mapped_column(String, unique=True, index=True, nullable=False)
    phone: Mapped[str | None] = mapped_column(String, nullable=True)
    password_hash: Mapped[str] = mapped_column(String, nullable=False)
    role: Mapped[str] = mapped_column(String, default=UserRole.STUDENT, nullable=False)
    department_id: Mapped[int | None] = mapped_column(
        ForeignKey("departments.id", use_alter=True, name="fk_user_department_id"),
        nullable=True,
    )
    is_active: Mapped[bool] = mapped_column(default=True, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )

    # Relationships
    department: Mapped[Optional["Department"]] = relationship(
        "Department",
        foreign_keys=[department_id],
        back_populates="staff_members",
    )
    headed_department: Mapped[Optional["Department"]] = relationship(
        "Department",
        back_populates="head",
        foreign_keys="[Department.head_id]",
    )

    complaints: Mapped[list["Complaint"]] = relationship(
        "Complaint",
        back_populates="student",
        foreign_keys="[Complaint.student_id]",
    )
    uploaded_files: Mapped[list["ComplaintFile"]] = relationship(
        "ComplaintFile",
        back_populates="uploader",
    )
    comments: Mapped[list["ComplaintComment"]] = relationship(
        "ComplaintComment",
        back_populates="user",
    )
    history_actions: Mapped[list["ComplaintHistory"]] = relationship(
        "ComplaintHistory",
        back_populates="performer",
    )

    assignments_received: Mapped[list["ComplaintAssignment"]] = relationship(
        "ComplaintAssignment",
        back_populates="staff",
        foreign_keys="[ComplaintAssignment.staff_id]",
    )
    assignments_given: Mapped[list["ComplaintAssignment"]] = relationship(
        "ComplaintAssignment",
        back_populates="assigner",
        foreign_keys="[ComplaintAssignment.assigned_by]",
    )
