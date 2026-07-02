import datetime

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.api import deps
from app.database import get_db
from app.models import (
    Complaint,
    ComplaintAssignment,
    ComplaintCategory,
    ComplaintHistory,
    ComplaintPriority,
    ComplaintStatus,
    User,
    UserRole,
)
from app.schemas.analytics import DepartmentDashboard
from app.schemas.complaint import ComplaintAssignmentCreate, ComplaintDetailOut, ComplaintOut, UserSimpleOut

router = APIRouter()

# Helper to serialize complaint
def serialize_complaint(complaint: Complaint, current_user: User, detail: bool = False) -> dict:
    if detail:
        out = ComplaintDetailOut.model_validate(complaint)
    else:
        out = ComplaintOut.model_validate(complaint)

    if complaint.anonymous:
        if current_user.role not in [UserRole.ADMIN, UserRole.SUPERADMIN]:
            out.student = UserSimpleOut(
                id=0,
                name="Anonymous Student",
                email="anonymous@student.local",
                role="STUDENT"
            )
            out.student_id = 0
    return out

@router.get("/dashboard", response_model=DepartmentDashboard)
def get_department_dashboard(
    db: Session = Depends(get_db),
    current_user: User = Depends(deps.RequireHead)
):
    dept_id = current_user.department_id
    if not dept_id:
        raise HTTPException(status_code=400, detail="Department Head has no associated department")

    # Open complaints (Status is NEW)
    open_count = db.query(func.count(Complaint.id)).filter(
        Complaint.department_id == dept_id,
        Complaint.status == ComplaintStatus.NEW
    ).scalar() or 0

    # In Progress (ASSIGNED, IN_PROGRESS, REOPENED, WAITING_FOR_STUDENT)
    in_progress = db.query(func.count(Complaint.id)).filter(
        Complaint.department_id == dept_id,
        Complaint.status.in_([
            ComplaintStatus.ASSIGNED,
            ComplaintStatus.IN_PROGRESS,
            ComplaintStatus.REOPENED,
            ComplaintStatus.WAITING_FOR_STUDENT
        ])
    ).scalar() or 0

    # Urgent complaints (Priority is URGENT, not resolved or closed)
    urgent = db.query(func.count(Complaint.id)).filter(
        Complaint.department_id == dept_id,
        Complaint.priority == ComplaintPriority.URGENT,
        ~Complaint.status.in_([ComplaintStatus.RESOLVED, ComplaintStatus.CLOSED, ComplaintStatus.REJECTED])
    ).scalar() or 0

    # Overdue complaints (Pending and created > 3 days ago)
    three_days_ago = datetime.datetime.now(datetime.UTC).replace(tzinfo=None) - datetime.timedelta(days=3)
    overdue = db.query(func.count(Complaint.id)).filter(
        Complaint.department_id == dept_id,
        Complaint.created_at < three_days_ago,
        ~Complaint.status.in_([ComplaintStatus.RESOLVED, ComplaintStatus.CLOSED, ComplaintStatus.REJECTED])
    ).scalar() or 0

    # Closed Today (Status resolved or closed and closed_at is today)
    today_start = datetime.datetime.combine(datetime.date.today(), datetime.time.min)
    closed_today = db.query(func.count(Complaint.id)).filter(
        Complaint.department_id == dept_id,
        Complaint.status.in_([ComplaintStatus.RESOLVED, ComplaintStatus.CLOSED]),
        Complaint.closed_at >= today_start
    ).scalar() or 0

    # Staff assigned count (Number of complaints in department currently assigned to staff)
    assigned_count = db.query(func.count(Complaint.id)).filter(
        Complaint.department_id == dept_id,
        Complaint.status == ComplaintStatus.ASSIGNED
    ).scalar() or 0

    return DepartmentDashboard(
        assigned_to_staff_count=assigned_count,
        pending_count=open_count + in_progress,
        urgent_count=urgent,
        overdue_count=overdue,
        closed_today_count=closed_today
    )

@router.get("/complaints", response_model=list[ComplaintOut])
def get_department_complaints(
    status: ComplaintStatus | None = None,
    priority: ComplaintPriority | None = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(deps.RequireHead)
):
    dept_id = current_user.department_id
    if not dept_id:
        raise HTTPException(status_code=400, detail="Department Head has no associated department")

    query = db.query(Complaint).filter(Complaint.department_id == dept_id)

    if status:
        query = query.filter(Complaint.status == status)
    if priority:
        query = query.filter(Complaint.priority == priority)

    complaints = query.order_by(Complaint.created_at.desc()).all()
    return [serialize_complaint(c, current_user) for c in complaints]

