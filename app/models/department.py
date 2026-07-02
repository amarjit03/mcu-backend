from typing import TYPE_CHECKING, Optional

from sqlalchemy import ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base_class import Base

if TYPE_CHECKING:
    from app.models.complaint import Complaint
    from app.models.user import User


class Department(Base):
    __tablename__ = "departments"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    name: Mapped[str] = mapped_column(String, unique=True, nullable=False)
    email: Mapped[str | None] = mapped_column(String, nullable=True)
    head_id: Mapped[int | None] = mapped_column(
        ForeignKey("users.id", use_alter=True, name="fk_department_head_id"),
        nullable=True,
    )

    # Relationships
    head: Mapped[Optional["User"]] = relationship(
        "User",
        foreign_keys=[head_id],
        back_populates="headed_department",
    )
    staff_members: Mapped[list["User"]] = relationship(
        "User",
        foreign_keys="[User.department_id]",
        back_populates="department",
    )
    categories: Mapped[list["ComplaintCategory"]] = relationship(
        "ComplaintCategory",
        back_populates="department",
        cascade="all, delete-orphan",
    )
    complaints: Mapped[list["Complaint"]] = relationship(
        "Complaint",
        back_populates="department",
    )


class ComplaintCategory(Base):
    __tablename__ = "complaint_categories"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    name: Mapped[str] = mapped_column(String, nullable=False)
    department_id: Mapped[int] = mapped_column(
        ForeignKey("departments.id"),
        nullable=False,
    )

    # Relationships
    department: Mapped["Department"] = relationship(
        "Department",
        back_populates="categories",
    )
    complaints: Mapped[list["Complaint"]] = relationship(
        "Complaint",
        back_populates="category",
    )
