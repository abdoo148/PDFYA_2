"""صفحة أدوات PDF + نافذة منظّم الصفحات."""
import os

try:
    import pymupdf as fitz
except ImportError:
    import fitz
from PySide6.QtCore import QSize, Qt, QTimer
from PySide6.QtGui import QColor, QIcon, QPainter, QTransform
from PySide6.QtWidgets import (
    QAbstractItemView, QCheckBox, QComboBox, QFileDialog, QFormLayout, QHBoxLayout, QLineEdit,
    QListView, QListWidget, QListWidgetItem, QMessageBox, QSlider, QStyledItemDelegate,
    QStyleOptionViewItem, QVBoxLayout, QWidget,
)

import core
from i18n import tr
from gui.dialogs import Dialog
from gui.operation import Op, OperationPage
from gui.widgets import PDF_FILTER, arrow_fwd, HelpBox, button, fitz_to_pixmap, label, sub_progress

PDF = ((".pdf",), PDF_FILTER)
RANGE_HELP = tr("أرقام الصفحات مفصولة بفاصلة، والنطاق بشرطة. مثال: 1-3, 5, 8-10")

OPS = [
    Op("organize", tr("تنظيم الصفحات"), tr("ترتيب وتدوير وحذف بالسحب"),
       tr("يعرض صفحات الملف كمصغرات: <b>اسحب</b> أي صفحة لتغيير مكانها، وحدد صفحة أو أكثر لتدويرها أو حذفها أو تكرارها، ثم احفظ النتيجة كملف جديد.<br>يعمل على ملف واحد — إن أضفت أكثر من ملف، اختر الملف المطلوب من القائمة."),
       *PDF, tr("فتح منظّم الصفحات"), outdir=False, max_files=1),
    Op("merge", tr("دمج"), tr("عدة ملفات في ملف واحد"),
       tr("يجمع ملفات PDF في ملف واحد <b>بنفس ترتيب القائمة</b>. اسحب الملفات في القائمة لتغيير ترتيبها قبل الدمج.<br><b>الناتج:</b> ستختار اسم الملف ومكانه عند الضغط على «ادمج الملفات»."),
       *PDF, tr("ادمج الملفات"), outdir=False, min_files=2),
    Op("split", tr("تقسيم"), tr("فصل الصفحات أو استخراج جزء"),
       tr("طريقتان:<br>• اترك خانة الصفحات <b>فارغة</b>: كل صفحة تُحفظ في ملف مستقل.<br>• اكتب صفحات محددة: تُستخرج في ملف واحد «الملف_مقتطف.pdf»."),
       *PDF, tr("قسّم الملف")),
    Op("compress", tr("ضغط"), tr("تقليل حجم الملف"),
       tr("يقلل حجم ملف PDF. المستوى «متوسط» مناسب لمعظم الحالات (إرسال بالبريد أو الواتساب).<br><b>الناتج:</b> «الملف_مضغوط.pdf»، وستظهر المقارنة بين الحجم قبل وبعد."),
       *PDF, tr("اضغط الملف")),
    Op("rotate", tr("تدوير"), tr("تدوير كل الصفحات أو بعضها"),
       tr("يدوّر الصفحات المحددة (أو كل الصفحات إن تركت الخانة فارغة).<br><b>الناتج:</b> «الملف_مدوّر.pdf». لتدوير صفحات مختلفة باتجاهات مختلفة استخدم «تنظيم الصفحات»."),
       *PDF, tr("دوّر الصفحات")),
    Op("delete", tr("حذف صفحات"), tr("إزالة صفحات محددة"),
       tr("يحذف الصفحات التي تكتب أرقامها، ويحفظ الباقي في «الملف_بعد_الحذف.pdf». الملف الأصلي لا يتغير."),
       *PDF, tr("احذف الصفحات")),
    Op("reorder", tr("إعادة ترتيب"), tr("بكتابة الترتيب الجديد"),
       tr("اكتب ترتيب الصفحات الجديد. مثال: «3, 1, 2» أو «10-1» لعكس ملف من 10 صفحات. يمكن تكرار صفحة بكتابتها مرتين. للترتيب بالسحب استخدم «تنظيم الصفحات»."),
       *PDF, tr("أعد الترتيب")),
    Op("protect", tr("حماية بكلمة مرور"), tr("منع فتح الملف بدونها"),
       tr("يحفظ نسخة مشفرة لا تُفتح إلا بكلمة المرور (تشفير AES-256).<br><b>مهم:</b> احفظ كلمة المرور في مكان آمن — لا يمكن استرجاع الملف بدونها."),
       *PDF, tr("احمِ الملف")),
    Op("unlock", tr("إزالة كلمة المرور"), tr("لملف تعرف كلمة مروره"),
       tr("ينشئ نسخة بدون كلمة مرور من ملف محمي، بشرط أن تعرف كلمة المرور الحالية.<br><b>الناتج:</b> «الملف_بدون_حماية.pdf»."),
       *PDF, tr("أزل الحماية")),
    Op("watermark", tr("علامة مائية"), tr("نص مائل شفاف على الصفحات"),
       tr("يكتب نصًا مائلًا شفافًا في وسط كل صفحة، مثل «سري» أو «نسخة للمراجعة».<br><b>الناتج:</b> «الملف_علامة_مائية.pdf»."),
       *PDF, tr("أضف العلامة المائية")),
]

