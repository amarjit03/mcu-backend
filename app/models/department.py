from sqlalchemy import Column, Integer, String, ForeignKey
from sqlalchemy.orm import relationship
from app.database import Base

class Department(Base):
    __tablename__ = "departments"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, unique=True, nullable=False)
    email = Column(String, nullable=True)
    head_id = Column(Integer, ForeignKey("users.id", use_alter=True, name="fk_department_head_id"), nullable=True)

    # Relationships
    head = relationship("User", foreign_keys=[head_id], back_populates="headed_department")
    staff_members = relationship("User", foreign_keys="[User.department_id]", back_populates="department")
    categories = relationship("ComplaintCategory", back_populates="department", cascade="all, delete-orphan")
    complaints = relationship("Complaint", back_populates="department")

class ComplaintCategory(Base):
    __tablename__ = "complaint_categories"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False)
    department_id = Column(Integer, ForeignKey("departments.id"), nullable=False)

    # Relationships
    department = relationship("Department", back_populates="categories")
    complaints = relationship("Complaint", back_populates="category")
