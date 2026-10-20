"""صفحة تعديل PDF: تعديل نص موجود، إضافة نص وصور، تظليل وتسطير وشطب، رسم حر، أشكال، تبييض، حجب نهائي، ملاحظات."""
import os

try:
    import pymupdf as fitz
except ImportError:
    import fitz
from PySide6.QtCore import QPointF, QRectF, QSize, Qt, QTimer
from PySide6.QtGui import QBrush, QColor, QPainterPath, QPen, QTransform
from PySide6.QtWidgets import (
    QButtonGroup, QCheckBox, QComboBox, QFileDialog, QFormLayout, QGraphicsEllipseItem, QGraphicsItem,
    QGraphicsItemGroup, QGraphicsLineItem, QGraphicsPathItem, QGraphicsPixmapItem, QGraphicsRectItem,
    QGraphicsScene, QGraphicsView, QGridLayout, QHBoxLayout, QInputDialog, QLabel, QMessageBox, QPlainTextEdit,
    QPushButton, QScrollArea, QSpinBox, QStackedWidget, QVBoxLayout, QWidget,
)

import core
from i18n import is_rtl, tr
from gui.dialogs import Dialog, load_signature_image
from gui.widgets import (
    IMG_FILTER, PDF_FILTER, HelpBox, PageHeader, RunBar, StepBar, button, card, ext_of, fitz_to_pixmap, label,
    pil_to_pixmap,
)

# (المفتاح، الاسم، الإرشاد)
TOOLS = [
    ("select", tr("تحديد وتحريك"),
     tr("<b>تحديد وتحريك:</b> اضغط على أي تعديل أضفته لتحديده، واسحبه لتحريكه. اضغط مرتين على نص لتعديله. "
        "Delete يحذف المحدد، وCtrl+Z يتراجع عن آخر تعديل.")),
    ("edit_text", tr("تعديل نص موجود"),
     tr("<b>تعديل نص موجود:</b> اضغط على أي سطر في الصفحة لتغيير نصه. يُخفى النص الأصلي بخلفية بيضاء ويُكتب "
        "الجديد مكانه بنفس الحجم واللون. يعمل بأفضل شكل على الخلفيات البيضاء، ولا يعمل مع الصفحات الممسوحة ضوئيًا.")),
    ("text", tr("إضافة نص"),
     tr("<b>إضافة نص:</b> اضغط في المكان الذي تريد الكتابة فيه، ثم اكتب النص واختر الخط والحجم واللون.")),
    ("image", tr("إضافة صورة"),
     tr("<b>إضافة صورة:</b> اسحب مستطيلًا على الصفحة بالمكان والحجم المطلوب، ثم اختر الصورة من جهازك.")),
    ("highlight", tr("تظليل"), tr("<b>تظليل:</b> اسحب فوق الكلمات التي تريد تظليلها. اختر اللون من الخصائص.")),
    ("underline", tr("تسطير"), tr("<b>تسطير:</b> اسحب فوق الكلمات التي تريد وضع خط تحتها.")),
    ("strike", tr("شطب"), tr("<b>شطب:</b> اسحب فوق الكلمات التي تريد وضع خط في منتصفها.")),
    ("ink", tr("رسم حر"), tr("<b>رسم حر:</b> ارسم بالماوس أو القلم مباشرة على الصفحة. كل ضغطة تبدأ خطًا جديدًا.")),
    ("rect", tr("مستطيل"), tr("<b>مستطيل:</b> اسحب لرسم المستطيل. فعّل «تعبئة الشكل» لملئه باللون الأصفر.")),
    ("ellipse", tr("دائرة"), tr("<b>دائرة:</b> اسحب لرسم دائرة أو شكل بيضاوي.")),
    ("line", tr("خط"), tr("<b>خط:</b> اسحب من نقطة البداية إلى نقطة النهاية.")),
    ("arrow", tr("سهم"), tr("<b>سهم:</b> اسحب من بداية السهم إلى رأسه.")),
    ("whiteout", tr("تبييض (إخفاء)"),
     tr("<b>تبييض:</b> اسحب فوق أي جزء لتغطيته بالأبيض. يخفيه شكليًا فقط؛ النص الأصلي يبقى موجودًا داخل الملف. "
        "لحذف معلومات سرية فعليًا استخدم «حجب نهائي».")),
    ("redact", tr("حجب نهائي"),
     tr("<b>حجب نهائي:</b> اسحب فوق معلومات سرية لحذفها نهائيًا من الملف (النص والصور) وتغطيتها بالأسود. "
        "لا يمكن استرجاعها من الملف الناتج.")),
    ("note", tr("ملاحظة"),
     tr("<b>ملاحظة:</b> اضغط في أي مكان واكتب تعليقك. يظهر كأيقونة صغيرة يفتحها القارئ في أي برنامج PDF.")),
]
TOOL_HELP = {k: h for k, _n, h in TOOLS}
DRAG_TOOLS = {"image", "highlight", "underline", "strike", "rect", "ellipse", "line", "arrow", "whiteout", "redact"}
MOVABLE = {"text", "image", "ink", "rect", "ellipse", "line", "arrow", "whiteout", "redact", "note"}
KIND_NAMES = {k: n for k, n, _h in TOOLS}
KIND_NAMES["replace"] = tr("تعديل نص موجود")
COLORS = [(tr(name), rgb) for name, rgb in core.EDIT_COLORS.items()]
PREVIEW_SCALE = 3  # دقة معاينة النص مقارنة بحجمه الفعلي


