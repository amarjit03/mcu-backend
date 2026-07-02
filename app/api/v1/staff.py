import datetime

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.api import deps
from app.database import get_db
from app.models import (
    Complaint,
    ComplaintAssignment,
    ComplaintComment,
    ComplaintHistory,
    ComplaintStatus,
    User,
    UserRole,
)
from app.schemas.complaint import (
    ComplaintAssignmentCreate,
    ComplaintCommentCreate,
    ComplaintCommentOut,
    ComplaintDetailOut,
    ComplaintOut,
    ComplaintStatusUpdate,
    UserSimpleOut,
)

router = APIRouter()

# Helper to serialize complaint and mask student if anonymous
def serialize_complaint(complaint: Complaint, current_user: User, detail: bool = False) -> dict:
    if detail:
        out = ComplaintDetailOut.model_validate(complaint)
    else:
        out = ComplaintOut.model_validate(complaint)

    if complaint.anonymous:
        # Mask student details for staff and department head
        if current_user.role not in [UserRole.ADMIN, UserRole.SUPERADMIN] and current_user.id != complaint.student_id:
            out.student = UserSimpleOut(
                id=0,
                name="Anonymous Student",
                email="anonymous@student.local",
                role="STUDENT"
            )
            out.student_id = 0
    return out

@router.get("/complaints", response_model=list[ComplaintOut])
def get_assigned_complaints(
    status: ComplaintStatus | None = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(deps.RequireStaff)
):
    # Staff can see complaints assigned to them OR unassigned complaints in their department
    query = db.query(Complaint).filter(Complaint.department_id == current_user.department_id)

    # Filter by status if requested
    if status:
        query = query.filter(Complaint.status == status)

    # Get complaints assigned to this staff member OR currently NEW/unassigned
    complaints = query.outerjoin(ComplaintAssignment).filter(
        (ComplaintAssignment.staff_id == current_user.id) | (Complaint.status == ComplaintStatus.NEW)
    ).order_by(Complaint.updated_at.desc()).all()

    return [serialize_complaint(c, current_user) for c in complaints]

@router.post("/complaints/{id}/accept", response_model=ComplaintOut)
def accept_complaint(
    id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(deps.RequireStaff)
):
    complaint = db.query(Complaint).filter(Complaint.id == id).first()
    if not complaint:
        raise HTTPException(status_code=404, detail="Complaint not found")

    if complaint.department_id != current_user.department_id:
        raise HTTPException(
            status_code=403,
            detail="Complaint does not belong to your department"
        )

    if complaint.status not in [ComplaintStatus.NEW, ComplaintStatus.ASSIGNED, ComplaintStatus.REOPENED]:
        raise HTTPException(
            status_code=400,
            detail="Complaint is already in progress, resolved, or closed"
        )

    old_status = complaint.status
    complaint.status = ComplaintStatus.IN_PROGRESS

    # Check if there is an existing assignment
    existing_assignment = db.query(ComplaintAssignment).filter(
        ComplaintAssignment.complaint_id == id,
        ComplaintAssignment.staff_id == current_user.id
    ).first()

    if not existing_assignment:
        assignment = ComplaintAssignment(
            complaint_id=id,
            staff_id=current_user.id,
            assigned_by=current_user.id
        )
        db.add(assignment)

    db.commit()
    db.refresh(complaint)

    # Audit log
    history = ComplaintHistory(
        complaint_id=id,
        action="Complaint Accepted by Staff",
        old_status=old_status,
        new_status=ComplaintStatus.IN_PROGRESS,
        performed_by=current_user.id
    )
    db.add(history)
    db.commit()

    return serialize_complaint(complaint, current_user)

@router.patch("/complaints/{id}/status", response_model=ComplaintOut)
def update_complaint_status(
    id: int,
    status_update: ComplaintStatusUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(deps.RequireStaff)
):
    complaint = db.query(Complaint).filter(Complaint.id == id).first()
    if not complaint:
        raise HTTPException(status_code=404, detail="Complaint not found")

    if complaint.department_id != current_user.department_id:
        raise HTTPException(status_code=403, detail="Not authorized to modify complaints outside your department")

    # Check if staff is assigned to this complaint
    is_assigned = db.query(ComplaintAssignment).filter(
        ComplaintAssignment.complaint_id == id,
        ComplaintAssignment.staff_id == current_user.id
    ).first()

    # Staff must be assigned, or it must be in progress
    if not is_assigned and complaint.status != ComplaintStatus.NEW:
         raise HTTPException(status_code=403, detail="You must be assigned to this complaint to update its status")

    old_status = complaint.status
    new_status = status_update.status

    # Basic state transition checks
    if new_status == ComplaintStatus.CLOSED:
        raise HTTPException(status_code=400, detail="Only students can close complaints (via feedback/verification)")

    complaint.status = new_status
    if new_status == ComplaintStatus.RESOLVED:
        complaint.closed_at = datetime.datetime.now(datetime.UTC)

    db.commit()
    db.refresh(complaint)

    # Audit log
    history = ComplaintHistory(
        complaint_id=id,
        action=f"Status updated to {new_status}",
        old_status=old_status,
        new_status=new_status,
        performed_by=current_user.id
    )
    db.add(history)
    db.commit()

    return serialize_complaint(complaint, current_user)

