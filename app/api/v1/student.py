import datetime
import os
from fastapi import APIRouter, Depends, HTTPException, status, UploadFile, File
from sqlalchemy.orm import Session
from sqlalchemy import func
from app.database import get_db
from app.models import User, UserRole, Complaint, ComplaintFile, ComplaintComment, ComplaintStatus, ComplaintPriority, ComplaintHistory
from app.schemas.user import UserOut, UserUpdateMe
from app.schemas.complaint import (
    ComplaintCreate,
    ComplaintUpdate,
    ComplaintOut,
    ComplaintDetailOut,
    ComplaintCommentCreate,
    ComplaintCommentOut,
    ComplaintFileOut,
    ComplaintFeedbackCreate,
    UserSimpleOut,
)
from app.schemas.analytics import StudentDashboard
from app.api import deps
from app.core import security
from app.services.file_storage import FileStorageService

router = APIRouter()

# Helper to mask anonymous student and filter internal comments
def serialize_complaint(complaint: Complaint, current_user: User, detail: bool = False) -> dict:
    if detail:
        out = ComplaintDetailOut.model_validate(complaint)
    else:
        out = ComplaintOut.model_validate(complaint)
        
    # Mask student if anonymous and requestor is not the author or an admin
    if complaint.anonymous:
        if current_user.id != complaint.student_id and current_user.role not in [UserRole.ADMIN, UserRole.SUPERADMIN]:
            out.student = UserSimpleOut(
                id=0,
                name="Anonymous Student",
                email="anonymous@student.local",
                role="STUDENT"
            )
            out.student_id = 0
            
    # Hide internal notes if the user is a student
    if current_user.role == UserRole.STUDENT and detail:
        out.comments = [c for c in out.comments if not c.internal_note]
        
    return out

# --- Profile Endpoints ---

@router.get("/profile", response_model=UserOut)
def get_student_profile(current_user: User = Depends(deps.RequireStudent)):
    return current_user

@router.patch("/profile", response_model=UserOut)
def update_student_profile(
    profile_data: UserUpdateMe,
    db: Session = Depends(get_db),
    current_user: User = Depends(deps.RequireStudent),
):
    if profile_data.name is not None:
        current_user.name = profile_data.name
    if profile_data.phone is not None:
        current_user.phone = profile_data.phone
    if profile_data.email is not None:
        # Check if email is already taken by another user
        existing_user = db.query(User).filter(User.email == profile_data.email, User.id != current_user.id).first()
        if existing_user:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Email already registered"
            )
        current_user.email = profile_data.email
    if profile_data.password is not None:
        if len(profile_data.password) < 6:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Password must be at least 6 characters"
            )
        current_user.password_hash = security.get_password_hash(profile_data.password)
        
    db.commit()
    db.refresh(current_user)
    return current_user

# --- Dashboard Endpoint ---

@router.get("/dashboard", response_model=StudentDashboard)
def get_student_dashboard(
    db: Session = Depends(get_db),
    current_user: User = Depends(deps.RequireStudent)
):
    # Total complaints
    total = db.query(func.count(Complaint.id)).filter(Complaint.student_id == current_user.id).scalar()
    
    # Pending
    pending = db.query(func.count(Complaint.id)).filter(
        Complaint.student_id == current_user.id,
        Complaint.status.in_([
            ComplaintStatus.NEW,
            ComplaintStatus.ASSIGNED,
            ComplaintStatus.IN_PROGRESS,
            ComplaintStatus.WAITING_FOR_STUDENT,
            ComplaintStatus.REOPENED,
        ])
    ).scalar()
    
    # Resolved
    resolved = db.query(func.count(Complaint.id)).filter(
        Complaint.student_id == current_user.id,
        Complaint.status == ComplaintStatus.RESOLVED
    ).scalar()
    
    # Closed
    closed = db.query(func.count(Complaint.id)).filter(
        Complaint.student_id == current_user.id,
        Complaint.status == ComplaintStatus.CLOSED
    ).scalar()
    
    # Average resolution time
    closed_complaints = db.query(Complaint).filter(
        Complaint.student_id == current_user.id,
        Complaint.status == ComplaintStatus.CLOSED,
        Complaint.closed_at.isnot(None)
    ).all()
    
    total_hours = 0
    closed_count = len(closed_complaints)
    for c in closed_complaints:
        delta = c.closed_at - c.created_at
        total_hours += delta.total_seconds() / 3600.0
        
    avg_time = (total_hours / closed_count) if closed_count > 0 else None
    
    return StudentDashboard(
        total_complaints=total or 0,
        pending_complaints=pending or 0,
        resolved_complaints=resolved or 0,
        closed_complaints=closed or 0,
        average_resolution_time_hours=avg_time,
    )

