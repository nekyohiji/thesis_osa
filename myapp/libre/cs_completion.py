# myapp/libre/cs_completion.py
import os, subprocess, tempfile
from django.conf import settings
from openpyxl import load_workbook

TEMPLATE_PATH = os.path.join(
    settings.BASE_DIR, "myapp", "cert_templates", "Completion_Certificate.xlsx"
)

def _set_input(ws, key, value):
    """Find `key` in column A (case-insensitive exact match) and write `value` to column B."""
    needle = (key or "").strip().lower()
    for row in ws.iter_rows(min_row=1, max_col=2):
        a = (row[0].value or "").strip().lower()
        if a == needle:
            row[1].value = "" if value is None else str(value)
            return True
    return False

def _fmt_student_name(case):
    # "First M. Last Ext" with normalized spacing, preserving normal casing
    parts = []
    if getattr(case, "first_name", None):
        parts.append(case.first_name.strip())
    mi = (getattr(case, "middle_initial", "") or "").strip().rstrip(".")
    if mi:
        parts.append(f"{mi}.")
    if getattr(case, "last_name", None):
        parts.append(case.last_name.strip())
    ext = (getattr(case, "extension_name", "") or "").strip()
    if ext:
        parts.append(ext)
    return " ".join(p for p in parts if p)

def build_cs_completion_pdf(case_obj, osa_head_name):
    """
    Fill `inputs` sheet then export 'Completion Certificate' to PDF via LibreOffice.
    Returns absolute path to the generated PDF.
    """
    if not os.path.exists(TEMPLATE_PATH):
        raise FileNotFoundError(f"Template not found: {TEMPLATE_PATH}")

    tmpdir = tempfile.mkdtemp(prefix="cs_complete_")
    xlsx_out = os.path.join(tmpdir, "completion_work.xlsx")

    # Load & fill workbook
    wb = load_workbook(TEMPLATE_PATH, data_only=False)
    ws_inputs = wb["inputs"]  # fail fast if missing

    payload = {
        "student_name": _fmt_student_name(case_obj),
        "program": getattr(case_obj, "program_course", ""),
        "osa_head": osa_head_name or "",
    }
    for k, v in payload.items():
        if not _set_input(ws_inputs, k, v):
            raise KeyError(f"Key '{k}' not found in inputs sheet A-column of {TEMPLATE_PATH}")

    # Hide inputs; activate target for cleaner export
    ws_inputs.sheet_state = "hidden"
    target_name = "Completion Certificate"
    if target_name not in wb.sheetnames:
        # Soft fallback in case the sheet was misnamed in a copy
        raise KeyError(f"Sheet '{target_name}' not found in template.")
    wb.active = wb.sheetnames.index(target_name)

    # OPTIONAL: ensure a sane print area (silences stale Print_Area warnings)
    try:
        ws_target = wb[target_name]
        ws_target.print_area = ws_target.calculate_dimension()  # or hardcode like 'A1:R18'
        # If a stale workbook-level Print_Area exists, removing it avoids warnings.
        wb.defined_names.delete("Print_Area")
    except Exception:
        pass

    wb.save(xlsx_out)

    # LibreOffice headless export
    lo = getattr(settings, "LIBREOFFICE_BIN", "soffice")
    cmd = [
        lo, "--headless", "--nologo", "--nofirststartwizard",
        "--convert-to", "pdf", "--outdir", tmpdir, xlsx_out,
    ]
    proc = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    if proc.returncode != 0:
        err = proc.stderr.decode(errors="ignore") or proc.stdout.decode(errors="ignore")
        raise RuntimeError(f"LibreOffice export failed: {err}")

    # LibreOffice names from XLSX basename -> completion_work.pdf
    pdf_path = os.path.join(tmpdir, "completion_work.pdf")
    nice_name = f"Completion-{case_obj.student_id}.pdf"
    nice_path = os.path.join(tmpdir, nice_name)
    if os.path.exists(pdf_path):
        os.replace(pdf_path, nice_path)
        pdf_path = nice_path

    return pdf_path
