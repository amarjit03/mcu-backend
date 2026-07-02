import os
from fastapi import APIRouter, Depends, HTTPException, status, UploadFile, File
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session
from app.database import get_db
from app.models.user import User, UserRole
from app.models.complaint import ComplaintFile, Complaint
from app.api import deps
from app.services.file_storage import FileStorageService

router = APIRouter()

@router.post("/upload", response_model=dict, status_code=status.HTTP_201_CREATED)
def upload_generic_file(
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(deps.get_current_active_user)
):
    # Save file under a special generic complaint ID folder '0'
    file_path = FileStorageService.save_complaint_file(0, file)
    
    # Save to database record
    db_file = ComplaintFile(
        complaint_id=0,  # 0 indicates unlinked generic file upload
        file_path=file_path,
        uploaded_by=current_user.id
    )
    db.add(db_file)
    db.commit()
    db.refresh(db_file)
    
    return {
        "id": db_file.id, 
        "file_path": db_file.file_path, 
        "filename": os.path.basename(file_path)
    }

@router.get("/files/{id}")
def get_file_by_id(
    id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(deps.get_current_active_user)
):
    comp_file = db.query(ComplaintFile).filter(ComplaintFile.id == id).first()
    if not comp_file:
        raise HTTPException(status_code=404, detail="File not found")
        
    # Check permissions: if linked to a complaint, students can only fetch files belonging to their complaints
    if comp_file.complaint_id != 0:
        complaint = db.query(Complaint).filter(Complaint.id == comp_file.complaint_id).first()
        if complaint and current_user.role == UserRole.STUDENT and complaint.student_id != current_user.id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Not authorized to access this file"
            )
            
    if not os.path.exists(comp_file.file_path):
        raise HTTPException(status_code=404, detail="File content not found on server disk")
        
    return FileResponse(comp_file.file_path)

@router.delete("/files/{id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_file_by_id(
    id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(deps.get_current_active_user)
):
    comp_file = db.query(ComplaintFile).filter(ComplaintFile.id == id).first()
    if not comp_file:
        raise HTTPException(status_code=404, detail="File not found")
        
    # Only uploader or Admin can delete files
    if comp_file.uploaded_by != current_user.id and current_user.role not in [UserRole.ADMIN, UserRole.SUPERADMIN]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized to delete this file"
        )
        
    FileStorageService.delete_file(comp_file.file_path)
    db.delete(comp_file)
    db.commit()
    return