def qcolor(rgb, alpha=255):
    return QColor(rgb[0], rgb[1], rgb[2], alpha)


# ---------------------------------------------------------------- نافذة النص
class EditTextDialog(Dialog):
    def __init__(self, parent, title, text="", size=14, color=(0, 0, 0), bold=False, font="Tahoma"):
        super().__init__(parent, title)
        self.lay.addWidget(HelpBox(tr("اكتب النص (يدعم العربية والإنجليزية وعدة أسطر)، ثم اختر شكله. "
                                      "النص العربي يُحاذى لليمين تلقائيًا.")))
        self.box = QPlainTextEdit(text)
        self.box.setFixedHeight(100)
        self.lay.addWidget(self.box)
        form = QFormLayout()
        self.font = QComboBox()
        self.font.addItems(list(core.TEXT_FONTS))
        self.font.setCurrentText(font if font in core.TEXT_FONTS else "Tahoma")
        form.addRow(tr("الخط:"), self.font)
        self.size = QSpinBox()
        self.size.setRange(5, 120)
        self.size.setValue(int(round(size)))
        self.size.setSuffix(tr(" نقطة"))
        form.addRow(tr("الحجم:"), self.size)
        self.color = QComboBox()
        for name, rgb in COLORS:
            self.color.addItem(name, rgb)
        idx = next((i for i, (_n, rgb) in enumerate(COLORS) if rgb == tuple(color)), -1)
        if idx < 0:
            self.color.addItem(tr("لون النص الأصلي"), tuple(color))
            idx = self.color.count() - 1
        self.color.setCurrentIndex(idx)
        form.addRow(tr("اللون:"), self.color)
        self.bold = QCheckBox(tr("خط عريض"))
        self.bold.setChecked(bold)
        form.addRow(self.bold)
        self.lay.addLayout(form)
        row = QHBoxLayout()
        row.addWidget(button(tr("موافق"), self._ok, "primary", size="big"))
        row.addStretch(1)
        row.addWidget(button(tr("إلغاء"), self.reject))
        self.lay.addLayout(row)
        self.resize(480, 360)
        self.result_data = None

    def _ok(self):
        text = self.box.toPlainText().strip()
        if not text:
            QMessageBox.information(self, tr("النص فارغ"), tr("اكتب النص أولًا."))
            return
        self.result_data = dict(text=text, size=self.size.value(), color=self.color.currentData(),
                                bold=self.bold.isChecked(), font=self.font.currentText())
        self.accept()


