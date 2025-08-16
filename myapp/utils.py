from django.core.mail import send_mail
from django.conf import settings
import os, json, datetime, tempfile, subprocess
from django.conf import settings
from django.core.files import File
from django.db import connection
from openpyxl import load_workbook
from .models import GoodMoralRequest
from django.core.mail import EmailMultiAlternatives
from django.utils.html import escape
import mimetypes


EMAIL_MAX_ATTACHMENT_SIZE = getattr(settings, "EMAIL_MAX_ATTACHMENT_SIZE", 10_000_000)  # ~5 MB

def _ordinal(n: int) -> str:
    if n == 1: return "first"
    if n == 2: return "second"
    if n == 3: return "third"
    return f"{n}th"

def send_violation_email(request, violation, student, violation_count=None, settlement_type=None, declined=False):
    """
    Sends an email to the student.
    - Approved: attaches evidence images (no links in body).
    - Declined: simple notice.
    """
    to_addr = [student.email]
    from_addr = settings.DEFAULT_FROM_EMAIL

    if declined:
        subject = "TUPC OSA: Violation Report Declined"
        text_body = (
            f"Dear {student.first_name} {student.last_name},\n\n"
            f"The violation report filed under your name dated {violation.violation_date} "
            f"for '{violation.get_violation_type_display()}' has been reviewed and declined by the Office of Student Affairs.\n\n"
            f"No further action is required on your part.\n\n"
            f"Thank you."
        )
        html_body = f"""
            <p>Dear {escape(student.first_name)} {escape(student.last_name)},</p>
            <p>The violation report filed under your name dated {escape(str(violation.violation_date))} for
            "<strong>{escape(violation.get_violation_type_display())}</strong>" has been reviewed and <strong>declined</strong>
            by the Office of Student Affairs.</p>
            <p>No further action is required on your part.</p>
            <p>Thank you.</p>
        """
        msg = EmailMultiAlternatives(subject, text_body, from_addr, to_addr)
        msg.attach_alternative(html_body, "text/html")
        msg.send(fail_silently=False)
        return

    # --- Approved path (attachments only, no links) ---
    ord_str = _ordinal(int(violation_count or 1))
    subject = f"TUPC OSA: Notice of {ord_str.capitalize()} Violation"

    evidence = []
    if getattr(violation, "evidence_1", None):
        evidence.append(("Evidence 1", violation.evidence_1))
    if getattr(violation, "evidence_2", None):
        evidence.append(("Evidence 2", violation.evidence_2))

    # Body text without any URLs
    if evidence:
        evidence_line_text = "Evidence files are attached to this email."
        evidence_line_html = "<p>Evidence files are attached to this email.</p>"
    else:
        evidence_line_text = "No evidence files were attached."
        evidence_line_html = "<p>No evidence files were attached.</p>"

    text_body = (
        f"Dear {student.first_name} {student.last_name},\n\n"
        f"You have committed your {ord_str} violation on {violation.violation_date}.\n"
        f"Violation Type: {violation.get_violation_type_display()}\n"
        f"You are required to submit a {settlement_type} at the Office of Student Affairs to settle this violation.\n\n"
        f"{evidence_line_text}\n\n"
        f"Please visit the Office of Student Affairs for more details.\n\n"
        f"Thank you."
    )

    html_body = (
        f"<p>Dear {escape(student.first_name)} {escape(student.last_name)},</p>"
        f"<p>You have committed your <strong>{escape(ord_str)}</strong> violation on {escape(str(violation.violation_date))}.<br>"
        f"Violation Type: <strong>{escape(violation.get_violation_type_display())}</strong><br>"
        f"You are required to submit a <strong>{escape(settlement_type)}</strong> at the Office of Student Affairs to settle this violation.</p>"
        f"{evidence_line_html}"
        f"<p>Please visit the Office of Student Affairs for more details.</p>"
        f"<p>Thank you.</p>"
    )

    msg = EmailMultiAlternatives(subject, text_body, from_addr, to_addr)
    msg.attach_alternative(html_body, "text/html")

    # Attach images (respecting size cap)
    for label, f in evidence:
        try:
            f.open("rb")
            size = getattr(f.file, "size", None) or getattr(f, "size", None)
            if size is None or size <= EMAIL_MAX_ATTACHMENT_SIZE:
                content = f.read()
                guessed = mimetypes.guess_type(f.name)[0] or "application/octet-stream"
                filename = f.name.split("/")[-1]
                msg.attach(filename, content, guessed)
            # else: silently skip oversized files (no links in body)
        except Exception:
            # Skip if storage/backing fails; body already says "attached" or "no evidence"
            pass
        finally:
            try:
                f.close()
            except Exception:
                pass

    msg.send(fail_silently=False)

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

def generate_gmf_pdf(req) -> bytes:
    """
    Build the GMF PDF and return the raw bytes.
    Does NOT save anything to a FileField.
    """
    payload = {
        "student_name": _format_student_name(req),
        "sex": (req.sex or "").strip(),
        "status": _status_for_excel(req.status),
        "program": req.program or "",
        "years_of_stay": req.inclusive_years or "",
        # year-only values, per your new UI
        "admission_date": (req.date_admission or "").strip(),  # "YYYY"
        "date_graduated": (req.date_graduated.strftime("%Y") if req.date_graduated else ""),
        "purpose": req.purpose or "",
        "purpose_other": req.other_purpose or "",
        "osahead": _get_osa_head_name(),
    }

    with tempfile.TemporaryDirectory() as tmpdir:
        out_pdf = os.path.join(tmpdir, "gmf.pdf")
        payload_path = os.path.join(tmpdir, "payload.json")
        with open(payload_path, "w", encoding="utf-8") as fh:
            json.dump(payload, fh, ensure_ascii=False)

        script_path = os.path.join(os.path.dirname(__file__), "libre", "lo_gmf_export.py")
        cmd = [str(settings.LIBREOFFICE_PY), script_path, str(settings.GMF_TEMPLATE_PATH), out_pdf, payload_path]
        r = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=180)
        if r.returncode != 0 or not os.path.exists(out_pdf):
            raise RuntimeError(
                "LibreOffice UNO export failed.\n"
                f"stdout:\n{r.stdout.decode(errors='ignore')}\n\n"
                f"stderr:\n{r.stderr.decode(errors='ignore')}"
            )

        with open(out_pdf, "rb") as fh:
            return fh.read()
