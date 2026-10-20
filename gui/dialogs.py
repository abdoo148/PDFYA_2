"""النوافذ المساعدة: رسم التوقيع، إضافة نص، مكتبة التواقيع، اختيار النوع، حول البرنامج."""
import os
import threading

from PIL import Image
from PySide6.QtCore import QObject, QPointF, QSize, Qt, QTimer, Signal
from PySide6.QtGui import QColor, QImage, QPainter, QPainterPath, QPen, QPixmap
from PySide6.QtWidgets import (
    QCheckBox, QComboBox, QDialog, QFileDialog, QHBoxLayout, QLabel, QListView, QListWidget,
    QListWidgetItem, QMessageBox, QPlainTextEdit, QSlider, QVBoxLayout, QWidget,
)

import core
from i18n import is_rtl, tr
from gui.widgets import (
    HelpBox, IMG_FILTER, app_icon, button, label, open_path, pil_to_pixmap, publisher_logo, resource,
    set_tone,
)

INKS = {tr("أزرق"): (20, 40, 120), tr("أسود"): (10, 10, 10), tr("أحمر"): (170, 20, 20)}


def load_signature_image(parent, path):
    """يفتح صورة توقيع/ختم ويزيل الخلفية البيضاء إن لم تكن شفافة."""
    try:
        img = Image.open(path).convert("RGBA")
        has_alpha = img.getextrema()[3][0] < 250
        return img if has_alpha else core.remove_white_bg(img)
    except Exception as e:  # noqa: BLE001
        QMessageBox.warning(parent, tr("تعذر فتح الصورة"),
                            tr("لم نتمكن من فتح الصورة:\n{0}\n\nتأكد أنها صورة سليمة بصيغة PNG أو JPG.\n\nالتفاصيل: {1}", os.path.basename(path), e))
        return None


def qimage_to_pil(qimg):
    qimg = qimg.convertToFormat(QImage.Format_RGBA8888)
    return Image.frombuffer("RGBA", (qimg.width(), qimg.height()), bytes(qimg.constBits()), "raw", "RGBA", 0, 1).copy()


class Dialog(QDialog):
    def __init__(self, parent, title):
        super().__init__(parent)
        self.setWindowTitle(title)
        self.setWindowIcon(app_icon())
        self.lay = QVBoxLayout(self)
        self.lay.setContentsMargins(20, 18, 20, 18)
        self.lay.setSpacing(12)


def ask_kind(parent, title=tr("حفظ في المكتبة كـ")):
    """يسأل عن نوع العنصر في المكتبة. يرجع المفتاح أو None."""
    dlg = Dialog(parent, title)
    dlg.lay.addWidget(label(tr("اختر تصنيف هذا العنصر حتى تجده بسهولة في المكتبة لاحقًا:")))
    row = QHBoxLayout()
    res = {"kind": None}
    for key, name in core.LIBRARY_KINDS.items():
        def pick(_=False, k=key):
            res["kind"] = k
            dlg.accept()
        row.addWidget(button(name, pick, "primary" if key == "signature" else None))
    dlg.lay.addLayout(row)
    dlg.exec()
    return res["kind"]