@router.post("/complaints/{id}/assign", response_model=ComplaintOut)
def assign_staff_member(
    id: int,
    assignment_data: ComplaintAssignmentCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(deps.RequireStaff)
):
    complaint = db.query(Complaint).filter(Complaint.id == id).first()
    if not complaint:
        raise HTTPException(status_code=404, detail="Complaint not found")

    if complaint.department_id != current_user.department_id:
        raise HTTPException(status_code=403, detail="Not authorized to assign complaints outside your department")

    # Check if target staff exists in the same department
    target_staff = db.query(User).filter(
        User.id == assignment_data.staff_id,
        User.role == UserRole.STAFF,
        User.department_id == current_user.department_id,
        User.is_active == True
    ).first()

    if not target_staff:
        raise HTTPException(
            status_code=400,
            detail="Target staff member not found in your department"
        )

    # Create assignment
    assignment = ComplaintAssignment(
        complaint_id=id,
        staff_id=target_staff.id,
        assigned_by=current_user.id
    )
    db.add(assignment)

    old_status = complaint.status
    complaint.status = ComplaintStatus.ASSIGNED
    db.commit()
    db.refresh(complaint)

    # Audit log
    history = ComplaintHistory(
        complaint_id=id,
        action=f"Assigned to staff: {target_staff.name}",
        old_status=old_status,
        new_status=ComplaintStatus.ASSIGNED,
        performed_by=current_user.id
    )
    db.add(history)
    db.commit()

    return serialize_complaint(complaint, current_user)

@router.post("/complaints/{id}/internal-note", response_model=ComplaintCommentOut, status_code=status.HTTP_201_CREATED)
def post_internal_note(
    id: int,
    note_data: ComplaintCommentCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(deps.RequireStaff)
):
    complaint = db.query(Complaint).filter(Complaint.id == id).first()
    if not complaint:
        raise HTTPException(status_code=404, detail="Complaint not found")

    if complaint.department_id != current_user.department_id:
         raise HTTPException(status_code=403, detail="Not authorized to comment on complaints outside your department")

    comment = ComplaintComment(
        complaint_id=id,
        user_id=current_user.id,
        message=note_data.message,
        internal_note=True
    )
    db.add(comment)
    db.commit()
    db.refresh(comment)

    # Audit log
    history = ComplaintHistory(
        complaint_id=id,
        action="Internal Note Added by Staff",
        old_status=complaint.status,
        new_status=complaint.status,
        performed_by=current_user.id
    )
    db.add(history)
    db.commit()

    return comment

@router.post("/complaints/{id}/resolve", response_model=ComplaintOut)
def resolve_complaint(
    id: int,
    resolution_data: ComplaintCommentCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(deps.RequireStaff)
):
    complaint = db.query(Complaint).filter(Complaint.id == id).first()
    if not complaint:
        raise HTTPException(status_code=404, detail="Complaint not found")

    if complaint.department_id != current_user.department_id:
         raise HTTPException(status_code=403, detail="Not authorized to resolve complaints outside your department")

    # Update status to RESOLVED
    old_status = complaint.status
    complaint.status = ComplaintStatus.RESOLVED
    complaint.closed_at = datetime.datetime.now(datetime.UTC)

    # Record resolution message as a public comment
    comment = ComplaintComment(
        complaint_id=id,
        user_id=current_user.id,
        message=f"RESOLUTION: {resolution_data.message}",
        internal_note=False
    )
    db.add(comment)
    db.commit()
    db.refresh(complaint)

    # Audit log
    history = ComplaintHistory(
        complaint_id=id,
        action="Complaint Resolved with Message",
        old_status=old_status,
        new_status=ComplaintStatus.RESOLVED,
        performed_by=current_user.id
    )
    db.add(history)
    db.commit()

    return serialize_complaint(complaint, current_user)
