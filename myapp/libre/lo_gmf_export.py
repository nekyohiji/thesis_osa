# lo_gmf_export.py
import shutil, uuid, os, sys, json, traceback, uno, officehelper
from com.sun.star.beans import PropertyValue

def pv(name, val):
    p = PropertyValue(); p.Name = name; p.Value = val; return p

def main(xlsx_path, out_pdf, payload_path):
    try:
        ctx = officehelper.bootstrap()
        smgr = ctx.getServiceManager()
        desk = smgr.createInstanceWithContext("com.sun.star.frame.Desktop", ctx)

        # Work on a unique temp copy to avoid any lock collisions
        tmp_dir  = os.path.dirname(os.path.abspath(out_pdf))
        tmp_copy = os.path.join(tmp_dir, f"gmf_{uuid.uuid4().hex}.xlsx")
        shutil.copy2(xlsx_path, tmp_copy)

        in_url  = uno.systemPathToFileUrl(tmp_copy)
        out_url = uno.systemPathToFileUrl(os.path.abspath(out_pdf))

        # Hidden + ReadOnly prevents LO from trying to create a lock
        doc = desk.loadComponentFromURL(in_url, "_blank", 0, (pv("Hidden", True), pv("ReadOnly", True)))
        if doc is None:
            print("Failed to load document.", file=sys.stderr)
            sys.exit(3)

        try:
            sheets = doc.getSheets()
            for nm in list(sheets.ElementNames):
                sh = sheets.getByName(nm)
                sh.IsVisible = (nm == "GMF")
            doc.getCurrentController().setActiveSheet(sheets.getByName("GMF"))

            data = json.load(open(payload_path, "r", encoding="utf-8"))
            # ... your existing set_named / calculateAll() code ...
            doc.storeToURL(out_url, (pv("FilterName", "calc_pdf_Export"),))
        finally:
            doc.close(True)
            try: os.remove(tmp_copy)
            except Exception: pass
    except Exception:
        traceback.print_exc()
        sys.exit(2)
