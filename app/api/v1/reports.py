import csv
import datetime
import io

from fastapi import APIRouter, Depends
from fastapi.responses import StreamingResponse
from openpyxl import Workbook
from reportlab.lib import colors
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle
from sqlalchemy.orm import Session

from app.api import deps
from app.database import get_db
from app.models.complaint import Complaint
from app.models.user import User, UserRole

router = APIRouter()

# Enforce access to Management (Head, Admin, SuperAdmin)
dependency_report = Depends(deps.RequireManagement)

def get_report_complaints(db: Session, current_user: User) -> list[Complaint]:
    query = db.query(Complaint)
    if current_user.role == UserRole.HEAD:
        # Department heads only get their department complaints
        query = query.filter(Complaint.department_id == current_user.department_id)
    return query.order_by(Complaint.created_at.desc()).all()

# --- CSV Report Export ---

@router.get("/csv", dependencies=[dependency_report])
def export_csv(
    db: Session = Depends(get_db),
    current_user: User = Depends(deps.get_current_active_user)
):
    complaints = get_report_complaints(db, current_user)

    output = io.StringIO()
    writer = csv.writer(output)

    # Header
    writer.writerow([
        "Ticket Number", "Title", "Description", "Student Name",
        "Department", "Category", "Priority", "Status",
        "Anonymous", "Feedback Rating", "Feedback Comment",
        "Created At", "Closed At"
    ])

    for c in complaints:
        # Mask student details if anonymous and requester is not Admin/SuperAdmin
        student_name = c.student.name if c.student else "Unknown"
        if c.anonymous and current_user.role not in [UserRole.ADMIN, UserRole.SUPERADMIN]:
            student_name = "Anonymous Student"

        writer.writerow([
            c.ticket_number,
            c.title,
            c.description,
            student_name,
            c.department.name if c.department else "N/A",
            c.category.name if c.category else "N/A",
            c.priority,
            c.status,
            "Yes" if c.anonymous else "No",
            c.feedback_rating or "N/A",
            c.feedback_comment or "N/A",
            c.created_at.strftime("%Y-%m-%d %H:%M:%S"),
            c.closed_at.strftime("%Y-%m-%d %H:%M:%S") if c.closed_at else "N/A"
        ])

    output.seek(0)

    filename = f"complaints_report_{datetime.date.today().strftime('%Y%m%d')}.csv"
    headers = {"Content-Disposition": f"attachment; filename={filename}"}
    return StreamingResponse(output, media_type="text/csv", headers=headers)

# --- Excel Report Export ---

@router.get("/excel", dependencies=[dependency_report])
def export_excel(
    db: Session = Depends(get_db),
    current_user: User = Depends(deps.get_current_active_user)
):
    complaints = get_report_complaints(db, current_user)

    wb = Workbook()
    ws = wb.active
    ws.title = "Complaints Report"

    # Header row
    headers = [
        "Ticket Number", "Title", "Description", "Student Name",
        "Department", "Category", "Priority", "Status",
        "Anonymous", "Feedback Rating", "Feedback Comment",
        "Created At", "Closed At"
    ]
    ws.append(headers)

    # Body rows
    for c in complaints:
        student_name = c.student.name if c.student else "Unknown"
        if c.anonymous and current_user.role not in [UserRole.ADMIN, UserRole.SUPERADMIN]:
            student_name = "Anonymous Student"

        ws.append([
            c.ticket_number,
            c.title,
            c.description,
            student_name,
            c.department.name if c.department else "N/A",
            c.category.name if c.category else "N/A",
            c.priority,
            c.status,
            "Yes" if c.anonymous else "No",
            c.feedback_rating or "",
            c.feedback_comment or "",
            c.created_at.strftime("%Y-%m-%d %H:%M:%S") if c.created_at else "",
            c.closed_at.strftime("%Y-%m-%d %H:%M:%S") if c.closed_at else "N/A"
        ])

    # Write to memory buffer
    file_stream = io.BytesIO()
    wb.save(file_stream)
    file_stream.seek(0)

    filename = f"complaints_report_{datetime.date.today().strftime('%Y%m%d')}.xlsx"
    res_headers = {"Content-Disposition": f"attachment; filename={filename}"}
    return StreamingResponse(
        file_stream,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers=res_headers
    )

# --- PDF Report Export ---

@router.get("/pdf", dependencies=[dependency_report])
def export_pdf(
    db: Session = Depends(get_db),
    current_user: User = Depends(deps.get_current_active_user)
):
    complaints = get_report_complaints(db, current_user)

    buffer = io.BytesIO()
    doc = SimpleDocTemplate(
        buffer,
        pagesize=letter,
        rightMargin=30,
        leftMargin=30,
        topMargin=30,
        bottomMargin=30
    )

    styles = getSampleStyleSheet()
    title_style = ParagraphStyle(
        'ReportTitle',
        parent=styles['Heading1'],
        textColor=colors.HexColor('#1A365D'),
        spaceAfter=15
    )
    normal_style = styles['Normal']
    header_style = ParagraphStyle(
        'HeaderStyle',
        parent=styles['Normal'],
        textColor=colors.white,
        fontName='Helvetica-Bold'
    )

    elements = []

    # Document Title
    elements.append(Paragraph("Student Complaint Management System - Reports", title_style))
    elements.append(Paragraph(f"Generated On: {datetime.date.today().strftime('%Y-%m-%d')}", normal_style))
    elements.append(Paragraph(f"Generated By: {current_user.name} ({current_user.role})", normal_style))
    elements.append(Spacer(1, 20))

    # Table headers & widths
    table_data = [[
        Paragraph("Ticket #", header_style),
        Paragraph("Title", header_style),
        Paragraph("Dept/Cat", header_style),
        Paragraph("Priority", header_style),
        Paragraph("Status", header_style),
        Paragraph("Created At", header_style)
    ]]

    # Limit to 50 entries in PDF to prevent buffer blowout on large datasets
    for c in complaints[:50]:
        dept_cat_text = f"{c.department.name[:12] if c.department else 'N/A'}\n/ {c.category.name[:12] if c.category else 'N/A'}"
        table_data.append([
            Paragraph(c.ticket_number, normal_style),
            Paragraph(c.title[:25] + ('...' if len(c.title) > 25 else ''), normal_style),
            Paragraph(dept_cat_text, normal_style),
            Paragraph(c.priority, normal_style),
            Paragraph(c.status, normal_style),
            Paragraph(c.created_at.strftime("%Y-%m-%d"), normal_style)
        ])

    # Build Table
    # Col widths: Ticket, Title, Dept/Cat, Priority, Status, Created At
    col_widths = [110, 140, 120, 55, 65, 60]
    t = Table(table_data, colWidths=col_widths)
    t.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#1A365D')),
        ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
        ('BOTTOMPADDING', (0, 0), (-1, 0), 8),
        ('TOPPADDING', (0, 0), (-1, 0), 8),
        ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
        ('VALIGN', (0, 0), (-1, -1), 'TOP'),
        ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.HexColor('#F7FAFC')]),
        ('FONTSIZE', (0, 0), (-1, -1), 8),
    ]))

    elements.append(t)
    doc.build(elements)

    buffer.seek(0)

    filename = f"complaints_report_{datetime.date.today().strftime('%Y%m%d')}.pdf"
    res_headers = {"Content-Disposition": f"attachment; filename={filename}"}
    return StreamingResponse(buffer, media_type="application/pdf", headers=res_headers)
