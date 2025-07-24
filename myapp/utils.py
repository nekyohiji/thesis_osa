from django.core.mail import send_mail
from django.conf import settings

def send_violation_email(violation, student, violation_count=None, settlement_type=None, declined=False):
    """
    Sends an email to the student notifying them of their violation.
    Supports both approved and declined notifications.
    """
    if declined:
        # Declined case
        subject = "TUPC OSA: Violation Report Declined"
        message = (
            f"Dear {student.first_name} {student.last_name},\n\n"
            f"The violation report filed under your name dated {violation.violation_date} "
            f"for '{violation.get_violation_type_display()}' has been reviewed and declined by the Office of Student Affairs.\n\n"
            f"No further action is required on your part.\n\n"
            f"Thank you."
        )
    else:
        # Approved case
        if violation_count == 1:
            ordinal = "first"
        elif violation_count == 2:
            ordinal = "second"
        elif violation_count == 3:
            ordinal = "third"
        else:
            ordinal = f"{violation_count}th"

        subject = f"TUPC OSA: Notice of {ordinal.capitalize()} Violation"

        # Collect evidence file names (if available)
        evidence_files = []
        if violation.evidence_1:
            evidence_files.append(violation.evidence_1.name)  # relative path in media/
        if violation.evidence_2:
            evidence_files.append(violation.evidence_2.name)

        evidence_text = "\n".join(evidence_files) if evidence_files else "No evidence attached."

        message = (
            f"Dear {student.first_name} {student.last_name},\n\n"
            f"You have committed your {ordinal} violation on {violation.violation_date}.\n"
            f"Violation Type: {violation.get_violation_type_display()}\n"
            f"You are required to submit a {settlement_type} at the Office of Student Affairs to settle this violation.\n\n"
            f"Evidence attached in the system:\n{evidence_text}\n\n"
            f"Please visit the Office of Student Affairs for more details.\n\n"
            f"Thank you."
        )

    # Send the email
    send_mail(
        subject=subject,
        message=message,
        from_email=settings.DEFAULT_FROM_EMAIL,
        recipient_list=[student.email],
        fail_silently=False
    )

def send_status_email(to_email, approved=True, reason=None):
    subject = "Good Moral Certificate Request Status"
    if approved:
        message = "Your Good Moral Certificate request has been approved."
    else:
        message = f"Your request has been declined. Reason: {reason or 'Not specified'}"

    send_mail(
        subject,
        message,
        settings.DEFAULT_FROM_EMAIL,
        [to_email],
        fail_silently=False,
    )