import os
import shutil

from fastapi import HTTPException, UploadFile, status

from app.core.config import settings


class FileStorageService:
    @staticmethod
    def save_complaint_file(complaint_id: int, file: UploadFile) -> str:
        # Validate file size
        file.file.seek(0, os.SEEK_END)
        file_size = file.file.tell()
        file.file.seek(0)

        max_size_bytes = settings.MAX_UPLOAD_SIZE_MB * 1024 * 1024
        if file_size > max_size_bytes:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"File exceeds maximum allowed size of {settings.MAX_UPLOAD_SIZE_MB}MB"
            )

        # Validate file extension
        allowed_extensions = {".jpg", ".jpeg", ".png", ".pdf", ".doc", ".docx", ".txt", ".xls", ".xlsx", ".csv"}
        _, ext = os.path.splitext(file.filename)
        if ext.lower() not in allowed_extensions:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Extension {ext} is not allowed. Allowed types: {', '.join(allowed_extensions)}"
            )

        # Create complaints subdirectory
        target_dir = os.path.join(settings.UPLOAD_DIR, "complaints", str(complaint_id))
        os.makedirs(target_dir, exist_ok=True)

        # Clean filename to avoid directory traversal
        safe_filename = os.path.basename(file.filename)
        dest_path = os.path.join(target_dir, safe_filename)

        # Save file to local disk
        with open(dest_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)

        return dest_path

    @staticmethod
    def delete_file(file_path: str) -> None:
        if os.path.exists(file_path):
            try:
                os.remove(file_path)
            except Exception:
                pass
