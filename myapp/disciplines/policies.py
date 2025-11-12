# myapp/disciplines/policies.py
from django.db.models import Count
from django.apps import apps

# Optional: exclude specific minor violation types from contributing to the cap
CS_EXEMPT_TYPES = {"Attempt Fraternity"}  # must exactly match Violation.violation_type

def _per_type_cap(n: int) -> int:
    """
    Minor-per-type progressive cap:
      1 -> 0
      2 -> 20
      3 -> 50
      4+ -> 50 + 10*(n-3)
    """
    if n <= 1:
        return 0
    if n == 2:
        return 20
    return 50 + 10 * (n - 3)

def compute_hours_cap_for_student(student_id: str) -> int:
    """
    Policy:
      - If the student has ≥1 Approved MAJOR violation -> cap = 500
      - Else, cap = sum over MINOR violations per type using _per_type_cap,
        excluding any exempt types.
    Returns an int (views can wrap in Decimal if needed).
    """
    Violation = apps.get_model("myapp", "Violation")

    # Any Approved MAJOR violation? -> hard cap = 500
    has_major = Violation.objects.filter(
        student_id=student_id, status="Approved", severity="MAJOR"
    ).exists()
    if has_major:
        return 500

    # Otherwise, sum MINOR caps per violation_type (Approved only), excluding exempts
    rows = (
        Violation.objects
        .filter(student_id=student_id, severity="MINOR", status="Approved")
        .exclude(violation_type__in=CS_EXEMPT_TYPES)
        .values("violation_type")
        .annotate(n=Count("id"))
    )
    return sum(_per_type_cap(row["n"]) for row in rows)