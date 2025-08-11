import os, shlex, subprocess, tempfile, datetime
from django.conf import settings
from django.utils import timezone
from openpyxl import load_workbook

TEMPLATE_PATH = os.path.join(settings.BASE_DIR, "myapp", "cert_templates", "Acknowledgement-Receipt-Form.xlsx")

def _set_input(ws, key, value):
    """Find `key` in column A and write `value` in column B (case-insensitive)."""
    k = (key or "").strip().lower()
    for row in ws.iter_rows(min_row=1, max_col=2):
        a = (row[0].value or "").strip().lower()
        if a == k:
            row[1].value = value
            return True
    return False

def _fmt_name(req):
    parts = [req.first_name, req.middle_name, req.surname, req.extension]
    name = " ".join(p for p in parts if p).strip()
    return " ".join(name.split()).upper()

def _fmt_timestamp(dt):
    # Example: 10/08/2025 8:57:32PM (no space before AM/PM)
    local = timezone.localtime(dt)
    s = local.strftime("%m/%d/%Y %I:%M:%S%p")
    return s.lstrip("0")  

def build_ack_pdf(request_obj, admin_name_upper):
    """
    Fills the inputs sheet then exports the 'Acknowledgement Receipt' sheet to PDF
    using LibreOffice. Returns absolute path to the generated PDF.
    """
    if not os.path.exists(TEMPLATE_PATH):
        raise FileNotFoundError(f"Template not found: {TEMPLATE_PATH}")

    tmpdir = tempfile.mkdtemp(prefix="ack_")
    xlsx_out = os.path.join(tmpdir, "ack_work.xlsx")

    # Load & fill workbook
    wb = load_workbook(TEMPLATE_PATH, data_only=False)
    ws_inputs = wb["inputs"]  # will raise KeyError if missing — good: fail fast

    data = {
        "student_name": _fmt_name(request_obj),
        "student_id": request_obj.student_number,
        "year_level": request_obj.year_level,
        "program": request_obj.program,
        "years_of_stay": request_obj.inclusive_years,
        "timestamp": _fmt_timestamp(timezone.now()),
        "proof": request_obj.get_document_type_display() if hasattr(request_obj, "get_document_type_display") else request_obj.document_type,
        "reason": request_obj.get_reason_display() if hasattr(request_obj, "get_reason_display") else request_obj.reason,
        "osa_head": admin_name_upper,
    }
    for k, v in data.items():
        _set_input(ws_inputs, k, v)

    # Hide inputs sheet; set the target sheet active (helps export)
    ws_inputs.sheet_state = "hidden"
    if "Acknowledgement Receipt" in wb.sheetnames:
        wb.active = wb.sheetnames.index("Acknowledgement Receipt")

    wb.save(xlsx_out)

    # Export to PDF via LibreOffice headless
    outdir = tmpdir
    lo = getattr(settings, "LIBREOFFICE_BIN", "soffice")
    cmd = [
        lo, "--headless", "--nologo", "--nofirststartwizard",
        "--convert-to", "pdf", "--outdir", outdir, xlsx_out,
    ]
    proc = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    if proc.returncode != 0:
        raise RuntimeError(f"LibreOffice export failed: {proc.stderr.decode(errors='ignore') or proc.stdout.decode(errors='ignore')}")

    # LibreOffice names the PDF from the XLSX basename
    pdf_path = os.path.join(outdir, "ack_work.pdf")
    # Rename to a nice filename
    nice_name = f"Acknowledgement-Receipt-{request_obj.student_number}.pdf"
    nice_path = os.path.join(outdir, nice_name)
    if os.path.exists(pdf_path):
        os.replace(pdf_path, nice_path)
        pdf_path = nice_path

    return pdf_path
