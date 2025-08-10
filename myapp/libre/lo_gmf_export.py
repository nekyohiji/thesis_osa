import sys, json, os, traceback
import uno
import officehelper
from com.sun.star.beans import PropertyValue

def pv(name, val):
    p = PropertyValue(); p.Name = name; p.Value = val; return p

def set_named(doc, sheets, name, value):
    try:
        named = doc.NamedRanges
        if not named.hasByName(name):
            return
        nr = named.getByName(name)
        addr = nr.getReferredCells().getRangeAddress()
        sh = sheets.getByIndex(addr.Sheet)
        cell = sh.getCellByPosition(addr.StartColumn, addr.StartRow)
        cell.setString("" if value is None else str(value))
    except Exception:
        # leave quiet—missing names shouldn't break the run
        pass

def main(xlsx_path, out_pdf, payload_path):
    try:
        # 1) Bootstrap LibreOffice and get the global Desktop
        ctx = officehelper.bootstrap()  # launches soffice headless and returns a remote context
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
            for k in ["student_name","sex","status","program","years_of_stay",
                      "admission_date","date_graduated","purpose","purpose_other","osahead"]:
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
        traceback.print_exc()  # send full traceback to stderr
        sys.exit(2)

if __name__ == "__main__":
    if len(sys.argv) != 4:
        print("Usage: lo_gmf_export.py <xlsx_path> <out_pdf> <payload_json>", file=sys.stderr)
        sys.exit(1)
    main(sys.argv[1], sys.argv[2], sys.argv[3])
