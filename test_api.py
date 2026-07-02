import sys
import os
from fastapi.testclient import TestClient

# Add project root to sys.path
sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)))

from app.main import app
from app.models.complaint import ComplaintStatus, ComplaintPriority

client = TestClient(app)

def test_workflow():
    print("\n--- RUNNING SCENARIO TEST ---")
    
    # 1. Login as Student
    print("Testing Student Login...")
    student_login = client.post("/auth/login", data={"username": "student@student.com", "password": "password123"})
    assert student_login.status_code == 200, f"Login failed: {student_login.text}"
    student_tokens = student_login.json()
    student_headers = {"Authorization": f"Bearer {student_tokens['access_token']}"}
    print("✓ Student Login Successful")
    
    # 2. Login as Staff
    print("Testing Staff Login...")
    staff_login = client.post("/auth/login", data={"username": "hostelstaff@admin.com", "password": "password123"})
    assert staff_login.status_code == 200
    staff_tokens = staff_login.json()
    staff_headers = {"Authorization": f"Bearer {staff_tokens['access_token']}"}
    print("✓ Staff Login Successful")
    
    # 3. Login as Department Head
    print("Testing Head Login...")
    head_login = client.post("/auth/login", data={"username": "hostelhead@admin.com", "password": "password123"})
    assert head_login.status_code == 200
    head_tokens = head_login.json()
    head_headers = {"Authorization": f"Bearer {head_tokens['access_token']}"}
    print("✓ Head Login Successful")
    
    # 4. Login as Admin
    print("Testing Admin Login...")
    admin_login = client.post("/auth/login", data={"username": "admin@admin.com", "password": "password123"})
    assert admin_login.status_code == 200
    admin_tokens = admin_login.json()
    admin_headers = {"Authorization": f"Bearer {admin_tokens['access_token']}"}
    print("✓ Admin Login Successful")
    
    # 5. Create Complaint as Student
    print("Creating complaint as Student...")
    complaint_payload = {
        "title": "Water Leakage in Room 204",
        "description": "The pipe under the bathroom sink is leaking heavily.",
        "category_id": 1,      # Hostel Room Maintenance (seeded)
        "department_id": 1,    # Hostel Department (seeded)
        "priority": "HIGH",
        "anonymous": False
    }
    create_res = client.post("/complaints", json=complaint_payload, headers=student_headers)
    assert create_res.status_code == 201, f"Complaint creation failed: {create_res.text}"
    complaint = create_res.json()
    complaint_id = complaint["id"]
    ticket_number = complaint["ticket_number"]
    assert ticket_number.startswith("COMP-")
    assert complaint["status"] == "NEW"
    print(f"✓ Complaint Created: {ticket_number} (ID: {complaint_id})")
    
    # 6. Post Public Comment as Student
    print("Posting student public comment...")
    comment_payload = {"message": "Please fix this quickly, water is spilling everywhere."}
    comment_res = client.post(f"/complaints/{complaint_id}/comments", json=comment_payload, headers=student_headers)
    assert comment_res.status_code == 201
    print("✓ Public Comment Posted")
    
    # 7. Staff Accepts Complaint
    print("Staff accepting complaint...")
    accept_res = client.post(f"/staff/complaints/{complaint_id}/accept", headers=staff_headers)
    assert accept_res.status_code == 200
    assert accept_res.json()["status"] == "IN_PROGRESS"
    print("✓ Complaint accepted by staff (Status: IN_PROGRESS)")
    
    # 8. Staff Adds Internal Note
    print("Staff posting internal note...")
    note_payload = {"message": "We need to dispatch plumber Dave to Room 204."}
    note_res = client.post(f"/staff/complaints/{complaint_id}/internal-note", json=note_payload, headers=staff_headers)
    assert note_res.status_code == 201
    print("✓ Internal note posted successfully by staff")
    
    # 9. Verify Student cannot see Internal Note
    print("Verifying student visibility restrictions...")
    comments_student_view = client.get(f"/complaints/{complaint_id}/comments", headers=student_headers)
    assert comments_student_view.status_code == 200
    comments_student = comments_student_view.json()
    
    # Check that none of the retrieved comments are internal notes
    for c in comments_student:
        assert not c["internal_note"], "Student received an internal note comment!"
    print("✓ Checked: student cannot view internal notes")
    
    # 10. Verify Staff can see Internal Note
    comments_staff_view = client.get(f"/complaints/{complaint_id}/comments", headers=staff_headers)
    assert comments_staff_view.status_code == 200
    comments_staff = comments_staff_view.json()
    has_internal = any(c["internal_note"] for c in comments_staff)
    assert has_internal, "Staff could not retrieve internal note comment!"
    print("✓ Checked: staff can view internal notes")
    
    # 11. Staff Resolves Complaint
    print("Staff resolving complaint...")
    resolve_payload = {"message": "Plumber Dave fixed the sink leak and replaced the gasket."}
    resolve_res = client.post(f"/staff/complaints/{complaint_id}/resolve", json=resolve_payload, headers=staff_headers)
    assert resolve_res.status_code == 200
    assert resolve_res.json()["status"] == "RESOLVED"
    print("✓ Complaint marked RESOLVED by staff")
    
    # 12. Student Submits Feedback and Closes Complaint
    print("Student submitting feedback...")
    feedback_payload = {
        "rating": 5,
        "comment": "Perfect service, leakage stopped completely!"
    }
    feedback_res = client.post(f"/complaints/{complaint_id}/feedback", json=feedback_payload, headers=student_headers)
    assert feedback_res.status_code == 200
    closed_complaint = feedback_res.json()
    assert closed_complaint["status"] == "CLOSED"
    assert closed_complaint["feedback_rating"] == 5
    assert closed_complaint["feedback_comment"] == "Perfect service, leakage stopped completely!"
    print("✓ Feedback submitted. Complaint status automatically updated to CLOSED")
    
    # 13. Verify Complaint History (Audit Log)
    print("Verifying complaint history audit log...")
    detail_res = client.get(f"/complaints/{complaint_id}", headers=student_headers)
    assert detail_res.status_code == 200
    history = detail_res.json()["history"]
    assert len(history) > 0
    actions = [h["action"] for h in history]
    print(f"Audit Actions recorded: {actions}")
    print("✓ Checked: audit history populated correctly")
    
    # 14. Verify Head Dashboard and statistics
    print("Verifying Department Head dashboard and stats...")
    head_dash = client.get("/department/dashboard", headers=head_headers)
    assert head_dash.status_code == 200
    head_stats = client.get("/department/statistics", headers=head_headers)
    assert head_stats.status_code == 200
    print("✓ Head Dashboard and statistics verified")
    
    # 15. Verify Admin Reports Exports (CSV, Excel, PDF)
    print("Verifying Admin reports exports...")
    csv_res = client.get("/reports/csv", headers=admin_headers)
    assert csv_res.status_code == 200
    assert "text/csv" in csv_res.headers["content-type"]
    
    excel_res = client.get("/reports/excel", headers=admin_headers)
    assert excel_res.status_code == 200
    assert "spreadsheetml" in excel_res.headers["content-type"]
    
    pdf_res = client.get("/reports/pdf", headers=admin_headers)
    assert pdf_res.status_code == 200
    assert "application/pdf" in pdf_res.headers["content-type"]
    print("✓ Admin Reports (CSV, Excel, PDF) exported successfully")
    
    # 16. Verify Advanced Search
    print("Verifying search filter operation...")
    search_res = client.get(f"/search?status=CLOSED&priority=HIGH", headers=student_headers)
    assert search_res.status_code == 200
    results = search_res.json()
    assert len(results) > 0
    assert results[0]["ticket_number"] == ticket_number
    print("✓ Search returned correct filtered complaint")
    
    print("\n==============================")
    print("ALL API FLOWS TESTED SUCCESSFULLY!")
    print("==============================\n")

if __name__ == "__main__":
    test_workflow()
