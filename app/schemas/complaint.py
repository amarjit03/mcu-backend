from datetime import datetime
from pydantic import BaseModel, Field
from app.models.complaint import ComplaintPriority, ComplaintStatus

class ComplaintCategorySimpleOut(BaseModel):
    id: int
    name: str
    
    class Config:
        from_attributes = True

class DepartmentSimpleOut(BaseModel):
    id: int
    name: str
    
    class Config:
        from_attributes = True

class UserSimpleOut(BaseModel):
    id: int
    name: str
    email: str
    role: str
    
    class Config:
        from_attributes = True

class ComplaintFileOut(BaseModel):
    id: int
    complaint_id: int
    file_path: str
    uploaded_by: int
    created_at: datetime
    
    class Config:
        from_attributes = True

class ComplaintCommentCreate(BaseModel):
    message: str

class ComplaintCommentOut(BaseModel):
    id: int
    complaint_id: int
    user_id: int
    message: str
    internal_note: bool
    created_at: datetime
    user: UserSimpleOut

    class Config:
        from_attributes = True

class ComplaintHistoryOut(BaseModel):
    id: int
    complaint_id: int
    action: str
    old_status: str | None = None
    new_status: str | None = None
    performed_by: int
    created_at: datetime
    performer: UserSimpleOut

    class Config:
        from_attributes = True

class ComplaintAssignmentOut(BaseModel):
    id: int
    complaint_id: int
    staff_id: int
    assigned_by: int
    assigned_at: datetime
    staff: UserSimpleOut
    assigner: UserSimpleOut

    class Config:
        from_attributes = True

class ComplaintCreate(BaseModel):
    title: str
    description: str
    category_id: int
    department_id: int
    priority: ComplaintPriority = ComplaintPriority.MEDIUM
    anonymous: bool = False

class ComplaintUpdate(BaseModel):
    title: str | None = None
    description: str | None = None
    category_id: int | None = None
    department_id: int | None = None
    priority: ComplaintPriority | None = None
    anonymous: bool | None = None

class ComplaintFeedbackCreate(BaseModel):
    rating: int = Field(..., ge=1, le=5)
    comment: str | None = None

class ComplaintAssignmentCreate(BaseModel):
    staff_id: int

class ComplaintStatusUpdate(BaseModel):
    status: ComplaintStatus

class ComplaintOut(BaseModel):
    id: int
    ticket_number: str
    title: str
    description: str
    student_id: int
    student: UserSimpleOut | None = None  # Will be dynamically masked/handled in API routers
    category_id: int
    category: ComplaintCategorySimpleOut
    department_id: int
    department: DepartmentSimpleOut
    priority: str
    status: str
    anonymous: bool
    feedback_rating: int | None = None
    feedback_comment: str | None = None
    created_at: datetime
    updated_at: datetime
    closed_at: datetime | None = None
    files: list[ComplaintFileOut] = []
    assignments: list[ComplaintAssignmentOut] = []

    class Config:
        from_attributes = True
        
class ComplaintDetailOut(ComplaintOut):
    comments: list[ComplaintCommentOut] = []
    history: list[ComplaintHistoryOut] = []