# ---------------------------------------------------------------- رسم التوقيع
class SignatureCanvas(QWidget):
    def __init__(self):
        super().__init__()
        self.setMinimumSize(620, 240)
        self.setCursor(Qt.CrossCursor)
        self.strokes = []  # [(QColor, width, [QPointF])]
        self.color = QColor(*INKS[tr("أزرق")])
        self.pen = 3.0

    def mousePressEvent(self, e):
        if e.button() == Qt.LeftButton:
            self.strokes.append((QColor(self.color), self.pen, [e.position()]))
            self.update()

    def mouseMoveEvent(self, e):
        if e.buttons() & Qt.LeftButton and self.strokes:
            self.strokes[-1][2].append(e.position())
            self.update()

    @staticmethod
    def _path(points):
        path = QPainterPath(points[0])
        if len(points) == 1:
            path.addEllipse(points[0], 0.6, 0.6)
            return path
        for a, b in zip(points, points[1:]):
            mid = QPointF((a.x() + b.x()) / 2, (a.y() + b.y()) / 2)
            path.quadTo(a, mid)
        path.lineTo(points[-1])
        return path

    def paint_strokes(self, p):
        p.setRenderHint(QPainter.Antialiasing)
        for color, width, pts in self.strokes:
            p.setPen(QPen(color, width, Qt.SolidLine, Qt.RoundCap, Qt.RoundJoin))
            p.drawPath(self._path(pts))

    def paintEvent(self, _e):
        p = QPainter(self)
        p.fillRect(self.rect(), QColor("white"))
        p.setPen(QPen(QColor("#C9CED6"), 1, Qt.DashLine))
        y = self.height() - 55
        p.drawLine(30, y, self.width() - 30, y)
        p.setPen(QColor("#A0A7B2"))
        p.drawText(30, y + 20, tr("وقّع فوق الخط"))
        self.paint_strokes(p)
        p.setPen(QPen(QColor("#B8BEC8"), 1))
        p.drawRect(self.rect().adjusted(0, 0, -1, -1))

    def to_image(self, scale=3):
        img = QImage(self.width() * scale, self.height() * scale, QImage.Format_ARGB32)
        img.fill(Qt.transparent)
        p = QPainter(img)
        p.scale(scale, scale)
        self.paint_strokes(p)
        p.end()
        pil = qimage_to_pil(img)
        bbox = pil.getbbox()
        return pil.crop(bbox) if bbox else None


class DrawDialog(Dialog):
    def __init__(self, parent, on_done):
        super().__init__(parent, tr("رسم التوقيع"))
        self.on_done = on_done
        self.lay.addWidget(HelpBox(tr("ارسم توقيعك بالماوس أو بقلم اللمس داخل المربع الأبيض. الخلفية ستكون شفافة تلقائيًا. استخدم «تراجع» لحذف آخر خط.")))
        self.canvas = SignatureCanvas()
        self.lay.addWidget(self.canvas, 1)

        opts = QHBoxLayout()
        opts.addWidget(label(tr("لون الحبر:"), wrap=False))
        ink = QComboBox()
        ink.addItems(list(INKS))
        ink.currentTextChanged.connect(lambda t: setattr(self.canvas, "color", QColor(*INKS[t])))
        opts.addWidget(ink)
        opts.addSpacing(16)
        opts.addWidget(label(tr("سُمك القلم:"), wrap=False))
        pen = QSlider(Qt.Horizontal)
        pen.setRange(15, 80)
        pen.setValue(30)
        pen.setFixedWidth(140)
        pen.valueChanged.connect(lambda v: setattr(self.canvas, "pen", v / 10))
        opts.addWidget(pen)
        opts.addSpacing(16)
        opts.addWidget(label(tr("حفظه في المكتبة كـ:"), wrap=False))
        self.save_as = QComboBox()
        self.save_as.addItem(tr("لا تحفظ"), None)
        for k, v in core.LIBRARY_KINDS.items():
            self.save_as.addItem(v, k)
        self.save_as.setToolTip(tr("الحفظ في المكتبة يتيح استخدام نفس التوقيع لاحقًا بدون رسمه مرة أخرى"))
        opts.addWidget(self.save_as)
        opts.addStretch(1)
        self.lay.addLayout(opts)

        row = QHBoxLayout()
        row.addWidget(button(tr("استخدام التوقيع"), self.finish, "primary", size="big"))
        row.addWidget(button(tr("تراجع (Ctrl+Z)"), self.undo))
        row.addWidget(button(tr("مسح الكل"), self.clear))
        row.addStretch(1)
        row.addWidget(button(tr("إلغاء"), self.reject))
        self.lay.addLayout(row)
        self.resize(720, 460)

    def keyPressEvent(self, e):
        if e.key() == Qt.Key_Z and e.modifiers() & Qt.ControlModifier:
            self.undo()
        else:
            super().keyPressEvent(e)

    def undo(self):
        if self.canvas.strokes:
            self.canvas.strokes.pop()
            self.canvas.update()

    def clear(self):
        self.canvas.strokes = []
        self.canvas.update()

    def finish(self):
        img = self.canvas.to_image()
        if img is None:
            QMessageBox.information(self, tr("لا يوجد توقيع"), tr("ارسم توقيعك داخل المربع الأبيض أولًا، ثم اضغط «استخدام التوقيع»."))
            return
        kind = self.save_as.currentData()
        if kind:
            core.library_save(img, kind)
        self.on_done(img, kind or "signature")
        self.accept()


