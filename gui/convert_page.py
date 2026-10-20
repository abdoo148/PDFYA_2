"""صفحة تحويل الملفات."""
import os
import webbrowser

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QComboBox, QFormLayout, QHBoxLayout, QSlider, QWidget

import core
from i18n import tr
from gui.operation import Op, OperationPage
from gui.widgets import IMG_EXTS, IMG_FILTER, PDF_FILTER, HelpBox, button, label, sub_progress

PDF = ((".pdf",), PDF_FILTER)
IMG = (IMG_EXTS, IMG_FILTER)
PDF_IMG = ((".pdf",) + IMG_EXTS, tr("PDF أو صور (*.pdf {0})", ' '.join('*' + e for e in IMG_EXTS)))
OFFICE_NOTE = (tr("<br><b>يتطلب:</b> Microsoft Office أو LibreOffice (مجاني) مثبتًا على الجهاز. إن لم يوجد أيٌّ منهما ستظهر رسالة توضح ذلك."))

OPS = [
    Op("pdf2word", tr("PDF إلى Word"), tr("مستند قابل للتعديل"),
       tr("يحوّل ملف PDF إلى مستند Word (.docx) يمكنك تعديله، مع الحفاظ على الفقرات والجداول والصور قدر الإمكان.<br><b>الناتج:</b> ملف بنفس الاسم بامتداد .docx.<br><b>تنبيه:</b> إذا كان الملف صورًا ممسوحة ضوئيًا فلن يظهر نص قابل للتعديل — استخدم «OCR إلى Word»."),
       *PDF, tr("حوّل إلى Word")),
    Op("word2pdf", tr("Word إلى PDF"), tr("ملفات docx و doc و rtf"),
       tr("يحوّل مستندات Word إلى PDF بنفس الشكل تمامًا.<br><b>الناتج:</b> ملف PDF بنفس الاسم.") + OFFICE_NOTE,
       (".docx", ".doc", ".rtf", ".odt"), tr("مستندات Word (*.docx *.doc *.rtf *.odt)"), tr("حوّل إلى PDF")),
    Op("excel2pdf", tr("Excel إلى PDF"), tr("ملفات xlsx و xls و csv"),
       tr("يحوّل ملفات Excel إلى PDF (كل الأوراق في الملف).<br><b>الناتج:</b> ملف PDF بنفس الاسم.") + OFFICE_NOTE,
       (".xlsx", ".xls", ".xlsm", ".csv"), tr("ملفات Excel (*.xlsx *.xls *.xlsm *.csv)"), tr("حوّل إلى PDF")),
    Op("ppt2pdf", tr("PowerPoint إلى PDF"), tr("عروض pptx و ppt"),
       tr("يحوّل العرض التقديمي إلى PDF، كل شريحة في صفحة.<br><b>الناتج:</b> ملف PDF بنفس الاسم.") + OFFICE_NOTE,
       (".pptx", ".ppt"), tr("عروض PowerPoint (*.pptx *.ppt)"), tr("حوّل إلى PDF")),
    Op("img2pdf", tr("صور إلى PDF"), tr("دمج الصور في ملف واحد"),
       tr("يجمع كل الصور في ملف PDF واحد، كل صورة في صفحة <b>بنفس ترتيب القائمة</b> (اسحب الملفات لتغيير الترتيب).<br><b>الناتج:</b> ملف «صور_مدمجة.pdf»."),
       *IMG, tr("أنشئ ملف PDF")),
    Op("pdf2img", tr("PDF إلى صور"), tr("صورة لكل صفحة"),
       tr("يحفظ كل صفحة من ملف PDF كصورة مستقلة.<br><b>الناتج:</b> صور باسم «الملف_صفحة_1» و«الملف_صفحة_2»...<br>اختر الدقة والصيغة من الإعدادات: 150 مناسبة للشاشة، و300 للطباعة."),
       *PDF, tr("حوّل إلى صور")),
    Op("pdf2xlsx", tr("PDF إلى Excel"), tr("استخراج الجداول"),
       tr("يبحث عن الجداول في كل صفحة ويضع كل جدول في ورقة Excel مستقلة، وتتحول الأرقام إلى أرقام قابلة للحساب.<br><b>يعمل مع:</b> ملفات PDF النصية التي فيها جداول واضحة الحدود. لا يعمل مع الملفات الممسوحة ضوئيًا."),
       *PDF, tr("استخرج الجداول")),
    Op("pdf2pptx", tr("PDF إلى PowerPoint"), tr("كل صفحة شريحة"),
       tr("ينشئ عرضًا تقديميًا تكون فيه كل صفحة شريحة. مناسب لعرض الملف على الشاشة.<br><b>تنبيه:</b> الشرائح صور، فلا يمكن تعديل النص داخلها."),
       *PDF, tr("حوّل إلى PowerPoint")),
    Op("ocr_pdf", tr("OCR: PDF قابل للبحث"), tr("للملفات الممسوحة ضوئيًا"),
       tr("يتعرّف على النص داخل الصفحات الممسوحة ضوئيًا (عربي وإنجليزي) ويضيفه للملف، فيصبح بإمكانك البحث فيه ونسخ النص منه، مع بقاء شكل الصفحات كما هو.<br><b>الناتج:</b> «الملف_قابل_للبحث.pdf». الصفحات التي فيها نص أصلًا تُنسخ كما هي."),
       *PDF_IMG, tr("ابدأ التعرف على النص")),
    Op("ocr_word", tr("OCR: إلى Word"), tr("نص قابل للتعديل من صورة"),
       tr("يستخرج النص من الملفات الممسوحة أو الصور إلى مستند Word قابل للتعديل (بدون التنسيق الأصلي).<br><b>الناتج:</b> «الملف_OCR.docx». راجع النص بعد التحويل، فقد تحدث أخطاء في الصور غير الواضحة."),
       *PDF_IMG, tr("ابدأ التعرف على النص")),
    Op("ocr_txt", tr("OCR: إلى نص"), tr("ملف نصي بسيط (txt)"),
       tr("يستخرج النص من الملفات الممسوحة أو الصور إلى ملف نصي بسيط، مع فاصل لكل صفحة.<br><b>الناتج:</b> «الملف_نص.txt»."),
       *PDF_IMG, tr("ابدأ التعرف على النص")),
]


