from pydantic import BaseModel


class ComplaintCategoryBase(BaseModel):
    name: str
    department_id: int

class ComplaintCategoryCreate(ComplaintCategoryBase):
    pass

class ComplaintCategoryUpdate(BaseModel):
    name: str | None = None
    department_id: int | None = None

class ComplaintCategoryOut(ComplaintCategoryBase):
    id: int

    class Config:
        from_attributes = True

class DepartmentBase(BaseModel):
    name: str
    email: str | None = None
    head_id: int | None = None

class DepartmentCreate(DepartmentBase):
    pass

class DepartmentUpdate(BaseModel):
    name: str | None = None
    email: str | None = None
    head_id: int | None = None

class DepartmentOut(DepartmentBase):
    id: int
    categories: list[ComplaintCategoryOut] = []

    class Config:
        from_attributes = True