# ---------------------------------------------------------------- عرض الصفحة
class EditView(QGraphicsView):
    def __init__(self, page):
        super().__init__()
        self.page = page
        self.setTransformationAnchor(QGraphicsView.AnchorUnderMouse)
        self.setLayoutDirection(Qt.LeftToRight)
        self.setAcceptDrops(True)
        self.start = None
        self.temp = None
        self.path = None

    def _scene_pt(self, e):
        p = self.mapToScene(e.position().toPoint())
        return QPointF(min(max(p.x(), 0), self.page.page_w), min(max(p.y(), 0), self.page.page_h))

    def mousePressEvent(self, e):
        tool = self.page.tool
        if tool == "select" or e.button() != Qt.LeftButton or not self.page.doc:
            return super().mousePressEvent(e)
        p = self._scene_pt(e)
        if tool in DRAG_TOOLS:
            self.start = p
            if tool in ("line", "arrow"):
                self.temp = QGraphicsLineItem(p.x(), p.y(), p.x(), p.y())
            elif tool == "ellipse":
                self.temp = QGraphicsEllipseItem(QRectF(p, p))
            else:
                self.temp = QGraphicsRectItem(QRectF(p, p))
            pen = QPen(QColor(theme_accent()), 1, Qt.DashLine)
            pen.setCosmetic(True)
            self.temp.setPen(pen)
            self.temp.setZValue(100)
            self.page.scene.addItem(self.temp)
        elif tool == "ink":
            self.path = [p]
            self.temp = QGraphicsPathItem()
            self.temp.setZValue(100)
            pen = QPen(qcolor(self.page.color()), self.page.width.value(), Qt.SolidLine, Qt.RoundCap, Qt.RoundJoin)
            self.temp.setPen(pen)
            self.page.scene.addItem(self.temp)
        elif tool == "text":
            self.page.add_text_at(p)
        elif tool == "edit_text":
            self.page.edit_text_at(p)
        elif tool == "note":
            self.page.add_note_at(p)

    def mouseMoveEvent(self, e):
        if self.temp is None:
            return super().mouseMoveEvent(e)
        p = self._scene_pt(e)
        if self.path is not None:
            self.path.append(p)
            qp = QPainterPath(self.path[0])
            for q in self.path[1:]:
                qp.lineTo(q)
            self.temp.setPath(qp)
        elif isinstance(self.temp, QGraphicsLineItem):
            self.temp.setLine(self.start.x(), self.start.y(), p.x(), p.y())
        else:
            self.temp.setRect(QRectF(self.start, p).normalized())

    def mouseReleaseEvent(self, e):
        if self.temp is None:
            return super().mouseReleaseEvent(e)
        p = self._scene_pt(e)
        self.page.scene.removeItem(self.temp)
        self.temp = None
        if self.path is not None:
            pts, self.path = self.path, None
            if len(pts) > 1:
                self.page.add_edit(dict(type="ink", paths=[[(q.x(), q.y()) for q in pts]]))
            return
        start, self.start = self.start, None
        if self.page.tool in ("line", "arrow"):
            if (p - start).manhattanLength() > 4:
                self.page.add_edit(dict(type=self.page.tool, p1=(start.x(), start.y()), p2=(p.x(), p.y())))
            return
        r = QRectF(start, p).normalized()
        if r.width() < 4 or r.height() < 4:
            if self.page.tool in ("highlight", "underline", "strike"):
                r = QRectF(p.x() - 2, p.y() - 2, 4, 4)  # ضغطة واحدة = الكلمة تحت المؤشر
            else:
                return
        self.page.add_rect_edit(self.page.tool, (r.left(), r.top(), r.right(), r.bottom()))

    def mouseDoubleClickEvent(self, e):
        if self.page.tool == "select":
            item = self.itemAt(e.position().toPoint())
            edit = self.page.edit_for_item(item)
            if edit and edit["type"] in ("text", "replace"):
                self.page.reedit_text(edit)
                return
        super().mouseDoubleClickEvent(e)

    def wheelEvent(self, e):
        if e.modifiers() & Qt.ControlModifier:
            self.page.set_zoom(self.page.zoom * (1.15 if e.angleDelta().y() > 0 else 1 / 1.15))
        else:
            super().wheelEvent(e)

    def keyPressEvent(self, e):
        if e.key() == Qt.Key_Delete:
            self.page.delete_selected()
        elif e.key() == Qt.Key_Z and e.modifiers() & Qt.ControlModifier:
            self.page.undo()
        elif e.key() == Qt.Key_PageDown:
            self.page.go(1)
        elif e.key() == Qt.Key_PageUp:
            self.page.go(-1)
        else:
            super().keyPressEvent(e)

    def dragEnterEvent(self, e):
        if e.mimeData().hasUrls():
            e.acceptProposedAction()

    def dragMoveEvent(self, e):
        if e.mimeData().hasUrls():
            e.acceptProposedAction()

    def dropEvent(self, e):
        for u in e.mimeData().urls():
            if u.isLocalFile() and ext_of(u.toLocalFile()) == ".pdf":
                self.page.load_pdf(u.toLocalFile())
                return


def theme_accent():
    from gui import theme
    return theme.colors()["accent"]


