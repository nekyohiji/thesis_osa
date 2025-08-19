from django.apps import AppConfig
import os, subprocess
from django.conf import settings
from pathlib import Path


class MyappConfig(AppConfig):
    name = "myapp"

    def ready(self):
        # Only when running the web server, not during migrations/collectstatic
        if any(cmd in os.sys.argv for cmd in ["runserver", "runserver_plus"]):
            lo_py = settings.LIBREOFFICE_PY
            if lo_py and Path(lo_py).exists():
                script = Path(__file__).with_name("libre").joinpath("lo_gmf_export.py")
                # a harmless call that just imports UNO; exits immediately on wrong argc
                try:
                    subprocess.Popen([str(lo_py), str(script)], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                except Exception:
                    pass