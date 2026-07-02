import enum

from sqlalchemy import Boolean, Column, DateTime, ForeignKey, Integer, String
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from app.database import Base


class UserRole(enum.StrEnum):
    STUDENT = "STUDENT"
    STAFF = "STAFF"
    HEAD = "HEAD"
    ADMIN = "ADMIN"
    SUPERADMIN = "SUPERADMIN"

class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False)
    email = Column(String, unique=True, index=True, nullable=False)
    phone = Column(String, nullable=True)
    password_hash = Column(String, nullable=False)
    role = Column(String, default=UserRole.STUDENT, nullable=False)
    department_id = Column(Integer, ForeignKey("departments.id", use_alter=True, name="fk_user_department_id"), nullable=True)
    is_active = Column(Boolean, default=True, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    # Relationships
    department = relationship("Department", foreign_keys=[department_id], back_populates="staff_members")
    headed_department = relationship("Department", back_populates="head", foreign_keys="[Department.head_id]")

    complaints = relationship("Complaint", back_populates="student", foreign_keys="[Complaint.student_id]")
    uploaded_files = relationship("ComplaintFile", back_populates="uploader")
    comments = relationship("ComplaintComment", back_populates="user")
    history_actions = relationship("ComplaintHistory", back_populates="performer")

    assignments_received = relationship("ComplaintAssignment", back_populates="staff", foreign_keys="[ComplaintAssignment.staff_id]")
    assignments_given = relationship("ComplaintAssignment", back_populates="assigner", foreign_keys="[ComplaintAssignment.assigned_by]")