# --- Complaint Endpoints ---

@router.post("/complaints", response_model=ComplaintOut, status_code=status.HTTP_201_CREATED)
def create_complaint(
    complaint_data: ComplaintCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(deps.RequireStudent)
):
    # Generate unique ticket number: COMP-YYYYMMDD-XXXX
    today_str = datetime.date.today().strftime("%Y%m%d")
    today_start = datetime.datetime.combine(datetime.date.today(), datetime.time.min)
    today_end = datetime.datetime.combine(datetime.date.today(), datetime.time.max)
    
    daily_count = db.query(func.count(Complaint.id)).filter(
        Complaint.created_at >= today_start,
        Complaint.created_at <= today_end
    ).scalar() or 0
    
    ticket_num = f"COMP-{today_str}-{(daily_count + 1):04d}"
    
    complaint = Complaint(
        ticket_number=ticket_num,
        title=complaint_data.title,
        description=complaint_data.description,
        student_id=current_user.id,
        category_id=complaint_data.category_id,
        department_id=complaint_data.department_id,
        priority=complaint_data.priority,
        status=ComplaintStatus.NEW,
        anonymous=complaint_data.anonymous,
    )
    db.add(complaint)
    db.commit()
    db.refresh(complaint)
    
    # Audit log
    history = ComplaintHistory(
        complaint_id=complaint.id,
        action="Complaint Created",
        old_status=None,
        new_status=ComplaintStatus.NEW,
        performed_by=current_user.id,
    )
    db.add(history)
    db.commit()
    
    return serialize_complaint(complaint, current_user)

@router.get("/complaints", response_model=list[ComplaintOut])
def get_my_complaints(
    skip: int = 0,
    limit: int = 100,
    status: ComplaintStatus | None = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(deps.RequireStudent)
):
    query = db.query(Complaint).filter(Complaint.student_id == current_user.id)
    if status:
        query = query.filter(Complaint.status == status)
    complaints = query.order_by(Complaint.created_at.desc()).offset(skip).limit(limit).all()
    return [serialize_complaint(c, current_user) for c in complaints]

@router.get("/complaints/{id}", response_model=ComplaintDetailOut)
def get_complaint_by_id(
    id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(deps.get_current_active_user)
):
    complaint = db.query(Complaint).filter(Complaint.id == id).first()
    if not complaint:
        raise HTTPException(status_code=404, detail="Complaint not found")
        
    # Students can only view their own complaints
    if current_user.role == UserRole.STUDENT and complaint.student_id != current_user.id:
        raise HTTPException(status_code=403, detail="Not authorized to view this complaint")
        
    return serialize_complaint(complaint, current_user, detail=True)

@router.patch("/complaints/{id}", response_model=ComplaintOut)
def update_complaint(
    id: int,
    complaint_data: ComplaintUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(deps.RequireStudent)
):
    complaint = db.query(Complaint).filter(Complaint.id == id).first()
    if not complaint:
        raise HTTPException(status_code=404, detail="Complaint not found")
    if complaint.student_id != current_user.id:
        raise HTTPException(status_code=403, detail="Not authorized to update this complaint")
    if complaint.status != ComplaintStatus.NEW:
        raise HTTPException(
            status_code=400,
            detail="Complaint can only be updated while in 'NEW' status"
        )
        
    # Apply updates
    for field, value in complaint_data.model_dump(exclude_unset=True).items():
        setattr(complaint, field, value)
        
    db.commit()
    db.refresh(complaint)
    
    # Audit log
    history = ComplaintHistory(
        complaint_id=complaint.id,
        action="Complaint Details Updated",
        old_status=complaint.status,
        new_status=complaint.status,
        performed_by=current_user.id,
    )
    db.add(history)
    db.commit()
    
    return serialize_complaint(complaint, current_user)

