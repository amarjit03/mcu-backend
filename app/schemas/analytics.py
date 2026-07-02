from pydantic import BaseModel


class StudentDashboard(BaseModel):
    total_complaints: int
    pending_complaints: int
    resolved_complaints: int
    closed_complaints: int
    average_resolution_time_hours: float | None = None

class DepartmentDashboard(BaseModel):
    assigned_to_staff_count: int
    pending_count: int  # NEW, ASSIGNED, IN_PROGRESS, WAITING_FOR_STUDENT
    urgent_count: int
    overdue_count: int  # pending and created > 3 days ago
    closed_today_count: int

class DepartmentPerformance(BaseModel):
    department_name: str
    total: int
    resolved: int
    pending: int
    resolution_rate: float

class CategoryBreakdown(BaseModel):
    category_name: str
    count: int

class MonthlyTrend(BaseModel):
    month: str  # YYYY-MM
    count: int

class AdminDashboard(BaseModel):
    total_users: int
    total_complaints: int
    resolved_complaints: int
    pending_complaints: int
    department_performance: list[DepartmentPerformance] = []
    category_breakdown: list[CategoryBreakdown] = []
    monthly_trend: list[MonthlyTrend] = []
