# myapp/services/community_service.py
from decimal import Decimal, InvalidOperation
from django.db import transaction
from myapp.models import Violation, ViolationSettlement, CommunityServiceCase

TEN_HOURS = Decimal("10.0")

@transaction.atomic
def auto_cs_after_two(student_id: str, last_violation: Violation | None = None) -> None:
    """
    If the student has >= 2 Approved violations, ensure a CommunityServiceCase exists
    with total_required_hours = 10 (created once). Do NOT auto-raise on later offenses.
    """
    approved_count = (
        Violation.objects
        .select_for_update()
        .filter(student_id=student_id, status="Approved")
        .count()
    )
    if approved_count < 2:
        return

    # Create a case with 10h if none exists. If it exists, leave it as-is.
    CommunityServiceCase.objects.select_for_update().get_or_create(
        student_id=student_id,
        defaults={"total_required_hours": TEN_HOURS}
    )

    # Make sure the specific violation has a settlement entry (for your UI)
    if last_violation is not None:
        ViolationSettlement.objects.get_or_create(
            violation=last_violation,
            defaults={"settlement_type": "Community Service", "is_settled": False}
        )
