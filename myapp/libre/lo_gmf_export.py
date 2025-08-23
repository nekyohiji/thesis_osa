# lo_gmf_export.py
# Usage: lo_gmf_export.py <template.xlsx> <out.pdf> <payload.json>

import os, sys, json, shutil, uuid, traceback, uno, officehelper
from com.sun.star.beans import PropertyValue

def pv(name, val):
    p = PropertyValue(); p.Name = name; p.Value = val; return p

def _set_named_string(doc, name, value) -> bool:
    """Write string value into a single-cell Named Range (Calc)."""
    try:
        named = doc.NamedRanges
        if not named.hasByName(name):
            return False
        ref = named.getByName(name).getReferredCells()
        addr = ref.getCellAddress()
        sheet = doc.Sheets.getByIndex(addr.Sheet)
        cell = sheet.getCellByPosition(addr.Column, addr.Row)
        cell.String = "" if value is None else str(value)
        return True
    except Exception:
        return False

def main(template_path, out_pdf_path, payload_json_path):
    try:
        # Bootstrap LibreOffice (run by LibreOffice-bundled python)
        ctx = officehelper.bootstrap()
        smgr = ctx.getServiceManager()
        desktop = smgr.createInstanceWithContext("com.sun.star.frame.Desktop", ctx)

        # Work on a temp copy to avoid locks
        tmp_dir  = os.path.dirname(os.path.abspath(out_pdf_path)) or os.getcwd()
        tmp_xlsx = os.path.join(tmp_dir, f"gmf_{uuid.uuid4().hex}.xlsx")
        shutil.copy2(template_path, tmp_xlsx)

        in_url  = uno.systemPathToFileUrl(os.path.abspath(tmp_xlsx))
        out_url = uno.systemPathToFileUrl(os.path.abspath(out_pdf_path))

        # Load hidden (writable)
        doc = desktop.loadComponentFromURL(in_url, "_blank", 0, (pv("Hidden", True),))
        if doc is None:
            print("Failed to load document.", file=sys.stderr)
            sys.exit(3)

        try:
            # 1) Read JSON payload
            try:
                data = json.load(open(payload_json_path, "r", encoding="utf-8"))
            except Exception:
                data = {}

            # 2) Write to Named Ranges on 'inputs' sheet
            #    (Names exactly as in your screenshot)
            mapping = {
                "student_name":   "student_name",
                "sex":            "sex",
                "status":         "status",
                "program":        "program",
                "years_of_stay":  "years_of_stay",
                "admission_date": "admission_date",
                "date_graduated": "date_graduated",
                "purpose":        "purpose",
                "purpose_other":  "purpose_other",
                "osahead":        "osahead",
            }
            for k, nr in mapping.items():
                _set_named_string(doc, nr, data.get(k, ""))

            # 3) Keep ONLY the GMF sheet visible, and make it active
            try:
                sheets = doc.getSheets()
                names = list(sheets.ElementNames)
                for nm in names:
                    sh = sheets.getByName(nm)
                    sh.IsVisible = (nm == "GMF")
                # Set active to GMF (avoids blank export on some builds)
                if "GMF" in names:
                    doc.getCurrentController().setActiveSheet(sheets.getByName("GMF"))
            except Exception:
                pass

            # 4) Recalculate formulas (GMF pulls from inputs!* via formulas)
            try: doc.calculateAll()
            except Exception: pass

            # 5) Export to PDF — by hiding other sheets, only GMF is exported
            export_props = (pv("FilterName", "calc_pdf_Export"),)
            doc.storeToURL(out_url, export_props)

        finally:
            try: doc.close(True)
            except Exception: pass
            try: os.remove(tmp_xlsx)
            except Exception: pass

    except Exception:
        traceback.print_exc()
        sys.exit(2)

if __name__ == "__main__":
    if len(sys.argv) != 4:
        print("Usage: lo_gmf_export.py <template.xlsx> <out.pdf> <payload.json>", file=sys.stderr)
        sys.exit(1)
    main(sys.argv[1], sys.argv[2], sys.argv[3])
