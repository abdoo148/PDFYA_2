"""صفحة توقيع PDF: عرض الصفحة، وضع العناصر وتحريكها وتغيير حجمها، المصغرات، الحفظ والتوقيع الجماعي."""
import os

try:
    import pymupdf as fitz
except ImportError:
    import fitz
from PySide6.QtCore import QPointF, QRectF, QSize, Qt, QTimer
from PySide6.QtGui import QBrush, QColor, QPen, QTransform
from PySide6.QtWidgets import (
    QAbstractItemView, QComboBox, QFileDialog, QFrame, QGraphicsItem, QGraphicsPixmapItem,
    QGraphicsRectItem, QGraphicsScene, QGraphicsView, QGridLayout, QHBoxLayout, QLabel, QListView,
    QListWidget, QListWidgetItem, QMessageBox, QScrollArea, QSlider, QSpinBox, QStackedWidget,
    QStyle, QStyleOptionGraphicsItem, QVBoxLayout, QWidget,
)

import core
from i18n import tr
from gui import theme
from gui.dialogs import DrawDialog, LibraryDialog, TextDialog, ask_kind, load_signature_image
from gui.widgets import (
    IMG_EXTS, IMG_FILTER, PDF_FILTER, HelpBox, PageHeader, RunBar, StepBar, button, card, ext_of,
    fitz_to_pixmap, label, pil_to_pixmap,
)

SCOPES = [("page", tr("هذه الصفحة فقط")), ("all", tr("كل الصفحات")), ("first", tr("الصفحة الأولى")), ("last", tr("الصفحة الأخيرة"))]
KIND_NAMES = dict(core.LIBRARY_KINDS, text=tr("نص"), date=tr("تاريخ"))
DEFAULT_WIDTH = {"signature": 160, "initials": 70, "stamp": 120}
TEXT_PT = 14  # حجم النص الافتراضي بالنقاط (الصورة تُرسم بـ 64px)
PT_TO_MM = 25.4 / 72


