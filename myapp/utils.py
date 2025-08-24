from django.core.mail import send_mail
from django.conf import settings
import os, json, datetime, tempfile, subprocess, uuid, sys, importlib
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


def _clean_suffix(ext) -> str:
    """
    Return a cleaned suffix (e.g., 'Jr.', 'III') or '' if it's a junk value like NA/N-A/None/--.
    """
    if not ext:
        return ""
    raw = str(ext).strip()
    if not raw:
        return ""

    # normalize for comparison: keep only letters/digits
    norm = "".join(ch for ch in raw if ch.isalnum()).upper()

    # values to treat as "no suffix"
    ignore = {"NA", "NONE", "NULL", "NAN"}  # covers 'na', 'n/a', 'N.A.', etc. after normalization
    if norm in ignore or raw in {"-", "--"}:
        return ""
    return raw  # keep user's casing/punctuation for real suffixes


def _format_student_name(req):
    """Build 'First M. Last Suffix' with suffix cleaned."""
    # prefer req.student_name if present
    if getattr(req, "student_name", None):
        return (req.student_name or "").strip()

    parts = [(getattr(req, "first_name", "") or "").strip()]

    mi = (getattr(req, "middle_name", "") or "").strip()
    if mi:
        parts.append(f"{mi[0].upper()}.")

    parts.append((getattr(req, "surname", "") or "").strip())

    ext_clean = _clean_suffix(getattr(req, "ext", ""))
    if ext_clean:
        parts.append(ext_clean)

    return " ".join(p for p in parts if p)


def _status_for_excel(raw: str) -> str:
    s = (raw or "").strip().lower()
    if s in {"current", "current student", "enrolled"}: return "Current Student"
    if s in {"former", "former student"}:               return "Former Student"
    if "grad" in s or "alum" in s:                      return "Graduate"
    return "Graduate"


def _fmt_yyyy_mm_dd(dt):
    return "" if not dt else dt.strftime("%Y-%m-%d")


def _lo_python_path() -> str | None:
    """
    Find LibreOffice's bundled Python.
    Priority: ENV -> common Windows/macOS/Linux locations.
    """
    cand = []

    # explicit override
    env = os.environ.get("LIBREOFFICE_PY")
    if env:
        cand.append(env)

    # Windows
    if os.name == "nt":
        for base in filter(None, [os.environ.get("ProgramFiles"), os.environ.get("ProgramFiles(x86)")]):
            cand += [
                str(Path(base) / "LibreOffice" / "program" / "python.exe"),
                str(Path(base) / "LibreOffice" / "program" / "python3.exe"),
            ]
    else:
        # macOS
        cand += [
            "/Applications/LibreOffice.app/Contents/Resources/python",
            "/Applications/LibreOffice.app/Contents/MacOS/python",
        ]
        # Linux
        cand += [
            "/usr/lib/libreoffice/program/python3",
            "/usr/lib/libreoffice/program/python",
        ]

    for p in cand:
        if p and os.path.exists(p):
            return p
    return None


def generate_gmf_pdf(req):
    """
    Calls LibreOffice's bundled Python to run lo_gmf_export.py (which uses UNO inside LO).
    This avoids importing 'uno' in Django's interpreter.
    """
    lo_py = _lo_python_path()
    if not lo_py:
        raise FileNotFoundError(
            "LibreOffice Python not found. Set LIBREOFFICE_PY to the LO python path.\n"
            "Windows: C:\\Program Files\\LibreOffice\\program\\python.exe\n"
            "macOS:   /Applications/LibreOffice.app/Contents/Resources/python\n"
            "Linux:   /usr/lib/libreoffice/program/python3"
        )

    script = Path(settings.BASE_DIR) / "lo_gmf_export.py"
    if not script.exists():
        raise FileNotFoundError(f"Export script not found: {script}")

    template = Path(settings.GMF_TEMPLATE_PATH)
    if not template.exists():
        raise FileNotFoundError(f"GMF template not found at: {template}")

    # Build payload expected by your LO script / named ranges
    payload = {
        "student_name": _format_student_name(req),
        "program": (getattr(req, "program", "") or "").strip(),
        "sex": (getattr(req, "sex", "") or "").strip().upper(),
        "status": _status_for_excel(getattr(req, "status", "")),
        "years_of_stay": str(getattr(req, "years_of_stay", "") or ""),
        "admission_date": str(getattr(req, "admission_date", "") or ""),
        "date_graduated": _fmt_yyyy_mm_dd(getattr(req, "date_graduated", None)),
        "purpose": (getattr(req, "purpose", "") or "").strip(),
        "purpose_other": (getattr(req, "purpose_other", "") or "").strip(),
        "osahead": _get_osa_head_name(),
    }

    with tempfile.TemporaryDirectory() as tmp:
        tmp = Path(tmp)
        out_pdf = tmp / "gmf.pdf"
        payload_json = tmp / "payload.json"
        payload_json.write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")

        cmd = [lo_py, str(script), str(template), str(out_pdf), str(payload_json)]
        try:
            proc = subprocess.run(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                timeout=120  # prevent runaway LO
            )
        except subprocess.TimeoutExpired:
            raise RuntimeError("LibreOffice export timed out (120s).")

        if proc.returncode != 0 or not out_pdf.exists():
            raise RuntimeError(
                "LibreOffice export failed.\n"
                f"CMD: {' '.join(cmd)}\n"
                f"STDOUT:\n{proc.stdout.decode(errors='ignore')}\n"
                f"STDERR:\n{proc.stderr.decode(errors='ignore')}"
            )

        return out_pdf.read_bytes()