@router.delete("/complaints/{id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_complaint(
    id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(deps.RequireStudent)
):
    complaint = db.query(Complaint).filter(Complaint.id == id).first()
    if not complaint:
        raise HTTPException(status_code=404, detail="Complaint not found")
    if complaint.student_id != current_user.id:
        raise HTTPException(status_code=403, detail="Not authorized to delete this complaint")
    if complaint.status != ComplaintStatus.NEW:
        raise HTTPException(
            status_code=400,
            detail="Complaint can only be deleted while in 'NEW' status"
        )
        
    # Delete uploaded files first
    for f in complaint.files:
        FileStorageService.delete_file(f.file_path)
        
    db.delete(complaint)
    db.commit()
    return

# --- File Upload Endpoints ---

@router.post("/complaints/{id}/files", response_model=ComplaintFileOut, status_code=status.HTTP_201_CREATED)
def upload_file_to_complaint(
    id: int,
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(deps.RequireStudent)
):
    complaint = db.query(Complaint).filter(Complaint.id == id).first()
    if not complaint:
        raise HTTPException(status_code=404, detail="Complaint not found")
    if complaint.student_id != current_user.id:
        raise HTTPException(status_code=403, detail="Not authorized to upload files for this complaint")
    # File upload is allowed while complaint is in NEW, REOPENED or IN_PROGRESS
    if complaint.status not in [ComplaintStatus.NEW, ComplaintStatus.IN_PROGRESS, ComplaintStatus.REOPENED]:
        raise HTTPException(
            status_code=400,
            detail="Cannot upload files to resolved or closed complaints"
        )
        
    file_path = FileStorageService.save_complaint_file(id, file)
    
    complaint_file = ComplaintFile(
        complaint_id=id,
        file_path=file_path,
        uploaded_by=current_user.id
    )
    db.add(complaint_file)
    db.commit()
    db.refresh(complaint_file)
    
    # Audit log
    history = ComplaintHistory(
        complaint_id=id,
        action=f"File uploaded: {os.path.basename(file.filename)}",
        old_status=complaint.status,
        new_status=complaint.status,
        performed_by=current_user.id,
    )
    db.add(history)
    db.commit()
    
    return complaint_file

@router.delete("/complaints/files/{file_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_complaint_file(
    file_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(deps.RequireStudent)
):
    comp_file = db.query(ComplaintFile).filter(ComplaintFile.id == file_id).first()
    if not comp_file:
        raise HTTPException(status_code=404, detail="File record not found")
        
    complaint = comp_file.complaint
    if complaint.student_id != current_user.id:
        raise HTTPException(status_code=403, detail="Not authorized to delete files from this complaint")
    if complaint.status not in [ComplaintStatus.NEW, ComplaintStatus.IN_PROGRESS, ComplaintStatus.REOPENED]:
        raise HTTPException(status_code=400, detail="Cannot delete files of resolved/closed complaints")
        
    FileStorageService.delete_file(comp_file.file_path)
    
    db.delete(comp_file)
    db.commit()
    return

# --- Comment Endpoints ---

@router.post("/complaints/{id}/comments", response_model=ComplaintCommentOut, status_code=status.HTTP_201_CREATED)
def post_comment_on_complaint(
    id: int,
    comment_data: ComplaintCommentCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(deps.RequireStudent)
):
    complaint = db.query(Complaint).filter(Complaint.id == id).first()
    if not complaint:
        raise HTTPException(status_code=404, detail="Complaint not found")
    if complaint.student_id != current_user.id:
        raise HTTPException(status_code=403, detail="Not authorized to comment on this complaint")
        
    comment = ComplaintComment(
        complaint_id=id,
        user_id=current_user.id,
        message=comment_data.message,
        internal_note=False
    )
    db.add(comment)
    db.commit()
    db.refresh(comment)
    
    # Audit log
    history = ComplaintHistory(
        complaint_id=id,
        action="Comment Added by Student",
        old_status=complaint.status,
        new_status=complaint.status,
        performed_by=current_user.id,
    )
    db.add(history)
    db.commit()
    
    return comment