COMPRESS = [("low", tr("خفيف — بدون أي فقد في الجودة (توفير أقل)")),
            ("medium", tr("متوسط — موصى به (يقلل دقة الصور الكبيرة)")),
            ("high", tr("قوي — أصغر حجم (قد تقل جودة الصور)"))]
ROTATE = [(90, tr("90° مع عقارب الساعة")), (270, tr("90° عكس عقارب الساعة")), (180, tr("180° (قلب الصفحة)"))]
WM_COLORS = [(tr("أحمر"), (200, 30, 30)), (tr("رمادي"), (110, 110, 110)), (tr("أزرق"), (30, 70, 180))]


def _form():
    w = QWidget()
    f = QFormLayout(w)
    f.setLabelAlignment(Qt.AlignRight)
    f.setContentsMargins(0, 0, 0, 0)
    return w, f


class ToolsPage(OperationPage):
    def __init__(self):
        super().__init__(tr("أدوات PDF"), tr("نظّم الصفحات، وادمج وقسّم واضغط واحمِ ملفاتك. كل الأدوات تحفظ ملفًا جديدًا ولا تغيّر الأصل."),
                         OPS)

    # ---- الإعدادات لكل أداة
    def build_options(self, key):
        if key == "split":
            w, f = _form()
            self.split_range = QLineEdit()
            self.split_range.setPlaceholderText(tr("اتركه فارغًا لفصل كل صفحة — أو مثلًا: 1-3, 5"))
            f.addRow(tr("الصفحات:"), self.split_range)
            f.addRow(label(RANGE_HELP, "small"))
            return w
        if key == "compress":
            w, f = _form()
            self.level = QComboBox()
            for k, t in COMPRESS:
                self.level.addItem(t, k)
            self.level.setCurrentIndex(1)
            f.addRow(tr("مستوى الضغط:"), self.level)
            return w
        if key == "rotate":
            w, f = _form()
            self.angle = QComboBox()
            for a, t in ROTATE:
                self.angle.addItem(t, a)
            f.addRow(tr("الاتجاه:"), self.angle)
            self.rot_range = QLineEdit()
            self.rot_range.setPlaceholderText(tr("فارغ = كل الصفحات — أو مثلًا: 2, 4-6"))
            f.addRow(tr("الصفحات:"), self.rot_range)
            return w
        if key == "delete":
            w, f = _form()
            self.del_range = QLineEdit()
            self.del_range.setPlaceholderText(tr("مثلًا: 2, 5-7"))
            f.addRow(tr("الصفحات المراد حذفها:"), self.del_range)
            self.del_info = label("", "small")
            f.addRow(self.del_info)
            return w
        if key == "reorder":
            w, f = _form()
            self.order = QLineEdit()
            self.order.setPlaceholderText(tr("مثلًا: 3, 1, 2"))
            f.addRow(tr("الترتيب الجديد:"), self.order)
            self.order_info = label("", "small")
            f.addRow(self.order_info)
            return w
        if key == "protect":
            w, f = _form()
            self.pw = QLineEdit()
            self.pw.setEchoMode(QLineEdit.Password)
            self.pw2 = QLineEdit()
            self.pw2.setEchoMode(QLineEdit.Password)
            f.addRow(tr("كلمة المرور:"), self.pw)
            f.addRow(tr("أعد كتابتها:"), self.pw2)
            show = QCheckBox(tr("إظهار كلمة المرور"))
            show.toggled.connect(lambda on: [e.setEchoMode(QLineEdit.Normal if on else QLineEdit.Password)
                                             for e in (self.pw, self.pw2)])
            f.addRow(show)
            return w
        if key == "unlock":
            w, f = _form()
            self.cur_pw = QLineEdit()
            self.cur_pw.setEchoMode(QLineEdit.Password)
            f.addRow(tr("كلمة المرور الحالية:"), self.cur_pw)
            return w
        if key == "watermark":
            w, f = _form()
            self.wm_text = QLineEdit(tr("سري"))
            f.addRow(tr("النص:"), self.wm_text)
            self.wm_color = QComboBox()
            for n, c in WM_COLORS:
                self.wm_color.addItem(n, c)
            f.addRow(tr("اللون:"), self.wm_color)
            row = QWidget()
            rl = QHBoxLayout(row)
            rl.setContentsMargins(0, 0, 0, 0)
            self.wm_op = QSlider(Qt.Horizontal)
            self.wm_op.setRange(10, 60)
            self.wm_op.setValue(25)
            op_lbl = label("25%", wrap=False)
            self.wm_op.valueChanged.connect(lambda v: op_lbl.setText(f"{v}%"))
            rl.addWidget(self.wm_op)
            rl.addWidget(op_lbl)
            f.addRow(tr("الوضوح:"), row)
            f.addRow(label(tr("قيمة منخفضة = علامة باهتة لا تعيق قراءة المحتوى."), "small"))
            return w
        return None

    def on_files_changed(self):
        super().on_files_changed()
        paths = self.files.paths()
        info = ""
        if paths:
            p = self.files.selected_path() or paths[0]
            try:
                with core.FITZ_LOCK:
                    n = core.page_count(p)
                info = tr("الملف «{0}» فيه {1} صفحة.", os.path.basename(p), n)
            except Exception:  # noqa: BLE001
                info = ""
        for attr in ("del_info", "order_info"):
            if hasattr(self, attr):
                getattr(self, attr).setText(info)

    # ---- التحقق قبل التنفيذ
    def validate(self, key, paths):
        if key == "delete" and not self.del_range.text().strip():
            return tr("اكتب أرقام الصفحات المراد حذفها في قسم الإعدادات (مثال: 2, 5-7).")
        if key == "reorder" and not self.order.text().strip():
            return tr("اكتب الترتيب الجديد للصفحات في قسم الإعدادات (مثال: 3, 1, 2).")
        if key == "protect":
            if len(self.pw.text()) < 4:
                return tr("اكتب كلمة مرور من 4 أحرف على الأقل.")
            if self.pw.text() != self.pw2.text():
                return tr("كلمتا المرور غير متطابقتين. أعد كتابتهما.")
        if key == "watermark" and not self.wm_text.text().strip():
            return tr("اكتب نص العلامة المائية.")
        for k, field in (("split", "split_range"), ("rotate", "rot_range"), ("delete", "del_range"), ("reorder", "order")):
            if key == k and getattr(self, field).text().strip():
                try:
                    with core.FITZ_LOCK:
                        for p in paths:
                            core.parse_ranges(getattr(self, field).text(), core.page_count(p))
                except ValueError as e:
                    return tr("أرقام الصفحات غير صحيحة: {0}. {1}", e, RANGE_HELP)
        return None

    def make_job(self, key, paths):
        out = self.outrow.for_file

        def each(suffix, fn, done_text):
            def job(prog):
                last = None
                for i, p in enumerate(paths):
                    name = os.path.splitext(os.path.basename(p))[0]
                    last = core.unique_path(os.path.join(out(p), f"{name}_{suffix}.pdf"))
                    fn(p, last, sub_progress(prog, i, len(paths)))
                    prog(i + 1, len(paths))
                return (f"{done_text}: {last}" if len(paths) == 1 else tr("{0} لـ {1} ملفات", done_text, len(paths))), last
            return job

        if key == "organize":
            PageOrganizer(self, paths[0], lambda o: (self.run.set_status(tr("✓ تم حفظ الملف المنظّم: {0}", o), "ok"),
                                                     setattr(self.run, "result_path", o),
                                                     self.run.open_btn.show(), self.run.folder_btn.show())).exec()
            return None
        if key == "merge":
            o, _ = QFileDialog.getSaveFileName(self, tr("حفظ الملف المدموج"),
                                               os.path.join(os.path.dirname(paths[0]), tr("مدموج.pdf")), PDF_FILTER)
            if not o:
                return None
            return lambda prog: (tr("تم دمج {0} ملفات في: {1}", len(paths), core.merge_pdfs(paths, o, prog)), o)
        if key == "split":
            rng = self.split_range.text()

            def job(prog):
                n, last = 0, None
                for i, p in enumerate(paths):
                    outs = core.split_pdf(p, out(p), rng, sub_progress(prog, i, len(paths)))
                    n += len(outs)
                    last = outs[-1]
                return tr("تم إنشاء {0} ملف في: {1}", n, os.path.dirname(last)), os.path.dirname(last)
            return job
        if key == "compress":
            level = self.level.currentData()

            def job(prog):
                lines, last = [], None
                for i, p in enumerate(paths):
                    name = os.path.splitext(os.path.basename(p))[0]
                    last = core.unique_path(os.path.join(out(p), tr("{0}_مضغوط.pdf", name)))
                    before = os.path.getsize(p)
                    core.compress_pdf(p, last, level)
                    after = os.path.getsize(last)
                    saved = (1 - after / before) * 100 if before else 0
                    lines.append(f"{name}: {core.size_text(p)} {arrow_fwd()} {core.size_text(last)}"
                                 + (tr(" (وفّرنا {0:.0f}%)", saved) if saved > 1 else tr(" (الملف مضغوط أصلًا)")))
                    prog(i + 1, len(paths))
                return "\n".join(lines), last
            return job
        if key == "rotate":
            angle, rng = self.angle.currentData(), self.rot_range.text()
            return each(tr("مدوّر"), lambda p, o, s: core.rotate_pages(p, o, angle, rng), tr("تم التدوير"))
        if key == "delete":
            rng = self.del_range.text()
            return each(tr("بعد_الحذف"), lambda p, o, s: core.delete_pages(p, o, rng), tr("تم الحذف"))
        if key == "reorder":
            order = self.order.text()
            return each(tr("مرتّب"), lambda p, o, s: core.reorder_pages(p, o, order), tr("تمت إعادة الترتيب"))
        if key == "protect":
            pw = self.pw.text()
            return each(tr("محمي"), lambda p, o, s: core.protect_pdf(p, o, pw), tr("تمت الحماية"))
        if key == "unlock":
            pw = self.cur_pw.text()
            return each(tr("بدون_حماية"), lambda p, o, s: core.unlock_pdf(p, o, pw), tr("تمت إزالة الحماية"))
        if key == "watermark":
            text, color, opacity = self.wm_text.text().strip(), self.wm_color.currentData(), self.wm_op.value() / 100
            return each(tr("علامة_مائية"), lambda p, o, s: core.add_watermark(p, o, text, color, opacity, progress=s),
                        tr("تمت إضافة العلامة المائية"))
        return None