class SigItem(QGraphicsPixmapItem):
    """عنصر على الصفحة (توقيع/ختم/نص). الإحداثيات بنقاط PDF."""
    HANDLE_PX = 12

    def __init__(self, page, model):
        self._sync = True  # قبل أي استدعاء لـ itemChange
        self._resizing = False
        super().__init__(pil_to_pixmap(model["img"]))
        self.page, self.model = page, model
        self.setFlags(QGraphicsItem.ItemIsMovable | QGraphicsItem.ItemIsSelectable
                      | QGraphicsItem.ItemSendsGeometryChanges)
        self.setTransformationMode(Qt.SmoothTransformation)
        self.setShapeMode(QGraphicsPixmapItem.BoundingRectShape)
        self.setAcceptHoverEvents(True)
        self.setCursor(Qt.SizeAllCursor)
        self.setZValue(10)
        self.apply()

    def size(self):
        w = self.model["width"]
        return w, w * self.model["img"].height / self.model["img"].width

    def apply(self):
        self._sync = True
        self.prepareGeometryChange()
        w, h = self.size()
        self.setScale(w / self.pixmap().width())
        self.setPos(self.model["rel"][0] * self.page.page_w - w / 2, self.model["rel"][1] * self.page.page_h - h / 2)
        self.setOpacity(self.model["opacity"])
        self._sync = False

    def _margin(self):
        """هامش (بإحداثيات العنصر) يتسع لمربع تغيير الحجم."""
        view_scale = self.page.zoom or 1
        return self.HANDLE_PX / (view_scale * self.scale())

    def boundingRect(self):
        m = self._margin()
        return QRectF(self.pixmap().rect()).adjusted(-m, -m, m, m)

    def shape(self):
        from PySide6.QtGui import QPainterPath
        path = QPainterPath()
        path.addRect(self.boundingRect())  # يشمل مربع تغيير الحجم الخارج عن حدود الصورة
        return path

    def _handle_scene(self):
        w, h = self.size()
        hs = self.HANDLE_PX / (self.page.zoom or 1)
        return QRectF(self.pos().x() + w - hs, self.pos().y() + h - hs, hs * 2, hs * 2)

    def itemChange(self, change, value):
        if not self._sync:
            if change == QGraphicsItem.ItemPositionChange:
                w, h = self.size()
                x = min(max(value.x(), -w / 2), self.page.page_w - w / 2)
                y = min(max(value.y(), -h / 2), self.page.page_h - h / 2)
                return QPointF(x, y)
            if change == QGraphicsItem.ItemPositionHasChanged:
                w, h = self.size()
                self.model["rel"] = ((self.pos().x() + w / 2) / self.page.page_w,
                                     (self.pos().y() + h / 2) / self.page.page_h)
                self.page.item_changed(placed=True)
        return super().itemChange(change, value)

    def hoverMoveEvent(self, e):
        on_handle = self.isSelected() and self._handle_scene().contains(e.scenePos())
        self.setCursor(Qt.SizeFDiagCursor if on_handle else Qt.SizeAllCursor)
        super().hoverMoveEvent(e)

    def mousePressEvent(self, e):
        if self.isSelected() and self._handle_scene().contains(e.scenePos()):
            self._resizing = True
            e.accept()
            return
        super().mousePressEvent(e)

    def mouseMoveEvent(self, e):
        if self._resizing:
            left, top = self.pos().x(), self.pos().y()
            ratio = self.model["img"].height / self.model["img"].width
            w = max(12.0, min(self.page.page_w, e.scenePos().x() - left))
            self.model["width"] = w
            self.model["rel"] = ((left + w / 2) / self.page.page_w, (top + w * ratio / 2) / self.page.page_h)
            self.apply()
            self.page.item_changed(placed=True, resized=True)
            return
        super().mouseMoveEvent(e)

    def mouseReleaseEvent(self, e):
        self._resizing = False
        super().mouseReleaseEvent(e)

    def paint(self, p, option, widget=None):
        opt = QStyleOptionGraphicsItem(option)
        opt.state &= ~QStyle.State_Selected
        super().paint(p, opt, widget)
        r = QRectF(self.pixmap().rect())
        c = QColor(theme.colors()["accent"])
        if self.isSelected():
            pen = QPen(c, 1.6, Qt.DashLine)
            pen.setCosmetic(True)
            p.setPen(pen)
            p.setBrush(Qt.NoBrush)
            p.drawRect(r)
            hs = self.HANDLE_PX / ((self.page.zoom or 1) * self.scale())
            p.setPen(QPen(QColor("white"), 0))
            p.setBrush(QBrush(c))
            p.drawRect(QRectF(r.right() - hs / 2, r.bottom() - hs / 2, hs, hs))
        else:
            pen = QPen(QColor("#9AA3B0"), 1, Qt.DotLine)
            pen.setCosmetic(True)
            p.setPen(pen)
            p.setBrush(Qt.NoBrush)
            p.drawRect(r)


class PageView(QGraphicsView):
    def __init__(self, page):
        super().__init__()
        self.page = page
        self.setRenderHints(self.renderHints())
        self.setDragMode(QGraphicsView.NoDrag)
        self.setTransformationAnchor(QGraphicsView.AnchorUnderMouse)
        self.setAcceptDrops(True)
        self.setLayoutDirection(Qt.LeftToRight)

    def wheelEvent(self, e):
        if e.modifiers() & Qt.ControlModifier:
            self.page.set_zoom(self.page.zoom * (1.15 if e.angleDelta().y() > 0 else 1 / 1.15))
        else:
            super().wheelEvent(e)

    def keyPressEvent(self, e):
        k = e.key()
        step = 10 if e.modifiers() & Qt.ShiftModifier else 1
        moves = {Qt.Key_Left: (-step, 0), Qt.Key_Right: (step, 0), Qt.Key_Up: (0, -step), Qt.Key_Down: (0, step)}
        if k == Qt.Key_Delete:
            self.page.delete_selected()
        elif k in moves and self.page.selected_item():
            it = self.page.selected_item()
            dx, dy = moves[k]
            it.setPos(it.pos() + QPointF(dx, dy))
        elif k == Qt.Key_PageDown:
            self.page.go(1)
        elif k == Qt.Key_PageUp:
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
        self.page.on_drop([u.toLocalFile() for u in e.mimeData().urls() if u.isLocalFile()])


