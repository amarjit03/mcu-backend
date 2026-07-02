import enum
from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import Boolean, DateTime, ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.sql import func

from app.db.base_class import Base

if TYPE_CHECKING:
    from app.models.department import ComplaintCategory, Department
    from app.models.history import ComplaintHistory
    from app.models.user import User


class ComplaintPriority(enum.StrEnum):
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"
    URGENT = "URGENT"


class ComplaintStatus(enum.StrEnum):
    NEW = "NEW"
    ASSIGNED = "ASSIGNED"
    IN_PROGRESS = "IN_PROGRESS"
    WAITING_FOR_STUDENT = "WAITING_FOR_STUDENT"
    RESOLVED = "RESOLVED"
    CLOSED = "CLOSED"
    REOPENED = "REOPENED"
    REJECTED = "REJECTED"


class Complaint(Base):
    __tablename__ = "complaints"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    ticket_number: Mapped[str] = mapped_column(String, unique=True, index=True, nullable=False)
    title: Mapped[str] = mapped_column(String, nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    student_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False)
    category_id: Mapped[int] = mapped_column(ForeignKey("complaint_categories.id"), nullable=False)
    department_id: Mapped[int] = mapped_column(ForeignKey("departments.id"), nullable=False)
    priority: Mapped[str] = mapped_column(String, default=ComplaintPriority.MEDIUM, nullable=False)
    status: Mapped[str] = mapped_column(String, default=ComplaintStatus.NEW, nullable=False)
    anonymous: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

    # Feedback fields
    feedback_rating: Mapped[int | None] = mapped_column(nullable=True)  # 1-5 stars
    feedback_comment: Mapped[str | None] = mapped_column(Text, nullable=True)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )
    closed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )

    # Relationships
    student: Mapped["User"] = relationship(
        "User",
        foreign_keys=[student_id],
        back_populates="complaints",
    )
    category: Mapped["ComplaintCategory"] = relationship(
        "ComplaintCategory",
        back_populates="complaints",
    )
    department: Mapped["Department"] = relationship(
        "Department",
        back_populates="complaints",
    )

    files: Mapped[list["ComplaintFile"]] = relationship(
        "ComplaintFile",
        back_populates="complaint",
        cascade="all, delete-orphan",
    )
    comments: Mapped[list["ComplaintComment"]] = relationship(
        "ComplaintComment",
        back_populates="complaint",
        cascade="all, delete-orphan",
    )
    history: Mapped[list["ComplaintHistory"]] = relationship(
        "ComplaintHistory",
        back_populates="complaint",
        cascade="all, delete-orphan",
    )
    assignments: Mapped[list["ComplaintAssignment"]] = relationship(
        "ComplaintAssignment",
        back_populates="complaint",
        cascade="all, delete-orphan",
    )


class ComplaintFile(Base):
    __tablename__ = "complaint_files"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    complaint_id: Mapped[int] = mapped_column(ForeignKey("complaints.id"), nullable=False)
    file_path: Mapped[str] = mapped_column(String, nullable=False)
    uploaded_by: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )

    # Relationships
    complaint: Mapped["Complaint"] = relationship(
        "Complaint",
        back_populates="files",
    )
    uploader: Mapped["User"] = relationship(
        "User",
        back_populates="uploaded_files",
    )


class ComplaintComment(Base):
    __tablename__ = "complaint_comments"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    complaint_id: Mapped[int] = mapped_column(ForeignKey("complaints.id"), nullable=False)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False)
    message: Mapped[str] = mapped_column(Text, nullable=False)
    internal_note: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )

    # Relationships
    complaint: Mapped["Complaint"] = relationship(
        "Complaint",
        back_populates="comments",
    )
    user: Mapped["User"] = relationship(
        "User",
        back_populates="comments",
    )


class ComplaintAssignment(Base):
    __tablename__ = "complaint_assignments"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    complaint_id: Mapped[int] = mapped_column(ForeignKey("complaints.id"), nullable=False)
    staff_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False)
    assigned_by: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False)
    assigned_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )

    # Relationships
    complaint: Mapped["Complaint"] = relationship(
        "Complaint",
        back_populates="assignments",
    )
    staff: Mapped["User"] = relationship(
        "User",
        foreign_keys=[staff_id],
        back_populates="assignments_received",
    )
    assigner: Mapped["User"] = relationship(
        "User",
        foreign_keys=[assigned_by],
        back_populates="assignments_given",
    )
