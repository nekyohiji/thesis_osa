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
    
import os, json, datetime, tempfile, subprocess
from django.conf import settings
from django.core.files import File
from django.db import connection
from openpyxl import load_workbook
from .models import GoodMoralRequest


# ---------- helpers ----------
def _get_osa_head_name():
    with connection.cursor() as cur:
        cur.execute("""
            SELECT full_name
            FROM user_accounts
            WHERE LOWER(role)='admin' AND is_active=1
            ORDER BY created_at DESC, id DESC
            LIMIT 1
        """)
        row = cur.fetchone()
    return (row[0].strip() if row and row[0] else "BEVERLY M. DE VEGA")

def _format_student_name(req: GoodMoralRequest) -> str:
    parts = [(req.first_name or "").strip()]
    mi = (req.middle_name or "").strip()
    if mi:
        parts.append(f"{mi[0].upper()}.")
    parts.append((req.surname or "").strip())
    if req.ext:
        parts.append(req.ext.strip())
    return " ".join([p for p in parts if p])

def _status_for_excel(raw: str) -> str:
    s = (raw or "").strip().lower()
    if s in {"current", "current student", "enrolled"}: return "Current Student"
    if s in {"former", "former student"}:               return "Former Student"
    if "grad" in s or "alum" in s:                      return "Graduate"
    return "Graduate"

def _fmt_grad_date(dt):
    return "" if not dt else dt.strftime("%Y-%m-%d")

def generate_gmf_pdf(req: GoodMoralRequest) -> str:
    """
    Use LibreOffice (UNO) to open the ORIGINAL xlsx, fill named ranges,
    hide non-GMF sheets, and export GMF to PDF (no openpyxl).
    Saves to FileField and returns persistent path.
    """
    payload = {
        "student_name": _format_student_name(req),
        "sex": (req.sex or "").strip(),
        "status": _status_for_excel(req.status),
        "program": req.program or "",
        "years_of_stay": req.inclusive_years or "",
        "admission_date": (req.date_admission or "").strip(),
        "date_graduated": _fmt_grad_date(req.date_graduated),
        "purpose": req.purpose or "",
        "purpose_other": req.other_purpose or "",
        "osahead": _get_osa_head_name(),
    }

    with tempfile.TemporaryDirectory() as tmpdir:
        out_pdf = os.path.join(tmpdir, "gmf.pdf")
        payload_path = os.path.join(tmpdir, "payload.json")
        with open(payload_path, "w", encoding="utf-8") as fh:
            json.dump(payload, fh, ensure_ascii=False)

        script_path = os.path.join(
            os.path.dirname(__file__), "libre", "lo_gmf_export.py"
        )

        cmd = [
            str(settings.LIBREOFFICE_PY), script_path,
            str(settings.GMF_TEMPLATE_PATH),
            out_pdf,
            payload_path,
        ]
        r = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=180)
        if r.returncode != 0 or not os.path.exists(out_pdf):
            raise RuntimeError(
                "LibreOffice UNO export failed.\n"
                f"stdout:\n{r.stdout.decode(errors='ignore')}\n\n"
                f"stderr:\n{r.stderr.decode(errors='ignore')}"
            )

        # Save to FileField
        filename = f"GMF_{req.student_id}_{datetime.date.today().isoformat()}.pdf"
        with open(out_pdf, "rb") as fh:
            req.certificate_pdf.save(filename, File(fh), save=True)

        return req.uploaded_file.path