@router.get("/statistics")
def get_department_statistics(
    db: Session = Depends(get_db),
    current_user: User = Depends(deps.RequireHead)
):
    dept_id = current_user.department_id
    if not dept_id:
        raise HTTPException(status_code=400, detail="Department Head has no associated department")

    # Category Breakdown
    category_breakdown = db.query(
        ComplaintCategory.name,
        func.count(Complaint.id)
    ).join(Complaint, Complaint.category_id == ComplaintCategory.id).filter(
        Complaint.department_id == dept_id
    ).group_by(ComplaintCategory.name).all()

    # Staff Performance (Total resolved complaints per staff member in department)
    staff_performance = db.query(
        User.name,
        func.count(Complaint.id)
    ).join(ComplaintAssignment, ComplaintAssignment.staff_id == User.id).join(
        Complaint, Complaint.id == ComplaintAssignment.complaint_id
    ).filter(
        User.department_id == dept_id,
        User.role == UserRole.STAFF,
        Complaint.status.in_([ComplaintStatus.RESOLVED, ComplaintStatus.CLOSED])
    ).group_by(User.name).all()

    # Status Breakdown
    status_breakdown = db.query(
        Complaint.status,
        func.count(Complaint.id)
    ).filter(
        Complaint.department_id == dept_id
    ).group_by(Complaint.status).all()

    return {
        "category_breakdown": [{"category": row[0], "count": row[1]} for row in category_breakdown],
        "staff_performance": [{"staff_name": row[0], "resolved_count": row[1]} for row in staff_performance],
        "status_breakdown": {row[0]: row[1] for row in status_breakdown}
    }

@router.post("/assign", response_model=ComplaintOut)
def assign_complaint_head(
    complaint_id: int,
    assignment_data: ComplaintAssignmentCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(deps.RequireHead)
):
    dept_id = current_user.department_id
    complaint = db.query(Complaint).filter(Complaint.id == complaint_id).first()
    if not complaint:
        raise HTTPException(status_code=404, detail="Complaint not found")

    if complaint.department_id != dept_id:
        raise HTTPException(status_code=403, detail="Not authorized to assign complaints outside your department")

    # Verify staff member exists in the same department
    staff_user = db.query(User).filter(
        User.id == assignment_data.staff_id,
        User.role == UserRole.STAFF,
        User.department_id == dept_id,
        User.is_active == True
    ).first()

    if not staff_user:
        raise HTTPException(status_code=400, detail="Staff member not found in this department")

    # Create or update assignment
    assignment = ComplaintAssignment(
        complaint_id=complaint.id,
        staff_id=staff_user.id,
        assigned_by=current_user.id
    )
    db.add(assignment)

    old_status = complaint.status
    complaint.status = ComplaintStatus.ASSIGNED
    db.commit()
    db.refresh(complaint)

    # Audit log
    history = ComplaintHistory(
        complaint_id=complaint.id,
        action=f"Assigned to staff '{staff_user.name}' by Department Head",
        old_status=old_status,
        new_status=ComplaintStatus.ASSIGNED,
        performed_by=current_user.id
    )
    db.add(history)
    db.commit()

    return serialize_complaint(complaint, current_user)

@router.post("/escalate", response_model=ComplaintOut)
def escalate_complaint_head(
    complaint_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(deps.RequireHead)
):
    dept_id = current_user.department_id
    complaint = db.query(Complaint).filter(Complaint.id == complaint_id).first()
    if not complaint:
        raise HTTPException(status_code=404, detail="Complaint not found")

    if complaint.department_id != dept_id:
        raise HTTPException(status_code=403, detail="Not authorized to escalate complaints outside your department")

    if complaint.priority == ComplaintPriority.URGENT:
        raise HTTPException(status_code=400, detail="Complaint is already marked URGENT")

    old_priority = complaint.priority
    complaint.priority = ComplaintPriority.URGENT

    db.commit()
    db.refresh(complaint)

    # Audit log
    history = ComplaintHistory(
        complaint_id=complaint.id,
        action=f"Escalated priority from {old_priority} to URGENT",
        old_status=complaint.status,
        new_status=complaint.status,
        performed_by=current_user.id
    )
    db.add(history)
    db.commit()

    return serialize_complaint(complaint, current_user)
