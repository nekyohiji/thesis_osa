import sys, json, os, traceback
import uno
import officehelper
from com.sun.star.beans import PropertyValue

def pv(name, val):
    p = PropertyValue(); p.Name = name; p.Value = val; return p

def is_na_like(value):
    """
    True if value looks like 'NA' in any case/format (NA, N/A, (NA), n.a., n - a, etc).
    Strategy: strip whitespace & common wrappers, remove non-alphanumerics, compare to 'na'.
    """
    if value is None:
        return False
    t = str(value).strip()
    # strip common single-layer wrappers like (), [], {}, quotes
    t = t.strip('()[]{}\'"').strip()
    compact = ''.join(ch for ch in t if ch.isalnum()).lower()
    return compact == 'na'

def set_named(doc, sheets, name, value):
    """
    Write a scalar string into a named range's top-left cell.
    If the name is extension- or middle-related and the value is NA-like, write blank.
    """
    try:
        # normalize NA-like middle/extension fields
        if name and name.lower() in ('ext', 'extension', 'suffix', 'middle_name', 'middlename', 'mname'):
            if is_na_like(value):
                value = ""

        named = doc.NamedRanges
        if not named.hasByName(name):
            return
        nr = named.getByName(name)
        addr = nr.getReferredCells().getRangeAddress()
        sh = sheets.getByIndex(addr.Sheet)
        cell = sh.getCellByPosition(addr.StartColumn, addr.StartRow)
        cell.setString("" if value is None else str(value))
    except Exception:
        # missing names shouldn't break the run
        pass

def build_student_name_from_parts(data):
    """
    Build 'student_name' from parts if available, skipping NA-like middle/ext.
    Returns None if insufficient data to build.
    """
    fn = (data.get('first_name') or '').strip()
    mn = (data.get('middle_name') or '').strip()
    sn = (data.get('surname') or '').strip()
    ex = (data.get('ext') or data.get('extension') or data.get('suffix') or '').strip()

    if not (fn or mn or sn or ex):
        return None

    if is_na_like(mn): mn = ""
    if is_na_like(ex): ex = ""

    parts = [p for p in (fn, mn, sn, ex) if p]
    return " ".join(parts).strip() or None

def main(xlsx_path, out_pdf, payload_path):
    try:
        # 1) Bootstrap LibreOffice and get the global Desktop
        ctx = officehelper.bootstrap()
        smgr = ctx.getServiceManager()
        desk = smgr.createInstanceWithContext("com.sun.star.frame.Desktop", ctx)

        # 2) Load workbook hidden
        in_url  = uno.systemPathToFileUrl(os.path.abspath(xlsx_path))
        out_url = uno.systemPathToFileUrl(os.path.abspath(out_pdf))
        doc = desk.loadComponentFromURL(in_url, "_blank", 0, (pv("Hidden", True),))
        if doc is None:
            print("Failed to load document.", file=sys.stderr)
            sys.exit(3)

        try:
            sheets = doc.getSheets()

            # show only GMF for export
            for nm in list(sheets.ElementNames):
                sh = sheets.getByName(nm)
                sh.IsVisible = (nm == "GMF")
            doc.getCurrentController().setActiveSheet(sheets.getByName("GMF"))

            # 3) Fill named ranges
            data = json.load(open(payload_path, "r", encoding="utf-8"))

            # sanitize NA-like fields in payload (defense in depth)
            for k in ('ext', 'extension', 'suffix', 'middle_name', 'middlename', 'mname'):
                if is_na_like(data.get(k)):
                    data[k] = ""

            # If student_name is missing/blank but we have parts, build it (skips NA-like middle/ext)
            if not (data.get('student_name') or '').strip():
                built = build_student_name_from_parts(data)
                if built:
                    data['student_name'] = built

            # write fields (safe: silently skips non-existent named ranges)
            for k in [
                "student_name","sex","status","program","years_of_stay",
                "admission_date","date_graduated","purpose","purpose_other","osahead",
                # optional named ranges if your sheet has them:
                "first_name","middle_name","surname","ext","extension","suffix"
            ]:
                set_named(doc, sheets, k, data.get(k))

            # 4) Recalculate so LET/TODAY etc update
            try:
                doc.calculateAll()
            except Exception:
                pass

            # 5) Export to PDF (GMF only is visible)
            doc.storeToURL(out_url, (pv("FilterName","calc_pdf_Export"),))
        finally:
            doc.close(True)
    except Exception:
        traceback.print_exc()
        sys.exit(2)

if __name__ == "__main__":
    if len(sys.argv) != 4:
        print("Usage: lo_gmf_export.py <xlsx_path> <out_pdf> <payload_json>", file=sys.stderr)
        sys.exit(1)
    main(sys.argv[1], sys.argv[2], sys.argv[3])
