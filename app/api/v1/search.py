import datetime
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from app.database import get_db
from app.models.user import User, UserRole
from app.models.complaint import Complaint, ComplaintStatus, ComplaintPriority
from app.schemas.complaint import ComplaintOut, UserSimpleOut
from app.api import deps

router = APIRouter()

@router.get("", response_model=list[ComplaintOut])
def search_complaints(
    status: ComplaintStatus | None = None,
    priority: ComplaintPriority | None = None,
    department_id: int | None = None,
    category_id: int | None = None,
    student_id: int | None = None,
    date_from: datetime.date | None = None,
    date_to: datetime.date | None = None,
    ticket_number: str | None = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(deps.get_current_active_user)
):
    query = db.query(Complaint)
    
    # Enforce role-based data boundaries (Students only see their own, Staff/Heads only see their department)
    if current_user.role == UserRole.STUDENT:
        query = query.filter(Complaint.student_id == current_user.id)
    elif current_user.role in [UserRole.STAFF, UserRole.HEAD]:
        query = query.filter(Complaint.department_id == current_user.department_id)
        
    # Apply filters
    if status:
        query = query.filter(Complaint.status == status)
    if priority:
        query = query.filter(Complaint.priority == priority)
        
    if department_id:
        if current_user.role not in [UserRole.ADMIN, UserRole.SUPERADMIN]:
            if department_id != current_user.department_id:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="Not authorized to filter by other departments"
                )
        query = query.filter(Complaint.department_id == department_id)
        
    if category_id:
        query = query.filter(Complaint.category_id == category_id)
        
    if student_id:
        if current_user.role == UserRole.STUDENT:
            if student_id != current_user.id:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="Not authorized to search other students' complaints"
                )
        query = query.filter(Complaint.student_id == student_id)
        
    if date_from:
        dt_from = datetime.datetime.combine(date_from, datetime.time.min)
        query = query.filter(Complaint.created_at >= dt_from)
    if date_to:
        dt_to = datetime.datetime.combine(date_to, datetime.time.max)
        query = query.filter(Complaint.created_at <= dt_to)
        
    if ticket_number:
        query = query.filter(Complaint.ticket_number.ilike(f"%{ticket_number}%"))
        
    complaints = query.order_by(Complaint.created_at.desc()).all()
    
    # Local serializer to handle anonymous masking dynamically
    def serialize(c):
        out = ComplaintOut.model_validate(c)
        if c.anonymous:
            if current_user.role not in [UserRole.ADMIN, UserRole.SUPERADMIN] and current_user.id != c.student_id:
                out.student = UserSimpleOut(
                    id=0,
                    name="Anonymous Student",
                    email="anonymous@student.local",
                    role="STUDENT"
                )
                out.student_id = 0
        return out
        
    return [serialize(c) for c in complaints]