# ---------------------------------------------------------------- إضافة نص
class TextDialog(Dialog):
    COLORS = {tr("أسود"): (10, 10, 10), tr("أزرق"): (20, 40, 120), tr("أحمر"): (170, 20, 20)}

    def __init__(self, parent, on_done):
        super().__init__(parent, tr("إضافة نص"))
        self.on_done = on_done
        self.lay.addWidget(HelpBox(tr("اكتب أي نص (اسم، صفة، «تمت الموافقة»...). يدعم العربية والإنجليزية وعدة أسطر. بعد الإضافة يمكنك تحريكه وتغيير حجمه على الصفحة.")))
        self.box = QPlainTextEdit()
        self.box.setPlaceholderText(tr("مثال: تمت المراجعة والموافقة"))
        self.box.setFixedHeight(90)
        if is_rtl():
            opt = self.box.document().defaultTextOption()
            opt.setTextDirection(Qt.RightToLeft)
            opt.setAlignment(Qt.AlignRight | Qt.AlignAbsolute)
            self.box.document().setDefaultTextOption(opt)
        self.box.textChanged.connect(self._schedule)
        self.lay.addWidget(self.box)
        row = QHBoxLayout()
        row.addWidget(label(tr("اللون:"), wrap=False))
        self.color = QComboBox()
        self.color.addItems(list(self.COLORS))
        self.color.currentTextChanged.connect(self._schedule)
        row.addWidget(self.color)
        self.bold = QCheckBox(tr("خط عريض"))
        self.bold.toggled.connect(self._schedule)
        row.addWidget(self.bold)
        row.addStretch(1)
        self.lay.addLayout(row)
        self.lay.addWidget(label(tr("معاينة:"), "muted"))
        self.preview = QLabel()
        self.preview.setAlignment(Qt.AlignCenter)
        self.preview.setMinimumHeight(90)
        self.preview.setObjectName("preview")
        self.lay.addWidget(self.preview)
        btns = QHBoxLayout()
        btns.addWidget(button(tr("إضافة إلى الصفحة"), self.finish, "primary", size="big"))
        btns.addStretch(1)
        btns.addWidget(button(tr("إلغاء"), self.reject))
        self.lay.addLayout(btns)
        self.timer = QTimer(self, singleShot=True, interval=250, timeout=self._render)
        self.img = None
        self.resize(520, 420)

    def _schedule(self):
        self.timer.start()

    def _make(self):
        return core.render_text_image(self.box.toPlainText(), self.COLORS[self.color.currentText()], self.bold.isChecked())

    def _render(self):
        text = self.box.toPlainText().strip()
        if not text:
            self.preview.clear()
            self.img = None
            return
        if not core.FITZ_LOCK.acquire(blocking=False):
            self.timer.start()
            return
        try:
            self.img = self._make()
        except Exception:  # noqa: BLE001
            self.img = None
        finally:
            core.FITZ_LOCK.release()
        if self.img:
            pm = pil_to_pixmap(self.img)
            self.preview.setPixmap(pm.scaled(QSize(460, 80), Qt.KeepAspectRatio, Qt.SmoothTransformation))

    def finish(self):
        if not self.box.toPlainText().strip():
            QMessageBox.information(self, tr("النص فارغ"), tr("اكتب النص الذي تريد إضافته أولًا."))
            return
        with core.FITZ_LOCK:
            try:
                img = self._make()
            except Exception as e:  # noqa: BLE001
                QMessageBox.warning(self, tr("تعذر إنشاء النص"), str(e))
                return
        self.on_done(img, "text")
        self.accept()