# ---------------------------------------------------------------- الصفحة
class EditPage(QWidget):
    def __init__(self):
        super().__init__()
        self.doc = None
        self.pdf_path = None
        self.page_no = 0
        self.zoom = 1.0
        self.page_w = self.page_h = 1.0
        self.edits = []
        self.saved = False
        self.tool = "select"
        self._prev_tool = "select"
        self._pen_color = (0, 0, 0)
        self.setAcceptDrops(True)

        root = QVBoxLayout(self)
        root.setContentsMargins(24, 20, 24, 16)
        root.setSpacing(12)
        root.addWidget(PageHeader(tr("تعديل PDF"),
                                  tr("عدّل النصوص، وأضف نصوصًا وصورًا وتظليلًا وأشكالًا وملاحظات، أو احجب معلومات سرية. "
                                     "يُحفظ الناتج كملف جديد ولا يتغير الأصل.")))
        self.steps = StepBar([tr("افتح ملف PDF"), tr("اختر أداة"), tr("عدّل على الصفحة"), tr("احفظ الملف")])
        root.addWidget(self.steps)
        self.guide = HelpBox()
        root.addWidget(self.guide)

        body = QHBoxLayout()
        body.setSpacing(12)
        root.addLayout(body, 1)

        # ------------------------------------------------ اللوحة الجانبية
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFixedWidth(330)
        panel = QWidget()
        pl = QVBoxLayout(panel)
        pl.setContentsMargins(0, 0, 6, 0)
        pl.setSpacing(12)
        scroll.setWidget(panel)
        body.addWidget(scroll)

        c, l = card(tr("الملف"))
        l.addWidget(button(tr("فتح ملف PDF..."), self.open_pdf, "primary",
                           tr("اختر ملف PDF من جهازك (أو اسحبه إلى منطقة العرض)")))
        self.file_lbl = label(tr("لم يتم فتح ملف بعد"), "muted")
        l.addWidget(self.file_lbl)
        pl.addWidget(c)

        c, l = card(tr("الأدوات"))
        grid = QGridLayout()
        grid.setSpacing(6)
        self.tool_group = QButtonGroup(self)
        self.tool_group.setExclusive(True)
        self.tool_btns = {}
        for i, (key, name, _h) in enumerate(TOOLS):
            b = QPushButton(name)
            b.setCheckable(True)
            b.setObjectName("toolBtn")
            b.setCursor(Qt.PointingHandCursor)
            b.clicked.connect(lambda _=False, k=key: self.set_tool(k))
            self.tool_group.addButton(b)
            self.tool_btns[key] = b
            grid.addWidget(b, i // 2, i % 2)
        l.addLayout(grid)
        pl.addWidget(c)

        c, l = card(tr("الخصائص"))
        form = QFormLayout()
        self.color_box = QComboBox()
        for name, rgb in COLORS:
            self.color_box.addItem(name, rgb)
        form.addRow(tr("اللون:"), self.color_box)
        self.width = QSpinBox()
        self.width.setRange(1, 12)
        self.width.setValue(2)
        form.addRow(tr("سُمك الخط:"), self.width)
        self.fill = QCheckBox(tr("تعبئة الشكل (أصفر)"))
        form.addRow(self.fill)
        l.addLayout(form)
        pl.addWidget(c)

        c, l = card(tr("التعديلات"))
        self.count_lbl = label("", "muted")
        l.addWidget(self.count_lbl)
        row = QHBoxLayout()
        self.undo_btn = button(tr("تراجع (Ctrl+Z)"), self.undo)
        row.addWidget(self.undo_btn)
        self.del_btn = button(tr("حذف المحدد"), self.delete_selected, tip=tr("أو اضغط Delete"))
        row.addWidget(self.del_btn)
        l.addLayout(row)
        self.clear_btn = button(tr("إلغاء كل التعديلات"), self.clear_all, "danger")
        l.addWidget(self.clear_btn)
        pl.addWidget(c)

        c, l = card(tr("الحفظ"))
        self.save_btn = button(tr("حفظ الملف المعدّل..."), self.save, "success", size="big",
                               tip=tr("يحفظ نسخة جديدة بكل التعديلات، ولا يغيّر الملف الأصلي"))
        l.addWidget(self.save_btn)
        self.run = RunBar()
        self.run.lock_widgets = [self.save_btn]
        self.run.on_done = self._saved
        l.addWidget(self.run)
        pl.addWidget(c)
        pl.addStretch(1)

        # ------------------------------------------------ العرض
        viewer = QWidget()
        vl = QVBoxLayout(viewer)
        vl.setContentsMargins(0, 0, 0, 0)
        vl.setSpacing(8)
        tb = QHBoxLayout()
        self.prev_btn = button(tr("الصفحة السابقة"), lambda: self.go(-1), tip="PageUp")
        self.next_btn = button(tr("الصفحة التالية"), lambda: self.go(1), tip="PageDown")
        tb.addWidget(self.prev_btn)
        tb.addWidget(label(tr("صفحة"), wrap=False))
        self.page_spin = QSpinBox()
        self.page_spin.setMinimum(1)
        self.page_spin.valueChanged.connect(lambda v: self.goto(v - 1))
        tb.addWidget(self.page_spin)
        self.total_lbl = label(tr("من —"), wrap=False)
        tb.addWidget(self.total_lbl)
        tb.addWidget(self.next_btn)
        tb.addStretch(1)
        tb.addWidget(button("−", lambda: self.set_zoom(self.zoom / 1.2), tip=tr("تصغير (Ctrl + عجلة الماوس)")))
        self.zoom_lbl = label("", "muted", wrap=False)
        tb.addWidget(self.zoom_lbl)
        tb.addWidget(button("+", lambda: self.set_zoom(self.zoom * 1.2), tip=tr("تكبير (Ctrl + عجلة الماوس)")))
        tb.addWidget(button(tr("ملاءمة العرض"), self.fit_width, tip=tr("يجعل الصفحة بعرض منطقة العرض")))
        vl.addLayout(tb)

        self.stack = QStackedWidget()
        empty = QWidget()
        empty.setObjectName("emptyState")
        el = QVBoxLayout(empty)
        el.addStretch(1)
        for text, name in ((tr("لم يتم فتح ملف بعد"), "h2"),
                           (tr("اسحب ملف PDF من المستكشف وأفلته هنا، أو اضغط الزر بالأسفل"), "muted")):
            t = label(text, name)
            t.setAlignment(Qt.AlignCenter)
            el.addWidget(t)
        bl = QHBoxLayout()
        bl.addStretch(1)
        bl.addWidget(button(tr("فتح ملف PDF..."), self.open_pdf, "primary", size="big"))
        bl.addStretch(1)
        el.addLayout(bl)
        el.addStretch(1)
        self.stack.addWidget(empty)
        self.scene = QGraphicsScene()
        self.scene.selectionChanged.connect(self._update_panel)
        self.view = EditView(self)
        self.view.setScene(self.scene)
        self.stack.addWidget(self.view)
        vl.addWidget(self.stack, 1)
        body.addWidget(viewer, 1)

        self.render_timer = QTimer(self, singleShot=True, interval=120, timeout=self.render_page)
        self.set_tool("select")

    # ================================================================ الملف والعرض
    def dragEnterEvent(self, e):
        if e.mimeData().hasUrls():
            e.acceptProposedAction()

    def dropEvent(self, e):
        for u in e.mimeData().urls():
            if u.isLocalFile() and ext_of(u.toLocalFile()) == ".pdf":
                self.load_pdf(u.toLocalFile())
                return

    def open_pdf(self):
        p, _ = QFileDialog.getOpenFileName(self, tr("اختر ملف PDF"), "", PDF_FILTER)
        if p:
            self.load_pdf(p)

    def _confirm_discard(self):
        if not self.edits or self.saved:
            return True
        return QMessageBox.question(self, tr("تعديلات غير محفوظة"),
                                    tr("لديك تعديلات لم تُحفظ على الملف الحالي. هل تريد تجاهلها وفتح ملف آخر؟")) \
            == QMessageBox.Yes

    def load_pdf(self, p):
        if not self._confirm_discard():
            return
        if not core.FITZ_LOCK.acquire(timeout=1):
            QMessageBox.information(self, tr("انتظر"), tr("هناك عملية قيد التنفيذ. انتظر حتى تنتهي ثم افتح الملف."))
            return
        try:
            d = fitz.open(p)
            if d.needs_pass:
                d.close()
                QMessageBox.warning(self, tr("الملف محمي بكلمة مرور"),
                                    tr("لا يمكن تعديل ملف محمي بكلمة مرور.\n\n"
                                       "أزل الحماية أولًا من: أدوات PDF ← إزالة كلمة المرور، ثم افتح الملف الناتج."))
                return
        except Exception as e:  # noqa: BLE001
            QMessageBox.warning(self, tr("تعذر فتح الملف"),
                                tr("لم نتمكن من فتح:\n{0}\n\nقد يكون الملف تالفًا أو ليس PDF.\n\nالتفاصيل: {1}",
                                   os.path.basename(p), e))
            return
        finally:
            core.FITZ_LOCK.release()
        if self.doc:
            self.doc.close()
        self.doc, self.pdf_path, self.page_no = d, p, 0
        self.edits, self.saved = [], False
        self.file_lbl.setText(tr("{0}\n{1} صفحة", os.path.basename(p), len(d)))
        self.file_lbl.setToolTip(p)
        self.page_spin.blockSignals(True)
        self.page_spin.setMaximum(len(d))
        self.page_spin.setValue(1)
        self.page_spin.blockSignals(False)
        self.total_lbl.setText(tr("من {0}", len(d)))
        self.stack.setCurrentIndex(1)
        if self.tool == "select":
            self.set_tool("edit_text")
        QTimer.singleShot(0, lambda: (self.fit_width(render=False), self.render_page()))

    def go(self, d):
        self.goto(self.page_no + d)

    def goto(self, i):
        if self.doc and 0 <= i < len(self.doc) and i != self.page_no:
            self._store_offsets()
            self.page_no = i
            self.render_page()

    def fit_width(self, render=True):
        if self.doc:
            avail = max(200, self.view.viewport().width() - 40)
            self.set_zoom(avail / self.doc[self.page_no].rect.width, render)

    def set_zoom(self, z, render=True):
        if not self.doc:
            return
        self.zoom = max(0.25, min(5.0, z))
        self.view.setTransform(QTransform.fromScale(self.zoom, self.zoom))
        self.zoom_lbl.setText(f"{self.zoom * 100:.0f}%")
        if render:
            self.render_timer.start()

    def render_page(self):
        if not self.doc:
            return
        if not core.FITZ_LOCK.acquire(blocking=False):
            self.render_timer.start(250)
            return
        try:
            page = self.doc[self.page_no]
            self.page_w, self.page_h = page.rect.width, page.rect.height
            s = min(4.0, self.zoom * self.devicePixelRatioF())
            pix = page.get_pixmap(matrix=fitz.Matrix(s, s), alpha=False)
        finally:
            core.FITZ_LOCK.release()
        self._store_offsets()
        for e in self.edits:
            e.pop("item", None)
        self.scene.clear()
        shadow = QGraphicsRectItem(3, 3, self.page_w, self.page_h)
        shadow.setBrush(QColor(0, 0, 0, 50))
        shadow.setPen(Qt.NoPen)
        self.scene.addItem(shadow)
        pm = QGraphicsPixmapItem(fitz_to_pixmap(pix))
        pm.setTransformationMode(Qt.SmoothTransformation)
        pm.setScale(1 / s)
        self.scene.addItem(pm)
        self.scene.setSceneRect(QRectF(-20, -20, self.page_w + 40, self.page_h + 40))
        self.page_spin.blockSignals(True)
        self.page_spin.setValue(self.page_no + 1)
        self.page_spin.blockSignals(False)
        self.prev_btn.setEnabled(self.page_no > 0)
        self.next_btn.setEnabled(self.page_no < len(self.doc) - 1)
        for e in self.edits:
            if e["page"] == self.page_no:
                self._make_item(e)
        self._update_panel()

    # ================================================================ الأدوات
    def set_tool(self, key):
        self.tool = key
        self.tool_btns[key].setChecked(True)
        self.view.setCursor(Qt.ArrowCursor if key == "select" else
                            Qt.IBeamCursor if key in ("text", "edit_text") else Qt.CrossCursor)
        for e in self.edits:
            it = e.get("item")
            if it is not None:
                it.setFlag(QGraphicsItem.ItemIsMovable, key == "select" and e["type"] in MOVABLE)
                it.setFlag(QGraphicsItem.ItemIsSelectable, key == "select")
        if key != "select":
            self.scene.clearSelection()
        self.fill.setEnabled(key in ("rect", "ellipse"))
        # التظليل أصفر افتراضيًا، وعند الخروج منه يعود اللون الذي اختاره المستخدم لباقي الأدوات
        if key == "highlight":
            if self._prev_tool != "highlight":
                self._pen_color = self.color()
            self._select_color((255, 214, 0))
        elif self._prev_tool == "highlight":
            self._select_color(self._pen_color)
        self._prev_tool = key
        self._update_panel()

    def _select_color(self, rgb):
        for i in range(self.color_box.count()):
            if tuple(self.color_box.itemData(i)) == tuple(rgb):
                self.color_box.setCurrentIndex(i)
                return

    def color(self):
        return tuple(self.color_box.currentData())

    # ================================================================ إنشاء التعديلات
    def add_edit(self, edit):
        if edit["type"] not in ("whiteout", "redact", "image"):
            edit.setdefault("color", self.color())
        if edit["type"] in ("ink", "rect", "ellipse", "line", "arrow"):
            edit.setdefault("width", self.width.value())
        if edit["type"] in ("rect", "ellipse") and self.fill.isChecked():
            edit["fill"] = (255, 214, 0)
        edit["page"] = self.page_no
        edit["dx"] = edit["dy"] = 0.0
        self.edits.append(edit)
        self.saved = False
        self._make_item(edit)
        self._update_panel()

    def add_rect_edit(self, tool, rect):
        if tool == "image":
            p, _ = QFileDialog.getOpenFileName(self, tr("اختر صورة"), "", IMG_FILTER)
            if not p:
                return
            try:
                from PIL import Image
                img = Image.open(p).convert("RGBA")
            except Exception:  # noqa: BLE001
                load_signature_image(self, p)  # يعرض رسالة الخطأ المناسبة
                return
            x0, y0, x1, y1 = rect
            ratio = img.height / img.width
            w, h = x1 - x0, y1 - y0
            if h / w > ratio:  # ملاءمة الصورة داخل المستطيل مع الحفاظ على النسبة
                h = w * ratio
            else:
                w = h / ratio
            self.add_edit(dict(type="image", rect=(x0, y0, x0 + w, y0 + h), png=core.image_to_png_bytes(img),
                               pil=img))
            return
        self.add_edit(dict(type=tool, rect=rect))

    def add_text_at(self, p):
        dlg = EditTextDialog(self, tr("إضافة نص"), color=self.color() if self.color() != (255, 255, 255) else (0, 0, 0))
        if not dlg.exec() or not dlg.result_data:
            return
        d = dlg.result_data
        w, h = self._text_size(d)
        self.add_edit(dict(type="text", rect=(p.x(), p.y(), p.x() + w, p.y() + h), **d))

    def edit_text_at(self, p):
        with core.FITZ_LOCK:
            line = core.text_line_at(self.doc[self.page_no], (p.x(), p.y()))
        if not line:
            QMessageBox.information(self, tr("لا يوجد نص هنا"),
                                    tr("لم نجد نصًا قابلًا للتعديل في هذا المكان. اضغط مباشرة على سطر مكتوب.\n\n"
                                       "إذا كانت الصفحة ممسوحة ضوئيًا (صورة) فلا يوجد نص لتعديله — استخدم «تبييض» ثم "
                                       "«إضافة نص»، أو حوّل الملف أولًا بأداة OCR."))
            return
        font = "Times New Roman" if "times" in line["font"].lower() else \
            "Courier New" if "cour" in line["font"].lower() else \
            "Arial" if "arial" in line["font"].lower() or "helv" in line["font"].lower() else "Tahoma"
        dlg = EditTextDialog(self, tr("تعديل نص موجود"), line["text"], line["size"], line["color"], line["bold"], font)
        if not dlg.exec() or not dlg.result_data:
            return
        e = dict(type="replace", rect=line["rect"], **dlg.result_data)
        e["trect"] = self._replace_text_rect(e)
        self.add_edit(e)

    def reedit_text(self, edit):
        dlg = EditTextDialog(self, tr("تعديل النص"), edit["text"], edit["size"], edit["color"], edit["bold"],
                             edit["font"])
        if not dlg.exec() or not dlg.result_data:
            return
        edit.update(dlg.result_data)
        if edit["type"] == "text":
            x0, y0 = edit["rect"][0], edit["rect"][1]
            w, h = self._text_size(dlg.result_data)
            edit["rect"] = (x0, y0, x0 + w, y0 + h)
        else:
            edit["trect"] = self._replace_text_rect(edit)
        self.saved = False
        self._rebuild_item(edit)

    def _replace_text_rect(self, e):
        """مكان النص البديل: يبدأ من نفس حافة السطر الأصلي ويتمدد حسب طول النص الجديد."""
        x0, y0, x1, y1 = e["rect"]
        w, h = self._text_size(e)
        w, h = max(w, x1 - x0), max(h, y1 - y0)
        if core._has_arabic(e["text"]):
            return (x1 - w, y0, x1, y0 + h)
        return (x0, y0, x0 + w, y0 + h)

    def add_note_at(self, p):
        text, ok = QInputDialog.getMultiLineText(self, tr("ملاحظة"), tr("اكتب الملاحظة:"))
        if ok and text.strip():
            self.add_edit(dict(type="note", point=(p.x(), p.y()), text=text.strip()))

    def _render_text(self, d):
        with core.FITZ_LOCK:
            align = "right" if core._has_arabic(d["text"]) else "left"
            return core.render_text_image(d["text"], d["color"], d["bold"], px=d["size"] * PREVIEW_SCALE,
                                          font=d["font"], align=align)

    def _text_size(self, d):
        img = self._render_text(d)
        return img.width / PREVIEW_SCALE + 4, img.height / PREVIEW_SCALE + 2

    # ================================================================ رسم التعديلات على الشاشة
    def _make_item(self, e):
        t = e["type"]
        col = qcolor(e.get("color", (0, 0, 0)))
        pen = QPen(col, e.get("width", 2))
        if t in ("text", "replace"):
            group = QGraphicsItemGroup()
            x0, y0, x1, y1 = e["rect"]
            if t == "replace":
                cover = QGraphicsRectItem(QRectF(x0 - 1, y0 - 1, x1 - x0 + 2, y1 - y0 + 2))
                cover.setBrush(QColor("white"))
                cover.setPen(Qt.NoPen)
                group.addToGroup(cover)
            img = self._render_text(e)
            pm = QGraphicsPixmapItem(pil_to_pixmap(img))
            pm.setTransformationMode(Qt.SmoothTransformation)
            pm.setScale(1 / PREVIEW_SCALE)
            w = img.width / PREVIEW_SCALE
            tx0, ty0, tx1, _ty1 = e.get("trect", e["rect"])
            pm.setPos(tx1 - w if core._has_arabic(e["text"]) else tx0, ty0)
            group.addToGroup(pm)
            item = group
        elif t == "image":
            x0, y0, x1, y1 = e["rect"]
            pmap = pil_to_pixmap(e["pil"])
            item = QGraphicsPixmapItem(pmap)
            item.setTransformationMode(Qt.SmoothTransformation)
            item.setScale((x1 - x0) / pmap.width())
            item.setOffset(x0 / item.scale(), y0 / item.scale())
        elif t in ("highlight", "underline", "strike"):
            item = QGraphicsItemGroup()
            with core.FITZ_LOCK:
                words = core.words_in_rect(self.doc[self.page_no], e["rect"]) or [e["rect"]]
            for (x0, y0, x1, y1) in words:
                if t == "highlight":
                    r = QGraphicsRectItem(QRectF(x0, y0, x1 - x0, y1 - y0))
                    r.setBrush(qcolor(e["color"], 110))
                    r.setPen(Qt.NoPen)
                else:
                    y = y1 - (y1 - y0) * 0.12 if t == "underline" else (y0 + y1) / 2
                    r = QGraphicsLineItem(x0, y, x1, y)
                    p = QPen(col, max(1.0, (y1 - y0) * 0.07))
                    r.setPen(p)
                item.addToGroup(r)
        elif t == "ink":
            qp = QPainterPath()
            for path in e["paths"]:
                qp.moveTo(*path[0])
                for pt in path[1:]:
                    qp.lineTo(*pt)
            item = QGraphicsPathItem(qp)
            pen.setCapStyle(Qt.RoundCap)
            pen.setJoinStyle(Qt.RoundJoin)
            item.setPen(pen)
        elif t in ("rect", "ellipse", "whiteout", "redact"):
            x0, y0, x1, y1 = e["rect"]
            r = QRectF(x0, y0, x1 - x0, y1 - y0)
            item = QGraphicsEllipseItem(r) if t == "ellipse" else QGraphicsRectItem(r)
            if t == "whiteout":
                item.setBrush(QColor("white"))
                p = QPen(QColor("#B0B6C0"), 1, Qt.DotLine)
                p.setCosmetic(True)
                item.setPen(p)
            elif t == "redact":
                item.setBrush(QColor("black"))
                p = QPen(QColor("#E05252"), 1.5, Qt.DashLine)
                p.setCosmetic(True)
                item.setPen(p)
            else:
                item.setPen(pen)
                if e.get("fill"):
                    item.setBrush(qcolor(e["fill"], 160))
        elif t in ("line", "arrow"):
            (x0, y0), (x1, y1) = e["p1"], e["p2"]
            item = QGraphicsItemGroup()
            ln = QGraphicsLineItem(x0, y0, x1, y1)
            ln.setPen(pen)
            item.addToGroup(ln)
            if t == "arrow":
                import math
                ang = math.atan2(y1 - y0, x1 - x0)
                size = 6 + e.get("width", 2) * 2
                path = QPainterPath(QPointF(x1, y1))
                for da in (2.6, -2.6):
                    path.lineTo(x1 + size * math.cos(ang + da), y1 + size * math.sin(ang + da))
                path.closeSubpath()
                head = QGraphicsPathItem(path)
                head.setBrush(col)
                head.setPen(QPen(col, 1))
                item.addToGroup(head)
        elif t == "note":
            x, y = e["point"]
            item = QGraphicsRectItem(QRectF(x, y, 16, 16))
            item.setBrush(qcolor(e.get("color", (255, 214, 0))))
            item.setPen(QPen(QColor("#7A6200"), 1))
            item.setToolTip(e["text"])
        else:
            return
        item.setZValue(10)
        item.setPos(e.get("dx", 0), e.get("dy", 0))
        item.setFlag(QGraphicsItem.ItemIsSelectable, self.tool == "select")
        item.setFlag(QGraphicsItem.ItemIsMovable, self.tool == "select" and t in MOVABLE)
        if t not in ("note",):
            item.setToolTip(KIND_NAMES.get(t, ""))
        self.scene.addItem(item)
        e["item"] = item

    def _rebuild_item(self, e):
        it = e.pop("item", None)
        if it is not None:
            e["dx"], e["dy"] = it.pos().x(), it.pos().y()
            self.scene.removeItem(it)
        self._make_item(e)
        self._update_panel()

    def _store_offsets(self):
        for e in self.edits:
            it = e.get("item")
            if it is not None:
                try:
                    e["dx"], e["dy"] = it.pos().x(), it.pos().y()
                except RuntimeError:
                    pass

    def edit_for_item(self, item):
        while item is not None and item.parentItem() is not None:
            item = item.parentItem()
        return next((e for e in self.edits if e.get("item") is item), None) if item else None

    # ================================================================ إدارة التعديلات
    def undo(self):
        if self.edits:
            e = self.edits.pop()
            if e.get("item") is not None:
                self.scene.removeItem(e["item"])
            if e["page"] != self.page_no:
                self.goto(e["page"])
            self.saved = False
            self._update_panel()

    def delete_selected(self):
        sel = [self.edit_for_item(it) for it in self.scene.selectedItems()]
        sel = [e for e in sel if e]
        for e in sel:
            self.scene.removeItem(e["item"])
            self.edits.remove(e)
        if sel:
            self.saved = False
            self._update_panel()

    def clear_all(self):
        if self.edits and QMessageBox.question(self, tr("تأكيد"), tr("إلغاء كل التعديلات على هذا الملف؟")) \
                == QMessageBox.Yes:
            self.edits = []
            self.render_page()

    def _update_panel(self):
        n = len(self.edits)
        here = sum(1 for e in self.edits if e["page"] == self.page_no)
        self.count_lbl.setText(tr("{0} تعديل في الملف ({1} في هذه الصفحة).", n, here) if n else tr("لا توجد تعديلات بعد."))
        self.undo_btn.setEnabled(n > 0)
        self.clear_btn.setEnabled(n > 0)
        self.del_btn.setEnabled(bool(self.scene.selectedItems()))
        self.save_btn.setEnabled(bool(self.doc and n))
        self.steps.set_progress([bool(self.doc), bool(self.doc) and self.tool != "select" or n > 0, n > 0,
                                 self.saved])
        if not self.doc:
            self.guide.set_text(tr("<b>ابدأ بفتح ملف PDF</b> — اضغط «فتح ملف PDF» أو اسحب الملف وأفلته في منطقة العرض."))
        elif self.saved:
            self.guide.set_text(tr("<b>تم حفظ الملف المعدّل.</b> افتحه من الزر بالأسفل، أو استمر في التعديل واحفظ نسخة أخرى."))
        else:
            self.guide.set_text(TOOL_HELP[self.tool])

    # ================================================================ الحفظ
    def _final_edits(self):
        """نسخ التعديلات مع إضافة إزاحة التحريك إلى الإحداثيات."""
        self._store_offsets()
        out = []
        for e in self.edits:
            dx, dy = e.get("dx", 0), e.get("dy", 0)
            f = {k: v for k, v in e.items() if k not in ("item", "pil", "dx", "dy")}
            if "rect" in f and f["type"] not in ("replace", "highlight", "underline", "strike"):
                x0, y0, x1, y1 = f["rect"]
                f["rect"] = (x0 + dx, y0 + dy, x1 + dx, y1 + dy)
            for k in ("p1", "p2", "point"):
                if k in f:
                    f[k] = (f[k][0] + dx, f[k][1] + dy)
            if "paths" in f:
                f["paths"] = [[(x + dx, y + dy) for x, y in path] for path in f["paths"]]
            out.append(f)
        return out

    def _saved(self, kind, _path):
        if kind == "ok":
            self.saved = True
            self._update_panel()

    def save(self):
        if not self.doc or not self.edits:
            return
        base = os.path.splitext(os.path.basename(self.pdf_path))[0]
        out, _ = QFileDialog.getSaveFileName(self, tr("حفظ الملف المعدّل"),
                                             os.path.join(os.path.dirname(self.pdf_path), tr("{0}_معدّل.pdf", base)),
                                             PDF_FILTER)
        if not out:
            return
        if os.path.abspath(out) == os.path.abspath(self.pdf_path):
            QMessageBox.warning(self, tr("اختر اسمًا آخر"),
                                tr("لا يمكن الحفظ فوق الملف الأصلي وهو مفتوح. اختر اسمًا مختلفًا للملف المعدّل."))
            return
        src, edits = self.pdf_path, self._final_edits()
        has_redact = any(e["type"] == "redact" for e in edits)
        msg = tr("تم حفظ الملف المعدّل: {0}", os.path.basename(out))
        if has_redact:
            msg += tr(" — المناطق المحجوبة حُذفت نهائيًا من هذه النسخة.")
        self.run.run(lambda prog: (msg, core.apply_edits(src, out, edits, prog)), tr("جاري حفظ التعديلات..."))

    def apply_theme(self):
        pass