class ConvertPage(OperationPage):
    def __init__(self):
        super().__init__(tr("تحويل الملفات"), tr("حوّل بين PDF وWord وExcel وPowerPoint والصور، واستخرج النص من الملفات الممسوحة."),
                         OPS)

    def build_options(self, key):
        if key == "pdf2img":
            w = QWidget()
            f = QFormLayout(w)
            f.setLabelAlignment(Qt.AlignRight)
            self.dpi = QComboBox()
            for d, t in ((96, tr("96 — صغيرة (للمعاينة)")), (150, tr("150 — مناسبة للشاشة")), (200, tr("200 — جودة عالية")),
                         (300, tr("300 — للطباعة (حجم أكبر)"))):
                self.dpi.addItem(t, d)
            self.dpi.setCurrentIndex(1)
            f.addRow(tr("الدقة (DPI):"), self.dpi)
            self.fmt = QComboBox()
            self.fmt.addItem(tr("PNG — جودة كاملة، حجم أكبر"), "png")
            self.fmt.addItem(tr("JPG — حجم أصغر"), "jpg")
            f.addRow(tr("الصيغة:"), self.fmt)
            q = QWidget()
            ql = QHBoxLayout(q)
            ql.setContentsMargins(0, 0, 0, 0)
            self.quality = QSlider(Qt.Horizontal)
            self.quality.setRange(40, 100)
            self.quality.setValue(85)
            self.q_lbl = label("85", wrap=False)
            self.quality.valueChanged.connect(lambda v: self.q_lbl.setText(str(v)))
            ql.addWidget(self.quality)
            ql.addWidget(self.q_lbl)
            f.addRow(tr("جودة JPG:"), q)
            self.fmt.currentIndexChanged.connect(lambda _: q.setEnabled(self.fmt.currentData() == "jpg"))
            q.setEnabled(False)
            return w
        if key.startswith("ocr"):
            # عمليات OCR الثلاث تشترك في نفس الإعدادات
            return self.ocr_box if hasattr(self, "ocr_box") else self._ocr_widget()
        return None

    def _ocr_widget(self):
        w = QWidget()
        f = QFormLayout(w)
        f.setLabelAlignment(Qt.AlignRight)
        self.ocr_lang = QComboBox()
        for name, code in core.OCR_LANGS.items():
            self.ocr_lang.addItem(name, code)
        self.ocr_lang.setToolTip(tr("اختر «عربي + إنجليزي» إذا كان الملف يحتوي اللغتين"))
        f.addRow(tr("لغة المستند:"), self.ocr_lang)
        self.ocr_dpi = QComboBox()
        for d, t in ((200, tr("200 — أسرع")), (300, tr("300 — موصى به")), (400, tr("400 — للخط الصغير (أبطأ)"))):
            self.ocr_dpi.addItem(t, d)
        self.ocr_dpi.setCurrentIndex(1)
        f.addRow(tr("الدقة:"), self.ocr_dpi)
        self.tess = HelpBox()
        f.addRow(self.tess)
        self.tess_btn = button(tr("فتح صفحة تنزيل Tesseract"), lambda: webbrowser.open(core.TESSERACT_URL))
        f.addRow(self.tess_btn)
        self.ocr_box = w
        return w

    def on_op(self, key):
        super().on_op(key)
        if key.startswith("ocr"):
            ok = core.find_tessdata() is not None
            self.tess.set_text(tr("✓ برنامج Tesseract مثبّت وجاهز.") if ok else
                               tr("<b>يحتاج برنامج Tesseract المجاني.</b> نزّله من الزر بالأسفل، واختر <b>Arabic</b> من قائمة اللغات أثناء التثبيت، ثم أعد تشغيل البرنامج."),
                               "info" if ok else "warn")
            self.tess_btn.setVisible(not ok)

    def validate(self, key, paths):
        if key.startswith("ocr") and core.find_tessdata() is None:
            return tr("التعرف على النص يحتاج برنامج Tesseract. اتبع التعليمات في قسم الإعدادات.")
        return None

    def make_job(self, key, paths):
        outrow = self.outrow
        dpi = self.dpi.currentData()
        fmt = self.fmt.currentData()
        quality = self.quality.value()
        lang = self.ocr_lang.currentData()
        ocr_dpi = self.ocr_dpi.currentData()

        def job(progress):
            if key == "img2pdf":
                od = outrow.for_file(paths[0])
                out = core.images_to_pdf(paths, core.unique_path(os.path.join(od, tr("صور_مدمجة.pdf"))), progress)
                return tr("تم إنشاء ملف PDF من {0} صورة: {1}", len(paths), out), out
            last, n = None, len(paths)
            for i, p in enumerate(paths):
                od, sub = outrow.for_file(p), sub_progress(progress, i, n)
                if key == "pdf2word":
                    last = core.pdf_to_word(p, od)
                elif key in ("word2pdf", "excel2pdf", "ppt2pdf"):
                    last = core.office_to_pdf(p, od)
                elif key == "pdf2img":
                    outs = core.pdf_to_images(p, od, dpi, fmt, quality, sub)
                    last = os.path.dirname(outs[-1])
                elif key == "pdf2xlsx":
                    last = core.pdf_to_excel(p, od, sub)
                elif key == "pdf2pptx":
                    last = core.pdf_to_pptx(p, od, progress=sub)
                elif key == "ocr_pdf":
                    last = core.ocr_pdf(p, od, lang, ocr_dpi, sub)
                elif key == "ocr_word":
                    last = core.ocr_to_word(p, od, lang, ocr_dpi, sub)
                elif key == "ocr_txt":
                    last = core.ocr_to_txt(p, od, lang, ocr_dpi, sub)
                progress(i + 1, n)
            what = tr("تم تحويل الملف") if n == 1 else tr("تم تحويل {0} ملفات", n)
            return tr("{0}. الناتج في: {1}", what, last if os.path.isdir(last) else os.path.dirname(last)), last

        return job
