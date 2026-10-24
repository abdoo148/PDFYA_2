"""PDFYA (موقّع ومحوّل الملفات) من إنتاج Codpact — نقطة تشغيل البرنامج. الواجهة في مجلد gui والمنطق في core.py."""
import multiprocessing
import sys

if __name__ == "__main__":
    # OCR وتحويل PDF إلى Word يوزّعان الصفحات على عمليات منفصلة؛ في نسخة EXE تعيد كل عملية تشغيل البرنامج،
    # و freeze_support يحوّلها إلى عامل بدل فتح نافذة. الاستيراد الثقيل داخل الشرط حتى لا تحمّله العمليات العاملة.
    multiprocessing.freeze_support()
    from gui.main import run
    sys.exit(run())