@router.get("/complaints/{id}/comments", response_model=list[ComplaintCommentOut])
def get_complaint_comments(
    id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(deps.get_current_active_user)
):
    complaint = db.query(Complaint).filter(Complaint.id == id).first()
    if not complaint:
        raise HTTPException(status_code=404, detail="Complaint not found")
    if current_user.role == UserRole.STUDENT and complaint.student_id != current_user.id:
        raise HTTPException(status_code=403, detail="Not authorized to view comments on this complaint")
        
    query = db.query(ComplaintComment).filter(ComplaintComment.complaint_id == id)
    # Hide internal notes from students
    if current_user.role == UserRole.STUDENT:
        query = query.filter(ComplaintComment.internal_note == False)
        
    return query.order_by(ComplaintComment.created_at.asc()).all()

# --- Reopen & Feedback Endpoints ---

@router.post("/complaints/{id}/reopen", response_model=ComplaintOut)
def reopen_complaint(
    id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(deps.RequireStudent)
):
    complaint = db.query(Complaint).filter(Complaint.id == id).first()
    if not complaint:
        raise HTTPException(status_code=404, detail="Complaint not found")
    if complaint.student_id != current_user.id:
        raise HTTPException(status_code=403, detail="Not authorized to reopen this complaint")
        
    if complaint.status not in [ComplaintStatus.RESOLVED, ComplaintStatus.CLOSED]:
        raise HTTPException(
            status_code=400,
            detail="Complaint can only be reopened if status is 'RESOLVED' or 'CLOSED'"
        )
        
    old_status = complaint.status
    complaint.status = ComplaintStatus.REOPENED
    complaint.closed_at = None
    db.commit()
    db.refresh(complaint)
    
    # Audit log
    history = ComplaintHistory(
        complaint_id=id,
        action="Complaint Reopened",
        old_status=old_status,
        new_status=ComplaintStatus.REOPENED,
        performed_by=current_user.id,
    )
    db.add(history)
    db.commit()
    
    return serialize_complaint(complaint, current_user)

@router.post("/complaints/{id}/feedback", response_model=ComplaintOut)
def submit_complaint_feedback(
    id: int,
    feedback: ComplaintFeedbackCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(deps.RequireStudent)
):
    complaint = db.query(Complaint).filter(Complaint.id == id).first()
    if not complaint:
        raise HTTPException(status_code=404, detail="Complaint not found")
    if complaint.student_id != current_user.id:
        raise HTTPException(status_code=403, detail="Not authorized to provide feedback on this complaint")
        
    # Feedback is allowed on resolved or closed complaints
    if complaint.status not in [ComplaintStatus.RESOLVED, ComplaintStatus.CLOSED]:
        raise HTTPException(
            status_code=400,
            detail="Feedback can only be submitted after the complaint is RESOLVED or CLOSED"
        )
        
    complaint.feedback_rating = feedback.rating
    complaint.feedback_comment = feedback.comment
    
    old_status = complaint.status
    # Automatically move RESOLVED -> CLOSED upon feedback
    if complaint.status == ComplaintStatus.RESOLVED:
        complaint.status = ComplaintStatus.CLOSED
        complaint.closed_at = datetime.datetime.now(datetime.timezone.utc)
        
    db.commit()
    db.refresh(complaint)
    
    # Audit log
    history = ComplaintHistory(
        complaint_id=id,
        action=f"Feedback submitted: Rating={feedback.rating}",
        old_status=old_status,
        new_status=complaint.status,
        performed_by=current_user.id,
    )
    db.add(history)
    db.commit()
    
    return serialize_complaint(complaint, current_user)
