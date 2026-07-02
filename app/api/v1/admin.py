import datetime
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from sqlalchemy import func, extract
from app.database import get_db
from app.models import User, UserRole, Department, ComplaintCategory, Complaint, ComplaintStatus, ComplaintPriority, ComplaintHistory
from app.schemas.user import UserCreate, UserUpdate, UserOut
from app.schemas.department import (
    DepartmentCreate, DepartmentUpdate, DepartmentOut,
    ComplaintCategoryCreate, ComplaintCategoryUpdate, ComplaintCategoryOut
)
from app.schemas.complaint import ComplaintOut, ComplaintDetailOut, ComplaintUpdate
from app.schemas.analytics import AdminDashboard, DepartmentPerformance, CategoryBreakdown, MonthlyTrend
from app.api import deps
from app.core import security

router = APIRouter()

# Enforce Admin role globally for this router
dependency_admin = Depends(deps.RequireAdmin)

# --- Department CRUD ---

@router.get("/departments", response_model=list[DepartmentOut], dependencies=[dependency_admin])
def list_departments(db: Session = Depends(get_db)):
    return db.query(Department).all()

@router.post("/departments", response_model=DepartmentOut, status_code=status.HTTP_201_CREATED, dependencies=[dependency_admin])
def create_department(dept: DepartmentCreate, db: Session = Depends(get_db)):
    # Check uniqueness
    existing = db.query(Department).filter(Department.name == dept.name).first()
    if existing:
        raise HTTPException(status_code=400, detail="Department with this name already exists")
    db_dept = Department(name=dept.name, email=dept.email, head_id=dept.head_id)
    db.add(db_dept)
    db.commit()
    db.refresh(db_dept)
    return db_dept

@router.patch("/departments/{id}", response_model=DepartmentOut, dependencies=[dependency_admin])
def update_department(id: int, dept_data: DepartmentUpdate, db: Session = Depends(get_db)):
    db_dept = db.query(Department).filter(Department.id == id).first()
    if not db_dept:
        raise HTTPException(status_code=404, detail="Department not found")
    for key, value in dept_data.model_dump(exclude_unset=True).items():
        setattr(db_dept, key, value)
    db.commit()
    db.refresh(db_dept)
    return db_dept

@router.delete("/departments/{id}", status_code=status.HTTP_204_NO_CONTENT, dependencies=[dependency_admin])
def delete_department(id: int, db: Session = Depends(get_db)):
    db_dept = db.query(Department).filter(Department.id == id).first()
    if not db_dept:
        raise HTTPException(status_code=404, detail="Department not found")
    db.delete(db_dept)
    db.commit()
    return

# --- Category CRUD ---

@router.get("/categories", response_model=list[ComplaintCategoryOut], dependencies=[dependency_admin])
def list_categories(db: Session = Depends(get_db)):
    return db.query(ComplaintCategory).all()

@router.post("/categories", response_model=ComplaintCategoryOut, status_code=status.HTTP_201_CREATED, dependencies=[dependency_admin])
def create_category(cat: ComplaintCategoryCreate, db: Session = Depends(get_db)):
    # Verify department exists
    dept = db.query(Department).filter(Department.id == cat.department_id).first()
    if not dept:
        raise HTTPException(status_code=400, detail="Department not found")
    db_cat = ComplaintCategory(name=cat.name, department_id=cat.department_id)
    db.add(db_cat)
    db.commit()
    db.refresh(db_cat)
    return db_cat

@router.patch("/categories/{id}", response_model=ComplaintCategoryOut, dependencies=[dependency_admin])
def update_category(id: int, cat_data: ComplaintCategoryUpdate, db: Session = Depends(get_db)):
    db_cat = db.query(ComplaintCategory).filter(ComplaintCategory.id == id).first()
    if not db_cat:
        raise HTTPException(status_code=404, detail="Category not found")
    for key, value in cat_data.model_dump(exclude_unset=True).items():
        setattr(db_cat, key, value)
    db.commit()
    db.refresh(db_cat)
    return db_cat

@router.delete("/categories/{id}", status_code=status.HTTP_204_NO_CONTENT, dependencies=[dependency_admin])
def delete_category(id: int, db: Session = Depends(get_db)):
    db_cat = db.query(ComplaintCategory).filter(ComplaintCategory.id == id).first()
    if not db_cat:
        raise HTTPException(status_code=404, detail="Category not found")
    db.delete(db_cat)
    db.commit()
    return

# --- User Management CRUD ---

@router.get("/users", response_model=list[UserOut], dependencies=[dependency_admin])
def list_users(role: UserRole | None = None, db: Session = Depends(get_db)):
    query = db.query(User)
    if role:
        query = query.filter(User.role == role)
    return query.order_by(User.id.asc()).all()

