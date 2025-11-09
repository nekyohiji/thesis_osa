# myapp/disciplines/policies.py
from django.db.models import Count
from django.apps import apps

def _per_type_cap(n: int) -> int:
    # 1 -> 0 | 2 -> 20 | 3 -> 50 | 4+ -> 50 + 10*(n-3)
    if n <= 1:
        return 0
    if n == 2:
        return 20
    return 50 + 10*(n - 3)

def compute_hours_cap_for_student(student_id: str) -> int:
    """
    Sum of caps across MINOR violations by type for this student.
    Counts only Approved violations (change filter if you want Pending included).
    """
    Violation = apps.get_model("myapp", "Violation")  # <-- no fragile imports
    rows = (Violation.objects
            .filter(student_id=student_id, severity="MINOR", status="Approved")
            .values("violation_type")
            .annotate(n=Count("id")))
    return sum(_per_type_cap(row["n"]) for row in rows)