class SignPage(QWidget):
    def __init__(self):
        super().__init__()
        self.doc = None
        self.pdf_path = None
        self.page_no = 0
        self.zoom = 1.0
        self.page_w = self.page_h = 1.0
        self.items = []          # نماذج العناصر (dict)
        self.gitems = []         # عناصر الرسم الظاهرة في الصفحة الحالية
        self.placed = False
        self.saved = False
        self.setAcceptDrops(True)

        root = QVBoxLayout(self)
        root.setContentsMargins(24, 20, 24, 16)
        root.setSpacing(12)
        root.addWidget(PageHeader(tr("توقيع PDF"), tr("ضع توقيعك أو ختمك أو أي نص على ملف PDF، ثم احفظه كملف جديد. الملف الأصلي لا يتغير.")))
        self.steps = StepBar([tr("افتح ملف PDF"), tr("أضف توقيعًا أو عنصرًا"), tr("اسحبه إلى مكانه"), tr("احفظ الملف")])
        root.addWidget(self.steps)
        self.guide = HelpBox()
        root.addWidget(self.guide)

        body = QHBoxLayout()
        body.setSpacing(12)
        root.addLayout(body, 1)

        # ------------------------------------------------ اللوحة الجانبية (يمين)
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFixedWidth(320)
        panel = QWidget()
        pl = QVBoxLayout(panel)
        pl.setContentsMargins(0, 0, 6, 0)
        pl.setSpacing(12)
        scroll.setWidget(panel)
        body.addWidget(scroll)

        c, l = card(tr("الملف"))
        l.addWidget(button(tr("فتح ملف PDF..."), self.open_pdf, "primary", tr("اختر ملف PDF من جهازك (أو اسحبه إلى منطقة العرض)")))
        self.file_lbl = label(tr("لم يتم فتح ملف بعد"), "muted")
        l.addWidget(self.file_lbl)
        pl.addWidget(c)

        c, l = card(tr("أضف عنصرًا"), tr("يظهر العنصر في منتصف الجزء الظاهر من الصفحة، ثم اسحبه لمكانه."))
        g = QGridLayout()
        g.setSpacing(6)
        adds = [
            (tr("رسم توقيع"), self.draw_sig, tr("ارسم توقيعك بالماوس أو قلم اللمس")),
            (tr("صورة توقيع / ختم"), self.load_sig, tr("استخدم صورة توقيع أو ختم من جهازك. تُحذف الخلفية البيضاء تلقائيًا")),
            (tr("من المكتبة"), self.open_library, tr("اختر توقيعًا أو ختمًا حفظته من قبل")),
            (tr("نص"), self.add_text, tr("أضف نصًا مثل الاسم أو الصفة أو «تمت الموافقة»")),
            (tr("تاريخ اليوم"), self.add_date, tr("يضيف تاريخ اليوم ({0})", core.today_text())),
        ]
        for i, (t, fn, tip) in enumerate(adds):
            g.addWidget(button(t, fn, tip=tip), i // 2, i % 2)
        l.addLayout(g)
        pl.addWidget(c)

        c, l = card(tr("العنصر المحدد"))
        self.sel_lbl = label("", "muted")
        l.addWidget(self.sel_lbl)
        self.sel_box = QWidget()
        sl = QVBoxLayout(self.sel_box)
        sl.setContentsMargins(0, 0, 0, 0)
        self.size_lbl = label(tr("العرض:"), wrap=False)
        sl.addWidget(self.size_lbl)
        self.size = QSlider(Qt.Horizontal)
        self.size.setRange(12, 500)
        self.size.setToolTip(tr("عرض العنصر على الصفحة. يمكنك أيضًا سحب المربع الأزرق في زاويته"))
        self.size.valueChanged.connect(self.on_size)
        sl.addWidget(self.size)
        self.op_lbl = label(tr("الشفافية:"), wrap=False)
        sl.addWidget(self.op_lbl)
        self.opacity = QSlider(Qt.Horizontal)
        self.opacity.setRange(15, 100)
        self.opacity.setToolTip(tr("قلّلها لجعل الختم أو العنصر شفافًا قليلًا"))
        self.opacity.valueChanged.connect(self.on_opacity)
        sl.addWidget(self.opacity)
        sl.addWidget(label(tr("يظهر في:"), wrap=False))
        self.scope = QComboBox()
        for k, t in SCOPES:
            self.scope.addItem(t, k)
        self.scope.setToolTip(tr("مثلًا: «كل الصفحات» لوضع الأحرف الأولى أسفل كل صفحة بنفس المكان"))
        self.scope.currentIndexChanged.connect(self.on_scope)
        sl.addWidget(self.scope)
        row = QHBoxLayout()
        row.addWidget(button(tr("نسخ لهذه الصفحة"), self.duplicate, tip=tr("ينشئ نسخة من العنصر في الصفحة المعروضة الآن")))
        row.addWidget(button(tr("حفظ في المكتبة"), self.save_to_library, tip=tr("لاستخدامه لاحقًا في ملفات أخرى")))
        sl.addLayout(row)
        sl.addWidget(button(tr("حذف العنصر (Delete)"), self.delete_selected, "danger"))
        l.addWidget(self.sel_box)
        pl.addWidget(c)

        c, l = card(tr("الحفظ"))
        self.save_btn = button(tr("حفظ الملف الموقّع..."), self.save, "success", size="big",
                               tip=tr("يحفظ نسخة جديدة موقّعة، ولا يغيّر الملف الأصلي"))
        l.addWidget(self.save_btn)
        self.batch_btn = button(tr("توقيع عدة ملفات بنفس العناصر..."), self.batch,
                                tip=tr("يضع نفس العناصر بنفس الأماكن على ملفات PDF أخرى دفعة واحدة"))
        l.addWidget(self.batch_btn)
        self.run = RunBar()
        self.run.lock_widgets = [self.save_btn, self.batch_btn]
        self.run.on_done = self._saved
        l.addWidget(self.run)
        pl.addWidget(c)
        pl.addStretch(1)

        # ------------------------------------------------ العرض (وسط)
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
        empty = QFrame()
        empty.setObjectName("emptyState")
        el = QVBoxLayout(empty)
        el.addStretch(1)
        t = label(tr("لم يتم فتح ملف بعد"), "h2")
        t.setAlignment(Qt.AlignCenter)
        el.addWidget(t)
        t = label(tr("اسحب ملف PDF من المستكشف وأفلته هنا، أو اضغط الزر بالأسفل"), "muted")
        t.setAlignment(Qt.AlignCenter)
        el.addWidget(t)
        b = button(tr("فتح ملف PDF..."), self.open_pdf, "primary", size="big")
        bl = QHBoxLayout()
        bl.addStretch(1)
        bl.addWidget(b)
        bl.addStretch(1)
        el.addLayout(bl)
        el.addStretch(1)
        self.stack.addWidget(empty)

        self.scene = QGraphicsScene()
        self.scene.selectionChanged.connect(self.update_panel)
        self.view = PageView(self)
        self.view.setScene(self.scene)
        self.stack.addWidget(self.view)
        vl.addWidget(self.stack, 1)
        body.addWidget(viewer, 1)

        # ------------------------------------------------ المصغرات (يسار)
        self.thumbs = QListWidget()
        self.thumbs.setObjectName("thumbs")
        self.thumbs.setViewMode(QListView.IconMode)
        self.thumbs.setFlow(QListView.TopToBottom)
        self.thumbs.setWrapping(False)
        self.thumbs.setMovement(QListView.Static)
        self.thumbs.setIconSize(QSize(96, 130))
        self.thumbs.setFixedWidth(135)
        self.thumbs.setSpacing(4)
        self.thumbs.setSelectionMode(QAbstractItemView.SingleSelection)
        self.thumbs.currentRowChanged.connect(lambda r: r >= 0 and self.goto(r))
        body.addWidget(self.thumbs)
        self.thumbs.hide()

        self.render_timer = QTimer(self, singleShot=True, interval=120, timeout=self.render_page)
        self.thumb_timer = QTimer(self, interval=0, timeout=self._thumb_step)
        self.thumb_next = 0
        self.page_item = None
        self.update_panel()

    # ================================================================ الملف
    def dragEnterEvent(self, e):
        if e.mimeData().hasUrls():
            e.acceptProposedAction()

    def dropEvent(self, e):
        self.on_drop([u.toLocalFile() for u in e.mimeData().urls() if u.isLocalFile()])

    def on_drop(self, paths):
        for p in paths:
            if ext_of(p) == ".pdf":
                self.load_pdf(p)
            elif ext_of(p) in IMG_EXTS:
                img = load_signature_image(self, p)
                if img is not None:
                    self.add_item(img, "signature")

    def open_pdf(self):
        p, _ = QFileDialog.getOpenFileName(self, tr("اختر ملف PDF"), "", PDF_FILTER)
        if p:
            self.load_pdf(p)

    def load_pdf(self, p):
        if not core.FITZ_LOCK.acquire(timeout=1):
            QMessageBox.information(self, tr("انتظر"), tr("هناك عملية قيد التنفيذ. انتظر حتى تنتهي ثم افتح الملف."))
            return
        try:
            d = fitz.open(p)
            if d.needs_pass:
                d.close()
                QMessageBox.warning(self, tr("الملف محمي بكلمة مرور"),
                                    tr("لا يمكن توقيع ملف محمي بكلمة مرور.\n\nأزل الحماية أولًا من: أدوات PDF ← إزالة كلمة المرور، ثم افتح الملف الناتج."))
                return
            if len(d) == 0:
                d.close()
                QMessageBox.warning(self, tr("ملف فارغ"), tr("هذا الملف لا يحتوي على أي صفحات."))
                return
        except Exception as e:  # noqa: BLE001
            QMessageBox.warning(self, tr("تعذر فتح الملف"),
                                tr("لم نتمكن من فتح:\n{0}\n\nقد يكون الملف تالفًا أو ليس PDF.\n\nالتفاصيل: {1}", os.path.basename(p), e))
            return
        finally:
            core.FITZ_LOCK.release()
        if self.doc:
            self.doc.close()
        self.doc, self.pdf_path, self.page_no = d, p, 0
        self.saved = False
        for it in self.items:  # العناصر السابقة تبقى لإعادة استخدامها
            it["page"] = min(it["page"], len(d) - 1)
        self.file_lbl.setText(tr("{0}\n{1} صفحة", os.path.basename(p), len(d)))
        self.file_lbl.setToolTip(p)
        self.page_spin.blockSignals(True)
        self.page_spin.setMaximum(len(d))
        self.page_spin.setValue(1)
        self.page_spin.blockSignals(False)
        self.total_lbl.setText(tr("من {0}", len(d)))
        self.stack.setCurrentIndex(1)
        self.thumbs.setVisible(len(d) > 1)
        QTimer.singleShot(0, self._after_open)

    def _after_open(self):
        self.fit_width(render=False)
        self.render_page()
        self.start_thumbs()
        self.update_panel()

    def go(self, d):
        self.goto(self.page_no + d)

    def goto(self, i):
        if not self.doc or not (0 <= i < len(self.doc)) or i == self.page_no and self.page_item:
            return
        self.page_no = i
        self.render_page()
        self.view.verticalScrollBar().setValue(0)

    def fit_width(self, render=True):
        if not self.doc:
            return
        avail = max(200, self.view.viewport().width() - 40)
        self.set_zoom(avail / self.doc[self.page_no].rect.width, render)

    def set_zoom(self, z, render=True):
        if not self.doc:
            return
        self.zoom = max(0.25, min(5.0, z))
        self.view.setTransform(QTransform.fromScale(self.zoom, self.zoom))
        self.zoom_lbl.setText(f"{self.zoom * 100:.0f}%")
        if render:
            self.render_timer.start()  # إعادة الرسم بدقة أعلى بعد توقف التكبير

    def render_page(self):
        if not self.doc:
            return
        if not core.FITZ_LOCK.acquire(blocking=False):
            self.render_timer.start(250)
            return
        try:
            page = self.doc[self.page_no]
            self.page_w, self.page_h = page.rect.width, page.rect.height
            dpr = self.devicePixelRatioF()
            s = min(4.0, self.zoom * dpr)
            pix = page.get_pixmap(matrix=fitz.Matrix(s, s), alpha=False)
        finally:
            core.FITZ_LOCK.release()
        pm = fitz_to_pixmap(pix)
        keep = self.selected_item().model if self.selected_item() else None
        for g in self.gitems:
            self.scene.removeItem(g)
        self.gitems = []
        self.scene.clear()
        shadow = QGraphicsRectItem(3, 3, self.page_w, self.page_h)
        shadow.setBrush(QColor(0, 0, 0, 50))
        shadow.setPen(Qt.NoPen)
        self.scene.addItem(shadow)
        self.page_item = QGraphicsPixmapItem(pm)
        self.page_item.setTransformationMode(Qt.SmoothTransformation)
        self.page_item.setScale(1 / s)
        self.scene.addItem(self.page_item)
        self.scene.setSceneRect(QRectF(-20, -20, self.page_w + 40, self.page_h + 40))
        self.page_spin.blockSignals(True)
        self.page_spin.setValue(self.page_no + 1)
        self.page_spin.blockSignals(False)
        self.prev_btn.setEnabled(self.page_no > 0)
        self.next_btn.setEnabled(self.page_no < len(self.doc) - 1)
        self.thumbs.blockSignals(True)
        self.thumbs.setCurrentRow(self.page_no)
        self.thumbs.blockSignals(False)
        self.rebuild_items(select=keep)

    # ================================================================ المصغرات
    def start_thumbs(self):
        self.thumbs.clear()
        if not self.doc or len(self.doc) < 2:
            return
        for i in range(len(self.doc)):
            it = QListWidgetItem(str(i + 1))
            it.setTextAlignment(Qt.AlignCenter)
            it.setSizeHint(QSize(110, 160))
            self.thumbs.addItem(it)
        self.thumbs.setCurrentRow(self.page_no)
        self.thumb_next = 0
        self.thumb_timer.start()

    def _thumb_step(self):
        if not self.doc or self.thumb_next >= len(self.doc):
            self.thumb_timer.stop()
            return
        if not core.FITZ_LOCK.acquire(blocking=False):
            return  # يُعاد المحاولة في الدورة التالية
        try:
            page = self.doc[self.thumb_next]
            s = min(96 / page.rect.width, 130 / page.rect.height)
            pix = page.get_pixmap(matrix=fitz.Matrix(s, s), alpha=False)
        finally:
            core.FITZ_LOCK.release()
        item = self.thumbs.item(self.thumb_next)
        if item:
            from PySide6.QtGui import QIcon
            pm = fitz_to_pixmap(pix)
            icon = QIcon(pm)
            icon.addPixmap(pm, QIcon.Selected)  # بدون تلوين أزرق للمصغّر المحدد
            item.setIcon(icon)
        self.thumb_next += 1

    # ================================================================ العناصر
    def visible(self, m):
        return bool(self.doc) and self.page_no in core.target_pages(m["scope"], m["page"], len(self.doc))

    def rebuild_items(self, select=None):
        sel_model = select or (self.selected_item().model if self.selected_item() else None)
        for g in self.gitems:
            self.scene.removeItem(g)
        self.gitems = []
        if not self.doc:
            return
        for m in self.items:
            if self.visible(m):
                g = SigItem(self, m)
                self.scene.addItem(g)
                self.gitems.append(g)
                if m is sel_model:
                    g.setSelected(True)
        self.update_panel()

    def selected_item(self):
        for g in self.gitems:
            try:
                if g.isSelected():
                    return g
            except RuntimeError:
                pass
        return None

    def view_center_rel(self):
        if not self.doc:
            return (0.5, 0.8)
        c = self.view.mapToScene(self.view.viewport().rect().center())
        return (max(0.1, min(0.9, c.x() / self.page_w)), max(0.1, min(0.9, c.y() / self.page_h)))

    def add_item(self, img, kind):
        width = img.width * TEXT_PT / 64 if kind in ("text", "date") else DEFAULT_WIDTH.get(kind, 150)
        if self.doc:
            width = min(width, self.page_w * 0.9)
        rx, ry = self.view_center_rel()
        ry = min(0.95, ry + 0.04 * (len(self.items) % 4))
        m = dict(img=img, kind=kind, width=width, rel=(rx, ry), scope="page", page=self.page_no, opacity=1.0)
        self.items.append(m)
        self.saved = False
        self.scene.clearSelection()
        self.rebuild_items(select=m)
        self.view.setFocus()

    def draw_sig(self):
        DrawDialog(self, self.add_item).exec()

    def load_sig(self):
        p, _ = QFileDialog.getOpenFileName(self, tr("اختر صورة التوقيع أو الختم"), "", IMG_FILTER)
        if p:
            img = load_signature_image(self, p)
            if img is not None:
                self.add_item(img, "signature")

    def open_library(self):
        LibraryDialog(self, self.add_item).exec()

    def add_text(self):
        TextDialog(self, self.add_item).exec()

    def add_date(self):
        with core.FITZ_LOCK:
            img = core.render_text_image(core.today_text(), (20, 40, 120))
        self.add_item(img, "date")

    def item_changed(self, placed=False, resized=False):
        if placed:
            self.placed = True
            self.saved = False
        g = self.selected_item()
        if resized and g:
            self.size.blockSignals(True)
            self.size.setValue(int(g.model["width"]))
            self.size.blockSignals(False)
            self._size_text(g.model["width"])
        self._update_guide()

    def _size_text(self, w):
        self.size_lbl.setText(tr("العرض: {0:.0f} مم", w * PT_TO_MM))

    def update_panel(self):
        g = self.selected_item()
        self.sel_box.setEnabled(g is not None)
        if g is None:
            self.sel_lbl.setText(tr("اضغط على أي عنصر في الصفحة لتعديله.") if self.items else tr("لم تُضف أي عنصر بعد."))
        else:
            m = g.model
            n = self.items.index(m) + 1
            self.sel_lbl.setText(tr("{0} — العنصر {1} من {2}", KIND_NAMES.get(m['kind'], tr("عنصر")), n, len(self.items)))
            for w in (self.size, self.opacity, self.scope):
                w.blockSignals(True)
            self.size.setValue(int(m["width"]))
            self.opacity.setValue(int(m["opacity"] * 100))
            self.scope.setCurrentIndex([k for k, _ in SCOPES].index(m["scope"]))
            for w in (self.size, self.opacity, self.scope):
                w.blockSignals(False)
            self._size_text(m["width"])
            self.op_lbl.setText(tr("الشفافية: {0}%", int(m['opacity'] * 100)))
        self._update_guide()

    def _update_guide(self):
        has_doc, has_items = bool(self.doc), bool(self.items)
        self.steps.set_progress([has_doc, has_items, has_items and self.placed, self.saved])
        if not has_doc:
            txt = (tr("<b>ابدأ بفتح ملف PDF</b> — اضغط «فتح ملف PDF» أو اسحب الملف وأفلته في منطقة العرض. ")
                   + (tr("العناصر التي أضفتها جاهزة وستظهر على الملف.") if has_items else ""))
        elif not has_items:
            txt = (tr("<b>أضف توقيعك</b> — من بطاقة «أضف عنصرًا»: ارسم توقيعك، أو استخدم صورة له، أو اختره من المكتبة. يمكنك أيضًا إضافة نص أو تاريخ."))
        elif self.saved:
            txt = tr("<b>تم حفظ الملف الموقّع.</b> يمكنك فتحه من الزر بالأسفل، أو فتح ملف آخر وستبقى العناصر جاهزة عليه.")
        elif self.selected_item():
            txt = (tr("<b>ضع العنصر في مكانه</b> — اسحبه بالماوس. لتغيير الحجم اسحب المربع الأزرق في زاويته أو استخدم شريط «العرض». الأسهم تحرّكه بدقة (Shift للتحريك الأسرع)، وDelete يحذفه."))
        else:
            txt = (tr("<b>عندما ينتهي ترتيب العناصر</b> اضغط «حفظ الملف الموقّع». لتعديل عنصر اضغط عليه. لاستخدام الصفحات استعمل المصغرات أو PageUp/PageDown."))
        self.guide.set_text(txt)

    def on_size(self, v):
        g = self.selected_item()
        if g:
            g.model["width"] = float(v)
            g.apply()
            self._size_text(v)
            self.saved = False

    def on_opacity(self, v):
        g = self.selected_item()
        if g:
            g.model["opacity"] = v / 100
            g.setOpacity(v / 100)
            self.op_lbl.setText(tr("الشفافية: {0}%", v))
            self.saved = False

    def on_scope(self, idx):
        g = self.selected_item()
        if not g:
            return
        g.model["scope"] = SCOPES[idx][0]
        if g.model["scope"] == "page":
            g.model["page"] = self.page_no
        self.saved = False
        self.rebuild_items(select=g.model)

    def duplicate(self):
        g = self.selected_item()
        if g:
            m = dict(g.model, scope="page", page=self.page_no)
            self.items.append(m)
            self.scene.clearSelection()
            self.rebuild_items(select=m)

    def delete_selected(self):
        g = self.selected_item()
        if g:
            self.items.remove(g.model)
            self.saved = False
            self.rebuild_items()

    def save_to_library(self):
        g = self.selected_item()
        if not g:
            return
        kind = g.model["kind"]
        if kind not in ("initials", "stamp"):
            kind = ask_kind(self)
        if kind:
            core.library_save(g.model["img"], kind)
            self.run.set_status(tr("تم الحفظ في المكتبة كـ «{0}».", core.LIBRARY_KINDS[kind]), "ok")

    # ================================================================ الحفظ
    def _job_items(self):
        return [dict(m) for m in self.items]

    def _saved(self, kind, _path):
        if kind == "ok":
            self.saved = True
            self._update_guide()

    def save(self):
        if not self.doc:
            QMessageBox.information(self, tr("لا يوجد ملف"), tr("افتح ملف PDF أولًا من زر «فتح ملف PDF»."))
            return
        if not self.items:
            QMessageBox.information(self, tr("لا يوجد توقيع"), tr("أضف توقيعًا أو عنصرًا أولًا من بطاقة «أضف عنصرًا»."))
            return
        base = os.path.splitext(os.path.basename(self.pdf_path))[0]
        out, _ = QFileDialog.getSaveFileName(self, tr("حفظ الملف الموقّع"),
                                             os.path.join(os.path.dirname(self.pdf_path), tr("{0}_موقّع.pdf", base)),
                                             PDF_FILTER)
        if not out:
            return
        if os.path.abspath(out) == os.path.abspath(self.pdf_path):
            QMessageBox.warning(self, tr("اختر اسمًا آخر"),
                                tr("لا يمكن الحفظ فوق الملف الأصلي وهو مفتوح. اختر اسمًا مختلفًا للملف الموقّع."))
            return
        src, items = self.pdf_path, self._job_items()
        self.run.run(lambda prog: (tr("تم حفظ الملف الموقّع: {0}", os.path.basename(out)),
                                   core.stamp_items(src, out, items, prog)), tr("جاري حفظ الملف الموقّع..."))

    def batch(self):
        if not self.items:
            QMessageBox.information(self, tr("لا توجد عناصر"),
                                    tr("أولًا افتح ملفًا نموذجيًا وضع عليه العناصر (التوقيع وغيره) في أماكنها، ثم استخدم هذا الزر لتطبيقها على ملفات أخرى."))
            return
        paths, _ = QFileDialog.getOpenFileNames(self, tr("اختر الملفات المراد توقيعها"), "", PDF_FILTER)
        if not paths:
            return
        od = QFileDialog.getExistingDirectory(self, tr("اختر مجلد حفظ الملفات الموقّعة"))
        if not od:
            return
        items = self._job_items()
        note = ""
        if any(m["scope"] == "page" for m in items):
            note = tr(" (العناصر المحددة لصفحة معينة تُطبَّق على نفس رقم الصفحة في كل ملف إن وُجد)")

        def job(prog):
            outs = core.batch_stamp(list(paths), od, items, prog)
            return tr("تم توقيع {0} ملف وحفظها في: {1}{2}", len(outs), od, note), od

        self.run.run(job, tr("جاري توقيع {0} ملف...", len(paths)))

    def apply_theme(self):
        for g in self.gitems:
            g.update()
