from sqlalchemy.orm import Session
from app.database import SessionLocal
from app.models.user import User, UserRole
from app.models.department import Department, ComplaintCategory
from app.core import security

def seed_db():
    db = SessionLocal()
    try:
        # Check if database is already seeded
        if db.query(User).first():
            print("Database already contains user records. Skipping seeding.")
            return

        print("Seeding database initial records...")
        
        # 1. Create Departments
        hostel_dept = Department(name="Hostel Department", email="hostel@uni.edu")
        mess_dept = Department(name="Mess Department", email="mess@uni.edu")
        academic_dept = Department(name="Academic Department", email="academic@uni.edu")
        it_dept = Department(name="IT Services", email="it@uni.edu")
        finance_dept = Department(name="Finance Department", email="finance@uni.edu")
        
        db.add_all([hostel_dept, mess_dept, academic_dept, it_dept, finance_dept])
        db.commit()
        
        # 2. Create Categories linked to Departments
        hostel_cats = [
            ComplaintCategory(name="Hostel Room Maintenance", department_id=hostel_dept.id),
            ComplaintCategory(name="Hostel Water Supply", department_id=hostel_dept.id),
            ComplaintCategory(name="Hostel Security", department_id=hostel_dept.id),
        ]
        mess_cats = [
            ComplaintCategory(name="Mess Food Quality", department_id=mess_dept.id),
            ComplaintCategory(name="Mess Hygiene", department_id=mess_dept.id),
        ]
        academic_cats = [
            ComplaintCategory(name="Course Registration", department_id=academic_dept.id),
            ComplaintCategory(name="Exam Schedule", department_id=academic_dept.id),
            ComplaintCategory(name="Faculty Behavior", department_id=academic_dept.id),
        ]
        it_cats = [
            ComplaintCategory(name="Wi-Fi Connection", department_id=it_dept.id),
            ComplaintCategory(name="Lab Systems", department_id=it_dept.id),
        ]
        finance_cats = [
            ComplaintCategory(name="Scholarship Disbursement", department_id=finance_dept.id),
            ComplaintCategory(name="Tuition Fee Payment", department_id=finance_dept.id),
        ]
        
        db.add_all(hostel_cats + mess_cats + academic_cats + it_cats + finance_cats)
        db.commit()
        
        # 3. Create Users for all roles
        super_admin = User(
            name="Super Administrator",
            email="superadmin@admin.com",
            phone="1112223330",
            role=UserRole.SUPERADMIN,
            password_hash=security.get_password_hash("password123")
        )
        
        admin = User(
            name="General Administrator",
            email="admin@admin.com",
            phone="1112223331",
            role=UserRole.ADMIN,
            password_hash=security.get_password_hash("password123")
        )
        
        head = User(
            name="Hostel Department Head",
            email="hostelhead@admin.com",
            phone="1112223332",
            role=UserRole.HEAD,
            department_id=hostel_dept.id,
            password_hash=security.get_password_hash("password123")
        )
        
        staff = User(
            name="Hostel Staff Member",
            email="hostelstaff@admin.com",
            phone="1112223333",
            role=UserRole.STAFF,
            department_id=hostel_dept.id,
            password_hash=security.get_password_hash("password123")
        )
        
        student = User(
            name="Alex Student",
            email="student@student.com",
            phone="1112223334",
            role=UserRole.STUDENT,
            password_hash=security.get_password_hash("password123")
        )
        
        db.add_all([super_admin, admin, head, staff, student])
        db.commit()
        
        # Link head to the department
        hostel_dept.head_id = head.id
        db.commit()
        
        print("Database seeding completed successfully.")
        
    except Exception as e:
        db.rollback()
        print(f"Error seeding database: {e}")
        raise e
    finally:
        db.close()

if __name__ == "__main__":
    seed_db()
