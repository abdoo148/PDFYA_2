"""قالب مشترك لصفحتي التحويل والأدوات: اختر العملية ← أضف الملفات ← الإعدادات ← تنفيذ."""
from PySide6.QtCore import Qt
from PySide6.QtWidgets import QScrollArea, QStackedWidget, QVBoxLayout, QWidget

from i18n import tr
from gui.widgets import FileList, HelpBox, OutDirRow, PageHeader, RunBar, TileGroup, button, card, label


class Op:
    def __init__(self, key, title, short, help, exts, filter_text, run_text, hint="", outdir=True, min_files=1,
                 max_files=None):
        self.key, self.title, self.short, self.help = key, title, short, help
        self.exts, self.filter_text, self.run_text, self.hint = exts, filter_text, run_text, hint
        self.outdir, self.min_files, self.max_files = outdir, min_files, max_files


class OperationPage(QWidget):
    COLUMNS = 4

    def __init__(self, title, subtitle, ops):
        super().__init__()
        self.ops = {o.key: o for o in ops}
        self.op = None
        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        outer.addWidget(scroll)
        content = QWidget()
        scroll.setWidget(content)
        lay = QVBoxLayout(content)
        lay.setContentsMargins(24, 20, 24, 20)
        lay.setSpacing(14)
        lay.addWidget(PageHeader(title, subtitle))

        c, l = card(tr("١ — اختر العملية"))
        self.tiles = TileGroup([(o.key, o.title, o.short) for o in ops], self.COLUMNS)
        self.tiles.changed.connect(self.on_op)
        l.addWidget(self.tiles)
        self.help = HelpBox()
        l.addWidget(self.help)
        lay.addWidget(c)

        c, l = card(tr("٢ — أضف الملفات"))
        first = ops[0]
        self.files = FileList(first.exts, first.filter_text, first.hint)
        self.files.changed.connect(self.on_files_changed)
        l.addWidget(self.files)
        lay.addWidget(c)

        self.opt_card, l = card(tr("٣ — الإعدادات"))
        self.opt_stack = QStackedWidget()
        self.opt_pages = {}
        for o in ops:
            w = self.build_options(o.key)
            if w is not None:
                self.opt_pages[o.key] = w
                if self.opt_stack.indexOf(w) < 0:  # قد تشترك عدة عمليات في نفس الإعدادات
                    self.opt_stack.addWidget(w)
        l.addWidget(self.opt_stack)
        lay.addWidget(self.opt_card)

        c, l = card()
        self.outrow = OutDirRow()
        l.addWidget(self.outrow)
        self.error = label("", "errorText")
        self.error.hide()
        l.addWidget(self.error)
        self.go = button("", self.start, "primary", size="big")
        l.addWidget(self.go)
        self.run = RunBar()
        self.run.lock_widgets = [self.go]
        l.addWidget(self.run)
        lay.addWidget(c)
        lay.addStretch(1)
        self.tiles.select(ops[0].key)

    # ---- يُعاد تعريفها في الصفحات
    def build_options(self, key):
        return None

    def validate(self, key, paths):
        return None

    def make_job(self, key, paths):
        raise NotImplementedError

    def on_files_changed(self):
        self.error.hide()

    # ---- منطق مشترك
    def on_op(self, key):
        o = self.op = self.ops[key]
        self.help.set_text(o.help)
        self.files.set_types(o.exts, o.filter_text, o.hint)
        has_opts = key in self.opt_pages
        self.opt_card.setVisible(has_opts)
        if has_opts:
            self.opt_stack.setCurrentWidget(self.opt_pages[key])
        self.outrow.setVisible(o.outdir)
        self.go.setText(o.run_text)
        self.error.hide()

    def show_error(self, text):
        self.error.setText("✗ " + text)
        self.error.show()

    def start(self):
        o = self.op
        paths = self.files.paths()
        if len(paths) < o.min_files:
            self.show_error(tr("أضف ملفًا واحدًا على الأقل في الخطوة ٢.") if o.min_files == 1
                            else tr("هذه العملية تحتاج {0} ملفات على الأقل في الخطوة ٢.", o.min_files))
            return
        if o.max_files and len(paths) > o.max_files:
            sel = self.files.selected_path()
            if not sel:
                self.show_error(tr("هذه العملية تعمل على ملف واحد. اختر الملف المطلوب من القائمة (اضغط عليه) ثم أعد المحاولة."))
                return
            paths = [sel]
        err = self.validate(o.key, paths)
        if err:
            self.show_error(err)
            return
        self.error.hide()
        job = self.make_job(o.key, paths)
        if job:
            self.run.run(job)