@router.post("/users", response_model=UserOut, status_code=status.HTTP_201_CREATED, dependencies=[dependency_admin])
def create_user(user_in: UserCreate, db: Session = Depends(get_db)):
    # Check unique email
    existing = db.query(User).filter(User.email == user_in.email).first()
    if existing:
        raise HTTPException(status_code=400, detail="Email is already in use")
        
    # Validate department_id if role is STAFF or HEAD
    if user_in.role in [UserRole.STAFF, UserRole.HEAD]:
        if not user_in.department_id:
            raise HTTPException(status_code=400, detail="Department is required for staff or department heads")
        dept = db.query(Department).filter(Department.id == user_in.department_id).first()
        if not dept:
            raise HTTPException(status_code=400, detail="Department not found")
            
    db_user = User(
        name=user_in.name,
        email=user_in.email,
        phone=user_in.phone,
        role=user_in.role,
        department_id=user_in.department_id,
        is_active=user_in.is_active,
        password_hash=security.get_password_hash(user_in.password)
    )
    db.add(db_user)
    db.commit()
    db.refresh(db_user)
    return db_user

@router.patch("/users/{id}", response_model=UserOut, dependencies=[dependency_admin])
def update_user(id: int, user_data: UserUpdate, db: Session = Depends(get_db)):
    db_user = db.query(User).filter(User.id == id).first()
    if not db_user:
        raise HTTPException(status_code=404, detail="User not found")
        
    for key, value in user_data.model_dump(exclude_unset=True).items():
        if key == "password":
            if len(value) < 6:
                raise HTTPException(status_code=400, detail="Password must be at least 6 characters")
            db_user.password_hash = security.get_password_hash(value)
        else:
            setattr(db_user, key, value)
            
    db.commit()
    db.refresh(db_user)
    return db_user

@router.delete("/users/{id}", status_code=status.HTTP_204_NO_CONTENT, dependencies=[dependency_admin])
def delete_user(id: int, db: Session = Depends(get_db)):
    db_user = db.query(User).filter(User.id == id).first()
    if not db_user:
        raise HTTPException(status_code=404, detail="User not found")
    db.delete(db_user)
    db.commit()
    return

# --- Complaint CRUD (Admin overrides) ---

@router.get("/complaints", response_model=list[ComplaintOut], dependencies=[dependency_admin])
def admin_list_complaints(db: Session = Depends(get_db)):
    # Admins see all complaints unmasked
    return db.query(Complaint).order_by(Complaint.created_at.desc()).all()

@router.get("/complaints/{id}", response_model=ComplaintDetailOut, dependencies=[dependency_admin])
def admin_get_complaint_details(id: int, db: Session = Depends(get_db)):
    complaint = db.query(Complaint).filter(Complaint.id == id).first()
    if not complaint:
        raise HTTPException(status_code=404, detail="Complaint not found")
    return complaint

@router.patch("/complaints/{id}", response_model=ComplaintOut, dependencies=[dependency_admin])
def admin_update_complaint(id: int, complaint_data: ComplaintUpdate, db: Session = Depends(get_db)):
    complaint = db.query(Complaint).filter(Complaint.id == id).first()
    if not complaint:
        raise HTTPException(status_code=404, detail="Complaint not found")
        
    # Update fields
    for field, value in complaint_data.model_dump(exclude_unset=True).items():
        setattr(complaint, field, value)
        
    db.commit()
    db.refresh(complaint)
    return complaint

@router.delete("/complaints/{id}", status_code=status.HTTP_204_NO_CONTENT, dependencies=[dependency_admin])
def admin_delete_complaint(id: int, db: Session = Depends(get_db)):
    complaint = db.query(Complaint).filter(Complaint.id == id).first()
    if not complaint:
        raise HTTPException(status_code=404, detail="Complaint not found")
    db.delete(complaint)
    db.commit()
    return

# --- Analytics Endpoints ---

