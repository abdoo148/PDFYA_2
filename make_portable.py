"""يضغط dist/PDFYA في نسخة محمولة: dist/installer/PDFYA-<الإصدار>-portable.zip"""
import os
import zipfile

import core

here = os.path.dirname(os.path.abspath(__file__))
src = os.path.join(here, "dist", core.APP_NAME)
out_dir = os.path.join(here, "dist", "installer")
os.makedirs(out_dir, exist_ok=True)
out = os.path.join(out_dir, f"{core.APP_NAME}-{core.APP_VERSION}-portable.zip")
with zipfile.ZipFile(out, "w", zipfile.ZIP_DEFLATED, compresslevel=6) as z:
    for root, _dirs, files in os.walk(src):
        for name in files:
            path = os.path.join(root, name)
            z.write(path, os.path.join(core.APP_NAME, os.path.relpath(path, src)))
print(out)
