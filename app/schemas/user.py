from datetime import datetime

from pydantic import BaseModel, EmailStr, Field

from app.models.user import UserRole


class UserBase(BaseModel):
    name: str
    email: EmailStr
    phone: str | None = None
    role: UserRole = UserRole.STUDENT
    department_id: int | None = None
    is_active: bool = True

class UserCreate(UserBase):
    password: str = Field(..., min_length=6)

class UserUpdate(BaseModel):
    name: str | None = None
    email: EmailStr | None = None
    phone: str | None = None
    role: UserRole | None = None
    department_id: int | None = None
    is_active: bool | None = None
    password: str | None = None

class UserUpdateMe(BaseModel):
    name: str | None = None
    email: EmailStr | None = None
    phone: str | None = None
    password: str | None = None

class UserOut(BaseModel):
    id: int
    name: str
    email: EmailStr
    phone: str | None = None
    role: str
    department_id: int | None = None
    is_active: bool
    created_at: datetime

    class Config:
        from_attributes = True