# ---------------------------------------------------------------- المكتبة
class LibraryDialog(Dialog):
    def __init__(self, parent, on_pick):
        super().__init__(parent, tr("مكتبة التواقيع والأختام"))
        self.on_pick = on_pick
        self.lay.addWidget(HelpBox(tr("هنا تواقيعك وأحرفك الأولى وأختامك المحفوظة. اضغط مرتين على أي عنصر لاستخدامه، أو اختره ثم «استخدام». المكتبة محفوظة على جهازك فقط.")))
        top = QHBoxLayout()
        top.addWidget(label(tr("عرض:"), wrap=False))
        self.filter = QComboBox()
        self.filter.addItem(tr("الكل"), None)
        for k, v in core.LIBRARY_KINDS.items():
            self.filter.addItem(v, k)
        self.filter.currentIndexChanged.connect(self.refresh)
        top.addWidget(self.filter)
        top.addStretch(1)
        top.addWidget(button(tr("＋ إضافة صورة للمكتبة"), self.add_image,
                             tip=tr("أضف صورة توقيع أو ختم من جهازك (تُزال الخلفية البيضاء تلقائيًا)")))
        self.lay.addLayout(top)
        self.list = QListWidget()
        self.list.setViewMode(QListView.IconMode)
        self.list.setIconSize(QSize(180, 80))
        self.list.setGridSize(QSize(205, 125))
        self.list.setResizeMode(QListView.Adjust)
        self.list.setMovement(QListView.Static)
        self.list.setWordWrap(True)
        self.list.itemDoubleClicked.connect(lambda _: self.use())
        self.list.itemSelectionChanged.connect(self._sel)
        self.lay.addWidget(self.list, 1)
        self.empty = label("", "muted")
        self.empty.setAlignment(Qt.AlignCenter)
        self.lay.addWidget(self.empty)
        row = QHBoxLayout()
        self.use_btn = button(tr("استخدام"), self.use, "primary", size="big")
        self.del_btn = button(tr("حذف من المكتبة"), self.delete, "danger")
        row.addWidget(self.use_btn)
        row.addWidget(self.del_btn)
        row.addStretch(1)
        row.addWidget(button(tr("إغلاق"), self.reject))
        self.lay.addLayout(row)
        self.resize(720, 540)
        self.refresh()

    def _sel(self):
        has = bool(self.list.selectedItems())
        self.use_btn.setEnabled(has)
        self.del_btn.setEnabled(has)

    def refresh(self):
        self.list.clear()
        kind = self.filter.currentData()
        items = [(p, k) for p, k in core.library_list() if kind in (None, k)]
        for path, k in items:
            try:
                img = Image.open(path).convert("RGBA")
            except OSError:
                continue
            bg = Image.new("RGBA", img.size, (255, 255, 255, 255))
            bg.alpha_composite(img)
            pm = pil_to_pixmap(bg).scaled(QSize(180, 80), Qt.KeepAspectRatio, Qt.SmoothTransformation)
            it = QListWidgetItem(pm, core.LIBRARY_KINDS[k])
            it.setData(Qt.UserRole, (path, k))
            self.list.addItem(it)
        self.empty.setText("" if items else
                           tr("المكتبة فارغة. احفظ توقيعًا من نافذة «رسم التوقيع» أو من زر «حفظ في المكتبة» بعد تحديد عنصر، أو أضف صورة من الزر بالأعلى."))
        self.empty.setVisible(not items)
        self._sel()

    def add_image(self):
        p, _ = QFileDialog.getOpenFileName(self, tr("اختر صورة توقيع أو ختم"), "", IMG_FILTER)
        if not p:
            return
        img = load_signature_image(self, p)
        if img is None:
            return
        kind = ask_kind(self)
        if kind:
            core.library_save(img, kind)
            self.refresh()

    def use(self):
        items = self.list.selectedItems()
        if not items:
            return
        path, kind = items[0].data(Qt.UserRole)
        self.on_pick(Image.open(path).convert("RGBA"), kind)
        self.accept()

    def delete(self):
        items = self.list.selectedItems()
        if items and QMessageBox.question(self, tr("تأكيد الحذف"), tr("حذف هذا العنصر من المكتبة نهائيًا؟")) == QMessageBox.Yes:
            core.library_delete(items[0].data(Qt.UserRole)[0])
            self.refresh()


# ---------------------------------------------------------------- حول البرنامج + التحديثات
class _UpdateBridge(QObject):
    done = Signal(object, str)


def run_update_check(parent, callback):
    """تحقق في الخلفية؛ callback(نتيجة أو None، رسالة خطأ) في الخيط الرئيسي."""
    bridge = _UpdateBridge(parent)
    bridge.done.connect(callback)

    def target():
        try:
            bridge.done.emit(core.check_for_update(), "")
        except Exception as e:  # noqa: BLE001
            bridge.done.emit(None, str(e) or e.__class__.__name__)

    threading.Thread(target=target, daemon=True).start()