@router.get("/dashboard", response_model=AdminDashboard, dependencies=[dependency_admin])
def admin_dashboard_metrics(db: Session = Depends(get_db)):
    total_users = db.query(func.count(User.id)).scalar() or 0
    total_complaints = db.query(func.count(Complaint.id)).scalar() or 0
    resolved = db.query(func.count(Complaint.id)).filter(Complaint.status == ComplaintStatus.RESOLVED).scalar() or 0
    closed = db.query(func.count(Complaint.id)).filter(Complaint.status == ComplaintStatus.CLOSED).scalar() or 0
    
    pending = db.query(func.count(Complaint.id)).filter(
        Complaint.status.in_([
            ComplaintStatus.NEW,
            ComplaintStatus.ASSIGNED,
            ComplaintStatus.IN_PROGRESS,
            ComplaintStatus.WAITING_FOR_STUDENT,
            ComplaintStatus.REOPENED
        ])
    ).scalar() or 0
    
    # Department Performance
    dept_performance = []
    departments = db.query(Department).all()
    for d in departments:
        d_total = db.query(func.count(Complaint.id)).filter(Complaint.department_id == d.id).scalar() or 0
        d_resolved = db.query(func.count(Complaint.id)).filter(
            Complaint.department_id == d.id,
            Complaint.status.in_([ComplaintStatus.RESOLVED, ComplaintStatus.CLOSED])
        ).scalar() or 0
        d_pending = d_total - d_resolved
        rate = (d_resolved / d_total * 100.0) if d_total > 0 else 0.0
        
        dept_performance.append(DepartmentPerformance(
            department_name=d.name,
            total=d_total,
            resolved=d_resolved,
            pending=d_pending,
            resolution_rate=round(rate, 2)
        ))
        
    # Category Breakdown
    cat_breakdown = []
    categories = db.query(ComplaintCategory).all()
    for c in categories:
        c_count = db.query(func.count(Complaint.id)).filter(Complaint.category_id == c.id).scalar() or 0
        if c_count > 0:
            cat_breakdown.append(CategoryBreakdown(category_name=c.name, count=c_count))
            
    # Monthly Trend (Last 6 months)
    monthly_trend = []
    # In SQLite, we can group by strftime. In Postgres, date_trunc. Let's make a cross-db approach or format standard.
    # Grouping using python or simple queries:
    complaints = db.query(Complaint.created_at).all()
    months = {}
    for c in complaints:
        m_str = c.created_at.strftime("%Y-%m")
        months[m_str] = months.get(m_str, 0) + 1
        
    sorted_months = sorted(months.keys(), reverse=True)[:6]
    for m in sorted_months:
        monthly_trend.append(MonthlyTrend(month=m, count=months[m]))
        
    return AdminDashboard(
        total_users=total_users,
        total_complaints=total_complaints,
        resolved_complaints=resolved + closed,
        pending_complaints=pending,
        department_performance=dept_performance,
        category_breakdown=cat_breakdown,
        monthly_trend=monthly_trend
    )

@router.get("/analytics", dependencies=[dependency_admin])
def admin_detailed_analytics(db: Session = Depends(get_db)):
    # Average Resolution Time per department
    avg_times = {}
    depts = db.query(Department).all()
    for d in depts:
        closed = db.query(Complaint).filter(
            Complaint.department_id == d.id,
            Complaint.status.in_([ComplaintStatus.RESOLVED, ComplaintStatus.CLOSED]),
            Complaint.closed_at.isnot(None)
        ).all()
        
        total_hours = 0
        count = len(closed)
        for c in closed:
            delta = c.closed_at - c.created_at
            total_hours += delta.total_seconds() / 3600.0
        avg_times[d.name] = round(total_hours / count, 2) if count > 0 else 0.0
        
    # Priority Breakdown
    priority_counts = db.query(
        Complaint.priority,
        func.count(Complaint.id)
    ).group_by(Complaint.priority).all()
    
    # Satisfaction Rating (Average feedback rating)
    avg_rating = db.query(func.avg(Complaint.feedback_rating)).filter(Complaint.feedback_rating.isnot(None)).scalar()
    
    return {
        "average_resolution_hours_by_department": avg_times,
        "priority_breakdown": {row[0]: row[1] for row in priority_counts},
        "average_student_satisfaction": round(float(avg_rating), 2) if avg_rating else None
    }

@router.get("/monthly-report", dependencies=[dependency_admin])
def admin_monthly_report(db: Session = Depends(get_db)):
    # Group by month and status
    complaints = db.query(Complaint.created_at, Complaint.status).all()
    report = {}
    for c in complaints:
        m_str = c.created_at.strftime("%Y-%m")
        if m_str not in report:
            report[m_str] = {"total": 0, "resolved": 0, "pending": 0}
        report[m_str]["total"] += 1
        if c.status in [ComplaintStatus.RESOLVED, ComplaintStatus.CLOSED]:
            report[m_str]["resolved"] += 1
        else:
            report[m_str]["pending"] += 1
            
    return report

@router.get("/category-report", dependencies=[dependency_admin])
def admin_category_report(db: Session = Depends(get_db)):
    categories = db.query(ComplaintCategory.name, func.count(Complaint.id)).join(
        Complaint, Complaint.category_id == ComplaintCategory.id
    ).group_by(ComplaintCategory.name).all()
    return [{"category": row[0], "count": row[1]} for row in categories]

@router.get("/department-report", dependencies=[dependency_admin])
def admin_department_report(db: Session = Depends(get_db)):
    departments = db.query(Department.name, func.count(Complaint.id)).join(
        Complaint, Complaint.department_id == Department.id
    ).group_by(Department.name).all()
    return [{"department": row[0], "count": row[1]} for row in departments]