# ---------------------------------------------------------------- منظّم الصفحات
class TopIconDelegate(QStyledItemDelegate):
    """أيقونة فوق النص (مثل وضع الأيقونات) مع بقاء القائمة في وضع List حتى يعيد السحب ترتيب الصفحات فعلًا."""

    def initStyleOption(self, opt, index):
        super().initStyleOption(opt, index)
        opt.decorationPosition = QStyleOptionViewItem.Top
        opt.decorationAlignment = Qt.AlignHCenter
        opt.displayAlignment = Qt.AlignHCenter | Qt.AlignTop


class PageOrganizer(Dialog):
    """مصغرات الصفحات: سحب لإعادة الترتيب، تدوير، حذف، تكرار، تراجع، ثم حفظ كملف جديد."""
    ICON = QSize(130, 170)

    def __init__(self, parent, path, on_saved):
        super().__init__(parent, tr("تنظيم الصفحات — {0}", os.path.basename(path)))
        self.path, self.on_saved = path, on_saved
        self.history = []
        self.last_state = None
        self._restoring = False
        with core.FITZ_LOCK:
            self.doc = core.open_pdf(path)
        self.base = {}  # رقم الصفحة الأصلي -> QPixmap

        self.lay.addWidget(HelpBox(tr("<b>اسحب</b> أي صفحة لمكان جديد. حدد صفحة (أو عدة صفحات بـ Ctrl / Shift) ثم استخدم الأزرار. الرقم الكبير هو الترتيب الجديد، و«أصلها» هو رقمها في الملف الأصلي.")))
        bar = QHBoxLayout()
        bar.addWidget(button(tr("تدوير يمين ↻"), lambda: self.rotate(90)))
        bar.addWidget(button(tr("تدوير يسار ↺"), lambda: self.rotate(270)))
        bar.addWidget(button(tr("تكرار"), self.duplicate, tip=tr("ينشئ نسخة من الصفحات المحددة بعدها مباشرة")))
        bar.addWidget(button(tr("حذف (Delete)"), self.delete, "danger"))
        bar.addWidget(button(tr("تحديد الكل"), lambda: self.list.selectAll()))
        bar.addWidget(button(tr("تراجع (Ctrl+Z)"), self.undo))
        bar.addStretch(1)
        self.info = label("", "muted", wrap=False)
        bar.addWidget(self.info)
        self.lay.addLayout(bar)

        self.list = QListWidget()
        self.list.setObjectName("thumbs")
        self.list.setViewMode(QListView.ListMode)
        self.list.setFlow(QListView.LeftToRight)
        self.list.setWrapping(True)
        self.list.setResizeMode(QListView.Adjust)
        self.list.setIconSize(self.ICON)
        self.list.setGridSize(QSize(160, 215))
        self.list.setItemDelegate(TopIconDelegate(self.list))
        self.list.setDragDropMode(QAbstractItemView.InternalMove)
        self.list.setDefaultDropAction(Qt.MoveAction)
        self.list.setSelectionMode(QAbstractItemView.ExtendedSelection)
        m = self.list.model()
        for sig in (m.rowsMoved, m.rowsInserted, m.rowsRemoved):
            sig.connect(lambda *a: QTimer.singleShot(0, self._relabel))
        self.list.itemSelectionChanged.connect(self._relabel_info)
        self.lay.addWidget(self.list, 1)

        row = QHBoxLayout()
        row.addWidget(button(tr("حفظ كملف جديد..."), self.save, "success", size="big"))
        row.addStretch(1)
        row.addWidget(button(tr("إغلاق بدون حفظ"), self.reject))
        self.lay.addLayout(row)
        self.resize(1050, 720)

        for i in range(len(self.doc)):
            self._add_item(self.list.count(), i, 0)
        self._relabel()
        self.next_thumb = 0
        self.timer = QTimer(self, interval=0, timeout=self._thumb_step)
        self.timer.start()

    # ---- المصغرات
    def _thumb_step(self):
        if self.next_thumb >= len(self.doc):
            self.timer.stop()
            return
        if not core.FITZ_LOCK.acquire(blocking=False):
            return
        try:
            page = self.doc[self.next_thumb]
            s = min(self.ICON.width() / page.rect.width, self.ICON.height() / page.rect.height) * self.devicePixelRatioF()
            pix = page.get_pixmap(matrix=fitz.Matrix(s, s), alpha=False)
        finally:
            core.FITZ_LOCK.release()
        pm = fitz_to_pixmap(pix)
        painter = QPainter(pm)
        painter.setPen(QColor("#AEB5C0"))
        painter.drawRect(0, 0, pm.width() - 1, pm.height() - 1)
        painter.end()
        pm.setDevicePixelRatio(self.devicePixelRatioF())
        self.base[self.next_thumb] = pm
        for r in range(self.list.count()):
            it = self.list.item(r)
            if it.data(Qt.UserRole)[0] == self.next_thumb:
                self._set_icon(it)
        self.next_thumb += 1

    def _set_icon(self, it):
        orig, rot = it.data(Qt.UserRole)
        pm = self.base.get(orig)
        if pm is not None:
            pm = pm.transformed(QTransform().rotate(rot), Qt.SmoothTransformation) if rot else pm
            icon = QIcon(pm)
            icon.addPixmap(pm, QIcon.Selected)
            it.setIcon(icon)

    def _add_item(self, row, orig, rot):
        it = QListWidgetItem()
        it.setData(Qt.UserRole, (orig, rot))
        it.setTextAlignment(Qt.AlignCenter)
        it.setFlags(it.flags() | Qt.ItemIsDragEnabled)
        self.list.insertItem(row, it)
        self._set_icon(it)
        return it

    def layout_state(self):
        return [self.list.item(r).data(Qt.UserRole) for r in range(self.list.count())]

    def _relabel(self):
        state = self.layout_state()
        if self.last_state is not None and state != self.last_state and not self._restoring:
            self.history = (self.history + [self.last_state])[-50:]
        self.last_state = state
        for r in range(self.list.count()):
            it = self.list.item(r)
            orig, rot = it.data(Qt.UserRole)
            extra = []
            if orig != r:
                extra.append(tr("أصلها {0}", orig + 1))
            if rot:
                extra.append(tr("مدوّرة {0}°", rot))
            it.setText(f"{r + 1}" + (f"\n({tr('، ').join(extra)})" if extra else ""))
        self._relabel_info()

    def _relabel_info(self):
        self.info.setText(tr("{0} صفحة — المحدد: {1}", self.list.count(), len(self.list.selectedItems())))

    # ---- العمليات (كل تغيير يُسجَّل تلقائيًا في سجل التراجع عبر _relabel)
    def _restore(self, state, select=(), undo=False):
        self._restoring = True
        self.list.clear()
        for orig, rot in state:
            self._add_item(self.list.count(), orig, rot)
        for r in select:
            self.list.item(r).setSelected(True)
        if undo:
            self.last_state = state
        self._restoring = False
        if not undo:
            self.history = (self.history + [self.last_state])[-50:]
            self.last_state = state
        self._relabel()

    def _selected_rows(self):
        return sorted(self.list.row(it) for it in self.list.selectedItems())

    def rotate(self, deg):
        rows = self._selected_rows()
        if not rows:
            return self._need_selection()
        for r in rows:
            it = self.list.item(r)
            orig, rot = it.data(Qt.UserRole)
            it.setData(Qt.UserRole, (orig, (rot + deg) % 360))
            self._set_icon(it)
        self._relabel()

    def duplicate(self):
        rows = self._selected_rows()
        if not rows:
            return self._need_selection()
        state = self.layout_state()
        copies = [state[r] for r in rows]
        at = rows[-1] + 1
        self._restore(state[:at] + copies + state[at:], range(at, at + len(copies)))

    def delete(self):
        rows = self._selected_rows()
        if not rows:
            return self._need_selection()
        if len(rows) == self.list.count():
            QMessageBox.information(self, tr("لا يمكن الحذف"), tr("لا يمكن حذف كل الصفحات — يجب أن يبقى صفحة واحدة على الأقل."))
            return
        state = self.layout_state()
        self._restore([s for r, s in enumerate(state) if r not in rows])

    def undo(self):
        if self.history:
            self._restore(self.history.pop(), undo=True)

    def _need_selection(self):
        QMessageBox.information(self, tr("حدد صفحة"), tr("اضغط على صفحة (أو أكثر مع Ctrl) أولًا، ثم اختر العملية."))

    def keyPressEvent(self, e):
        if e.key() == Qt.Key_Delete:
            self.delete()
        elif e.key() == Qt.Key_Z and e.modifiers() & Qt.ControlModifier:
            self.undo()
        else:
            super().keyPressEvent(e)

    def save(self):
        base = os.path.splitext(os.path.basename(self.path))[0]
        out, _ = QFileDialog.getSaveFileName(self, tr("حفظ الملف المنظّم"),
                                             os.path.join(os.path.dirname(self.path), tr("{0}_منظّم.pdf", base)), PDF_FILTER)
        if not out:
            return
        if os.path.abspath(out) == os.path.abspath(self.path):
            QMessageBox.warning(self, tr("اختر اسمًا آخر"), tr("لا يمكن الحفظ فوق الملف الأصلي. اختر اسمًا مختلفًا."))
            return
        try:
            with core.FITZ_LOCK:
                core.organize_pages(self.path, out, self.layout_state())
        except Exception as e:  # noqa: BLE001
            QMessageBox.warning(self, tr("تعذر الحفظ"), str(e))
            return
        self.on_saved(out)
        self.accept()

    def done(self, r):
        self.timer.stop()
        with core.FITZ_LOCK:
            self.doc.close()
        super().done(r)