class AboutDialog(Dialog):
    def __init__(self, parent, settings, on_update):
        super().__init__(parent, tr("حول البرنامج"))
        self.settings, self.on_update = settings, on_update
        png = resource("assets", "icon.png")
        if os.path.exists(png):
            ic = QLabel()
            ic.setPixmap(QPixmap(png).scaled(72, 72, Qt.KeepAspectRatio, Qt.SmoothTransformation))
            ic.setAlignment(Qt.AlignCenter)
            self.lay.addWidget(ic)
        t = label(core.APP_NAME, "h1")
        t.setAlignment(Qt.AlignCenter)
        self.lay.addWidget(t)
        v = label(tr("{0} — الإصدار {1}", core.APP_TAGLINE, core.APP_VERSION), "muted")
        v.setAlignment(Qt.AlignCenter)
        self.lay.addWidget(v)
        by = label(tr("من إنتاج {0}", core.PUBLISHER_AR), "h2")
        by.setAlignment(Qt.AlignCenter)
        self.lay.addWidget(by)
        self.lay.addWidget(publisher_logo(170, 120), 0, Qt.AlignHCenter)
        body = label(
            tr("برنامج مجاني لتوقيع ملفات PDF وتحويل الصيغ وأدوات PDF والتعرف على النص. يعمل بالكامل على جهازك، ولا تُرفع ملفاتك إلى أي مكان.<br><br><b>ملاحظة:</b> التوقيع هنا صورة مرسومة على الصفحة، وليس توقيعًا رقميًا معتمدًا بشهادة.<br><br>© 2026 {0}. برنامج حر مرخّص بـ GNU AGPL-3.0، والكود المصدري مرفق في مجلد <b>source</b> داخل مجلد التثبيت.", core.PUBLISHER_AR))
        body.setTextFormat(Qt.RichText)
        self.lay.addWidget(body)

        upd = QHBoxLayout()
        self.check_btn = button(tr("التحقق من التحديثات"), self.check)
        upd.addWidget(self.check_btn)
        self.auto = QCheckBox(tr("تحقق تلقائيًا عند التشغيل (مرة يوميًا)"))
        self.auto.setChecked(settings.get("auto_update", True))
        self.auto.toggled.connect(self._auto)
        upd.addWidget(self.auto)
        upd.addStretch(1)
        self.lay.addLayout(upd)
        self.upd_lbl = label("", "status")
        self.lay.addWidget(self.upd_lbl)
        if not core.update_url():
            self.check_btn.setEnabled(False)
            self.auto.setEnabled(False)
            self.upd_lbl.setText(tr("التحقق من التحديثات غير مفعّل في هذه النسخة."))

        row = QHBoxLayout()
        row.addWidget(button(tr("نص الترخيص"), lambda: open_path(resource("LICENSE.txt"))))
        row.addWidget(button(tr("المكتبات المستخدمة"), lambda: open_path(resource("THIRD_PARTY_NOTICES.txt"))))
        row.addStretch(1)
        row.addWidget(button(tr("إغلاق"), self.accept, "primary"))
        self.lay.addLayout(row)
        self.setFixedWidth(520)

    def _auto(self, on):
        self.settings["auto_update"] = on
        core.save_settings(self.settings)

    def check(self):
        self.check_btn.setEnabled(False)
        self.upd_lbl.setText(tr("جاري التحقق..."))

        def done(res, err):
            self.check_btn.setEnabled(True)
            if err:
                self.upd_lbl.setText(tr("تعذر التحقق: {0}\nتأكد من اتصال الإنترنت ثم حاول مرة أخرى.", err))
                set_tone(self.upd_lbl, "error")
            elif res["newer"]:
                self.upd_lbl.setText(tr("يتوفر الإصدار {0} — ستظهر رسالة أعلى النافذة برابط التنزيل.", res['version']))
                set_tone(self.upd_lbl, "ok")
                self.on_update(res)
            else:
                self.upd_lbl.setText(tr("لديك أحدث إصدار."))
                set_tone(self.upd_lbl, "ok")

        run_update_check(self, done)
