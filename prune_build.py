"""يحذف من dist/PDFYA ملفات Qt غير المستخدمة لتقليل الحجم (تُشغَّل بعد PyInstaller)."""
import os

here = os.path.dirname(os.path.abspath(__file__))
qt = os.path.join(here, "dist", "PDFYA", "_internal", "PySide6")
removed = 0
# OpenGL برمجي غير لازم لواجهة Widgets
p = os.path.join(qt, "opengl32sw.dll")
if os.path.exists(p):
    removed += os.path.getsize(p)
    os.remove(p)
# ترجمات Qt: نُبقي العربية فقط
tr = os.path.join(qt, "translations")
if os.path.isdir(tr):
    for name in os.listdir(tr):
        if not name.endswith("_ar.qm"):
            f = os.path.join(tr, name)
            removed += os.path.getsize(f)
            os.remove(f)
print(f"pruned {removed / 1024 / 1024:.1f} MB")
