"""عناصر واجهة مشتركة: بطاقات، شريط خطوات، قائمة ملفات بالسحب والإفلات، شريط تقدم مع إلغاء."""
import os
import sys
import threading

from PySide6.QtCore import QObject, QSize, Qt, Signal
from PySide6.QtGui import QIcon, QImage, QPixmap
from PySide6.QtWidgets import (
    QAbstractItemView, QFileDialog, QFrame, QGridLayout, QHBoxLayout, QLabel, QListWidget,
    QListWidgetItem, QMessageBox, QProgressBar, QPushButton, QSizePolicy, QStackedLayout,
    QVBoxLayout, QWidget,
)

import core
from i18n import is_rtl, tr


def STEP_DIGITS():
    return "١٢٣٤٥٦" if is_rtl() else "123456"


def arrow_fwd():
    """سهم «إلى» حسب اتجاه اللغة."""
    return "←" if is_rtl() else "→"

PDF_FILTER = tr("ملفات PDF (*.pdf)")
IMG_EXTS = (".png", ".jpg", ".jpeg", ".bmp", ".webp", ".tif", ".tiff")
IMG_FILTER = tr("صور (") + " ".join("*" + e for e in IMG_EXTS) + ")"


# ---------------------------------------------------------------- أدوات عامة
def resource(*parts):
    base = getattr(sys, "_MEIPASS", os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    return os.path.join(base, *parts)


def app_icon():
    ico = resource("assets", "icon.ico")
    return QIcon(ico) if os.path.exists(ico) else QIcon()


def publisher_logo(max_w, max_h):
    """شعار Codpact على خلفية بيضاء مستديرة (يناسب الوضعين الفاتح والداكن)."""
    lb = QLabel()
    lb.setObjectName("publisherLogo")
    pm = QPixmap(resource("assets", "codpact_logo.png"))
    if not pm.isNull():
        dpr = 2.0
        pm = pm.scaled(int(max_w * dpr), int(max_h * dpr), Qt.KeepAspectRatio, Qt.SmoothTransformation)
        pm.setDevicePixelRatio(dpr)
        lb.setPixmap(pm)
    else:
        lb.setText("Codpact")
    lb.setAlignment(Qt.AlignCenter)
    lb.setToolTip(tr("Codpact للحلول الرقمية"))
    return lb


def open_path(path):
    if path and os.path.exists(path) and hasattr(os, "startfile"):
        os.startfile(path)


def repolish(w):
    w.style().unpolish(w)
    w.style().polish(w)


def set_tone(w, tone):
    """يلوّن النص حسب الحالة (ok / error / warn / muted) عبر خاصية tone في الأنماط العامة."""
    w.setProperty("tone", tone)
    repolish(w)


def button(text, slot=None, kind=None, tip=None, size=None):
    b = QPushButton(text)
    if kind:
        b.setProperty("kind", kind)
    if size:
        b.setProperty("size", size)
    if tip:
        b.setToolTip(tip)
    if slot:
        b.clicked.connect(slot)
    b.setCursor(Qt.PointingHandCursor)
    return b


def label(text="", name=None, wrap=True):
    lb = QLabel(text)
    if name:
        lb.setObjectName(name)
    lb.setWordWrap(wrap)
    lb.setTextInteractionFlags(Qt.TextSelectableByMouse)
    return lb


def pil_to_pixmap(img):
    img = img.convert("RGBA")
    qimg = QImage(img.tobytes("raw", "RGBA"), img.width, img.height, 4 * img.width, QImage.Format_RGBA8888)
    return QPixmap.fromImage(qimg.copy())


def fitz_to_pixmap(pix):
    fmt = QImage.Format_RGBA8888 if pix.alpha else QImage.Format_RGB888
    qimg = QImage(pix.samples, pix.width, pix.height, pix.stride, fmt)
    return QPixmap.fromImage(qimg.copy())


def ext_of(path):
    return os.path.splitext(path)[1].lower()


def friendly_error(e):
    """يحوّل الأخطاء التقنية إلى رسالة مفهومة مع ما يجب فعله."""
    msg = str(e) or e.__class__.__name__
    if isinstance(e, PermissionError):
        return (tr("تعذر الكتابة أو القراءة: الملف مفتوح في برنامج آخر أو لا توجد صلاحية على المجلد. أغلق الملف (مثل Word أو قارئ PDF) أو اختر مجلد حفظ آخر، ثم حاول مرة أخرى."))
    if isinstance(e, FileNotFoundError):
        return tr("الملف غير موجود. ربما نُقل أو حُذف بعد إضافته — أضفه من جديد.")
    low = msg.lower()
    if "cannot open" in low or "no objects found" in low or "format error" in low or "broken" in low:
        return tr("تعذر قراءة الملف: قد يكون تالفًا أو ليس بالصيغة الصحيحة. جرّب فتحه في برنامج آخر للتأكد.")
    if "no space" in low:
        return tr("لا توجد مساحة كافية على القرص. احذف بعض الملفات أو اختر قرصًا آخر للحفظ.")
    return msg


def card(title=None, subtitle=None, spacing=10):
    """بطاقة بيضاء بعنوان اختياري. ترجع (الإطار، التخطيط الداخلي)."""
    fr = QFrame()
    fr.setObjectName("card")
    lay = QVBoxLayout(fr)
    lay.setContentsMargins(16, 14, 16, 16)
    lay.setSpacing(spacing)
    if title:
        lay.addWidget(label(title, "h2"))
    if subtitle:
        lay.addWidget(label(subtitle, "muted"))
    return fr, lay


class HelpBox(QFrame):
    """صندوق إرشاد: نص قصير يشرح ما يحدث وما يجب فعله."""

    def __init__(self, text="", tone="info"):
        super().__init__()
        self.setObjectName("help")
        self.setProperty("tone", tone)
        lay = QHBoxLayout(self)
        lay.setContentsMargins(12, 10, 12, 10)
        icon = QLabel("ⓘ" if tone == "info" else "⚠")
        icon.setObjectName("helpIcon")
        icon.setAlignment(Qt.AlignTop)
        lay.addWidget(icon)
        self.text = label(text)
        self.text.setTextFormat(Qt.RichText)
        lay.addWidget(self.text, 1)

    def set_text(self, text, tone=None):
        self.text.setText(text)
        if tone:
            self.setProperty("tone", tone)
            repolish(self)


class PageHeader(QWidget):
    def __init__(self, title, subtitle):
        super().__init__()
        lay = QVBoxLayout(self)
        lay.setContentsMargins(0, 0, 0, 4)
        lay.setSpacing(2)
        lay.addWidget(label(title, "h1"))
        lay.addWidget(label(subtitle, "subtitle"))


class StepBar(QWidget):
    """خطوات مرقّمة تُظهر للمستخدم أين هو الآن."""

    def __init__(self, steps):
        super().__init__()
        lay = QHBoxLayout(self)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.setSpacing(6)
        self.chips = []
        self.names = list(steps)
        for i, s in enumerate(steps):
            chip = QLabel(f"{STEP_DIGITS()[i]}  {s}")
            chip.setObjectName("step")
            lay.addWidget(chip)
            self.chips.append(chip)
            if i < len(steps) - 1:
                arrow = QLabel("←" if is_rtl() else "→")
                arrow.setObjectName("muted")
                lay.addWidget(arrow)
        lay.addStretch(1)

    def set_progress(self, done_flags):
        """done_flags: قائمة bool لكل خطوة. أول خطوة غير منجزة تصبح النشطة."""
        active = next((i for i, d in enumerate(done_flags) if not d), None)
        for i, chip in enumerate(self.chips):
            state = "done" if done_flags[i] else ("active" if i == active else "todo")
            chip.setText(("✓  " if done_flags[i] else f"{STEP_DIGITS()[i]}  ") + self.names[i])
            chip.setProperty("state", state)
            repolish(chip)


class TileGroup(QWidget):
    """بلاطات قابلة للاختيار (بديل القائمة المنسدلة) مع عنوان ووصف لكل خيار."""
    changed = Signal(str)

    def __init__(self, options, columns=4):
        """options: [(key, title, short_description)]"""
        super().__init__()
        grid = QGridLayout(self)
        grid.setContentsMargins(0, 0, 0, 0)
        grid.setSpacing(8)
        self.buttons = {}
        for i, (key, title, desc) in enumerate(options):
            b = QPushButton()
            b.setObjectName("tile")
            b.setCheckable(True)
            b.setAutoExclusive(True)
            b.setCursor(Qt.PointingHandCursor)
            b.setFixedHeight(66)
            b.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
            tl = QVBoxLayout(b)
            tl.setContentsMargins(12, 8, 12, 8)
            tl.setSpacing(2)
            for text, name in ((title, "tileTitle"), (desc, "tileDesc")):
                lb = QLabel(text)
                lb.setObjectName(name)
                lb.setAttribute(Qt.WA_TransparentForMouseEvents)
                tl.addWidget(lb)
            b.clicked.connect(lambda _=False, k=key: self.changed.emit(k))
            grid.addWidget(b, i // columns, i % columns)
            self.buttons[key] = b
        for c in range(columns):
            grid.setColumnStretch(c, 1)

    def select(self, key):
        self.buttons[key].setChecked(True)
        self.changed.emit(key)


# ---------------------------------------------------------------- قائمة الملفات
class FileList(QWidget):
    """قائمة ملفات: إضافة، حذف، ترتيب بالسحب، وسحب وإفلات من مستكشف ويندوز."""
    changed = Signal()

    def __init__(self, exts, filter_text, hint=""):
        super().__init__()
        self.exts, self.filter_text = tuple(exts), filter_text
        lay = QVBoxLayout(self)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.setSpacing(8)
        bar = QHBoxLayout()
        bar.addWidget(button(tr("＋ إضافة ملفات"), self.add, "primary", tr("اختر ملفًا أو أكثر من جهازك")))
        self.remove_btn = button(tr("حذف المحدد"), self.remove, tip=tr("يحذف الملف من القائمة فقط، ولا يحذفه من جهازك (أو اضغط Delete)"))
        bar.addWidget(self.remove_btn)
        bar.addWidget(button(tr("مسح القائمة"), self.clear, tip=tr("يفرّغ القائمة")))
        bar.addStretch(1)
        self.count = label("", "muted", wrap=False)
        bar.addWidget(self.count)
        lay.addLayout(bar)

        self.stack = QStackedLayout()
        self.list = QListWidget()
        self.list.setSelectionMode(QAbstractItemView.ExtendedSelection)
        self.list.setDragDropMode(QAbstractItemView.InternalMove)
        self.list.setMinimumHeight(150)
        self.list.model().rowsMoved.connect(lambda *a: self.changed.emit())
        self.list.keyPressEvent = self._key
        self.empty = QLabel()
        self.empty.setAlignment(Qt.AlignCenter)
        self.empty.setObjectName("dropZone")
        self.empty.setWordWrap(True)
        self.set_hint(hint)
        self.stack.addWidget(self.empty)
        self.stack.addWidget(self.list)
        holder = QWidget()
        holder.setLayout(self.stack)
        lay.addWidget(holder, 1)
        self.setAcceptDrops(True)
        self._refresh()

    def set_hint(self, hint):
        self.empty.setText(tr("اسحب الملفات من المستكشف وأفلتها هنا\nأو اضغط «＋ إضافة ملفات»")
                           + (f"\n\n{hint}" if hint else ""))

    def set_types(self, exts, filter_text, hint=""):
        self.exts, self.filter_text = tuple(exts), filter_text
        self.set_hint(hint)
        removed = [p for p in self.paths() if ext_of(p) not in self.exts]
        for p in removed:
            self._remove_path(p)
        self._refresh()

    def _key(self, e):
        if e.key() == Qt.Key_Delete:
            self.remove()
        else:
            QListWidget.keyPressEvent(self.list, e)

    def paths(self):
        return [self.list.item(i).data(Qt.UserRole) for i in range(self.list.count())]

    def selected_path(self):
        items = self.list.selectedItems()
        return items[0].data(Qt.UserRole) if items else None

    def add(self):
        files, _ = QFileDialog.getOpenFileNames(self, tr("اختر الملفات"), "", self.filter_text)
        self.add_paths(files)

    def add_paths(self, files):
        existing = set(self.paths())
        skipped = []
        for p in files:
            p = os.path.normpath(p)
            if ext_of(p) not in self.exts:
                skipped.append(os.path.basename(p))
            elif p not in existing:
                it = QListWidgetItem(f"{os.path.basename(p)}    —    {os.path.dirname(p)}")
                it.setData(Qt.UserRole, p)
                it.setToolTip(p)
                self.list.addItem(it)
                existing.add(p)
        self._refresh()
        if skipped:
            allowed = tr("، ").join(self.exts)
            QMessageBox.information(self, tr("ملفات غير مناسبة"),
                                    tr("تم تجاهل {0} ملف لأن صيغته لا تناسب هذه العملية:\n", len(skipped))
                                    + "\n".join(skipped[:6]) + tr("\n\nالصيغ المقبولة هنا: {0}", allowed))

    def _remove_path(self, p):
        for i in range(self.list.count()):
            if self.list.item(i).data(Qt.UserRole) == p:
                self.list.takeItem(i)
                return

    def remove(self):
        for it in self.list.selectedItems():
            self.list.takeItem(self.list.row(it))
        self._refresh()

    def clear(self):
        self.list.clear()
        self._refresh()

    def _refresh(self):
        n = self.list.count()
        self.stack.setCurrentIndex(1 if n else 0)
        self.count.setText(tr("{0} ملف — اسحب لتغيير الترتيب", n) if n > 1 else (tr("{0} ملف", n) if n else ""))
        self.remove_btn.setEnabled(n > 0)
        self.changed.emit()

    def dragEnterEvent(self, e):
        if e.mimeData().hasUrls():
            e.acceptProposedAction()

    def dropEvent(self, e):
        self.add_paths([u.toLocalFile() for u in e.mimeData().urls() if u.isLocalFile()])


class OutDirRow(QWidget):
    def __init__(self):
        super().__init__()
        self.dir = None
        lay = QHBoxLayout(self)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.addWidget(label(tr("مكان الحفظ:"), wrap=False))
        self.lbl = label(tr("نفس مجلد كل ملف أصلي"), "muted")
        lay.addWidget(self.lbl, 1)
        lay.addWidget(button(tr("تغيير..."), self.pick, tip=tr("اختر مجلدًا تُحفظ فيه كل الملفات الناتجة")))
        self.reset_btn = button(tr("إرجاع للافتراضي"), self.reset, "flat")
        self.reset_btn.hide()
        lay.addWidget(self.reset_btn)

    def pick(self):
        d = QFileDialog.getExistingDirectory(self, tr("اختر مجلد الحفظ"))
        if d:
            self.dir = os.path.normpath(d)
            self.lbl.setText(self.dir)
            self.reset_btn.show()

    def reset(self):
        self.dir = None
        self.lbl.setText(tr("نفس مجلد كل ملف أصلي"))
        self.reset_btn.hide()

    def for_file(self, path):
        return self.dir or os.path.dirname(path)


# ---------------------------------------------------------------- تشغيل في الخلفية
class _Bridge(QObject):
    progress = Signal(float)
    finished = Signal(str, str, str)  # النوع (ok/cancel/error)، الرسالة، المسار


def sub_progress(progress, i, n):
    """تقدم ملف واحد ضمن مجموعة."""
    return lambda done, total: progress(i + (done / total if total else 1), n)


class RunBar(QWidget):
    """تقدم بنسبة مئوية + إلغاء + رسالة النتيجة + زر فتح الناتج."""

    def __init__(self):
        super().__init__()
        self.busy = False
        self.cancelled = False
        self.result_path = None
        self.lock_widgets = []
        self.on_done = None
        self.bridge = _Bridge()
        self.bridge.progress.connect(self._show)
        self.bridge.finished.connect(self._finish)
        lay = QVBoxLayout(self)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.setSpacing(6)
        row = QHBoxLayout()
        self.bar = QProgressBar()
        self.bar.setRange(0, 1000)
        self.bar.setValue(0)
        self.bar.setFixedHeight(10)
        row.addWidget(self.bar, 1)
        self.pct = label("", "muted", wrap=False)
        self.pct.setMinimumWidth(42)
        row.addWidget(self.pct)
        self.cancel_btn = button(tr("إلغاء"), self.cancel, tip=tr("يوقف العملية بعد انتهاء الخطوة الحالية"))
        self.cancel_btn.hide()
        row.addWidget(self.cancel_btn)
        lay.addLayout(row)
        row2 = QHBoxLayout()
        self.status = label("", "status")
        self.status.setTextFormat(Qt.PlainText)
        row2.addWidget(self.status, 1)
        self.open_btn = button(tr("فتح الناتج"), lambda: open_path(self.result_path), "primary")
        self.folder_btn = button(tr("فتح المجلد"), self._open_folder)
        self.open_btn.hide()
        self.folder_btn.hide()
        row2.addWidget(self.folder_btn)
        row2.addWidget(self.open_btn)
        lay.addLayout(row2)
        self.bar.hide()

    def set_status(self, text, tone="muted"):
        set_tone(self.status, tone)
        self.status.setText(text)

    def _open_folder(self):
        p = self.result_path
        open_path(p if os.path.isdir(p) else os.path.dirname(p))

    def cancel(self):
        if self.busy:
            self.cancelled = True
            self.set_status(tr("جاري الإلغاء... سيتوقف بعد انتهاء الخطوة الحالية"), "warn")

    def run(self, job, start_text=tr("جاري التنفيذ...")):
        """job(progress) -> رسالة أو (رسالة، مسار الناتج). progress(done, total) يرفع Cancelled عند الإلغاء."""
        if self.busy:
            QMessageBox.information(self, tr("انتظر"), tr("هناك عملية قيد التنفيذ. انتظر حتى تنتهي أو اضغط «إلغاء»."))
            return
        self.busy, self.cancelled, self.result_path = True, False, None
        for w in self.lock_widgets:
            w.setEnabled(False)
        self.open_btn.hide()
        self.folder_btn.hide()
        self.cancel_btn.show()
        self.bar.show()
        self.bar.setRange(0, 0)  # غير محدد حتى أول تقدم
        self.pct.setText("")
        self.set_status(start_text)

        def progress(done, total):
            if self.cancelled:
                raise core.Cancelled()
            self.bridge.progress.emit(max(0.0, min(1.0, done / total)) if total else 0.0)

        def target():
            try:
                with core.FITZ_LOCK:
                    res = job(progress)
                msg, path = res if isinstance(res, tuple) else (res, None)
                self.bridge.finished.emit("ok", msg, path or "")
            except core.Cancelled:
                self.bridge.finished.emit("cancel", tr("تم إلغاء العملية. الملفات التي اكتملت قبل الإلغاء تبقى محفوظة."), "")
            except Exception as e:  # noqa: BLE001
                self.bridge.finished.emit("error", friendly_error(e), "")

        threading.Thread(target=target, daemon=True).start()

    def _show(self, frac):
        if self.bar.maximum() == 0:
            self.bar.setRange(0, 1000)
        self.bar.setValue(int(frac * 1000))
        self.pct.setText(f"{frac * 100:.0f}%")

    def _finish(self, kind, msg, path):
        self.busy = False
        self.cancel_btn.hide()
        self.bar.setRange(0, 1000)
        self.bar.setValue(1000 if kind == "ok" else 0)
        self.pct.setText("100%" if kind == "ok" else "")
        for w in self.lock_widgets:
            w.setEnabled(True)
        icon = {"ok": "✓ ", "cancel": "", "error": "✗ "}[kind]
        self.set_status(icon + msg, {"ok": "ok", "cancel": "warn", "error": "error"}[kind])
        if kind == "ok" and path and os.path.exists(path):
            self.result_path = path
            self.folder_btn.show()
            if os.path.isfile(path):
                self.open_btn.show()
        if self.on_done:
            self.on_done(kind, path)
