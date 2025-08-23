from django.core.mail import send_mail
from django.conf import settings
import os, json, datetime, tempfile, subprocess, uuid
from django.conf import settings
from django.core.files import File
from django.db import connection
from openpyxl import load_workbook
from .models import GoodMoralRequest, UserAccount
from django.core.mail import EmailMultiAlternatives
from django.utils.html import escape
import mimetypes
from pathlib import Path

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
    from myapp.models import UserAccount 

    name = (
        UserAccount.objects
        .filter(role='admin', is_active=True)
        .order_by('-created_at', '-id')
        .values_list('full_name', flat=True)
        .first()
    )
    return name.strip() if name else "BEVERLY M. DE VEGA"

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
    lo_py = getattr(settings, "LIBREOFFICE_PY", None)
    script_path = Path(getattr(settings, "LO_EXPORT_SCRIPT", 
                        Path(settings.BASE_DIR) / "myapp" / "libre" / "lo_gmf_export.py"))
    template_path = Path(getattr(settings, "GMF_TEMPLATE_PATH"))

    if not lo_py or not Path(lo_py).exists():
        raise FileNotFoundError(
            "LibreOffice not found. Install LibreOffice or set LIBREOFFICE_PY to its bundled interpreter.\n"
            "Windows: C:\\Program Files\\LibreOffice\\program\\python.exe\n"
            "macOS:   /Applications/LibreOffice.app/Contents/Resources/python\n"
            "Linux:   /usr/lib/libreoffice/program/python3"
        )
    if not script_path.exists():
        raise FileNotFoundError(f"LO export script not found: {script_path}")
    if not template_path.exists():
        raise FileNotFoundError(f"GMF template not found: {template_path}")

    # Build payload from your request object
    payload = {
        "student_name": getattr(req, "student_name", "") or "",
        "sex": getattr(req, "sex", "") or "",
        "status": getattr(req, "student_status", "") or "",
        "program": getattr(req, "program", "") or "",
        "years_of_stay": getattr(req, "years_of_stay", "") or "",
        "admission_date": getattr(req, "admission_date", "") or "",
        "date_graduated": getattr(req, "date_graduated", "") or "",
        "purpose": getattr(req, "purpose", "") or "",
        "purpose_other": getattr(req, "purpose_other", "") or "",
        "osahead": _get_osa_head_name(),  # your fixed ORM-based function
    }

    with tempfile.TemporaryDirectory() as td:
        td = Path(td)
        payload_json = td / "payload.json"
        out_pdf = td / f"gmf_{uuid.uuid4().hex}.pdf"
        payload_json.write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")

        cmd = [str(lo_py), str(script_path), str(template_path), str(out_pdf), str(payload_json)]
        proc = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        if proc.returncode != 0:
            raise RuntimeError(
                "LibreOffice export failed.\n"
                f"CMD: {' '.join(cmd)}\n\nSTDOUT:\n{proc.stdout.decode(errors='ignore')}\n\n"
                f"STDERR:\n{proc.stderr.decode(errors='ignore')}"
            )

        if not out_pdf.exists() or out_pdf.stat().st_size == 0:
            raise RuntimeError("LibreOffice export produced no PDF output.")
        return out_pdf.read_bytes()