"""النافذة الرئيسية: شريط جانبي للتنقل + الصفحات + شريط التحديثات."""
import datetime
import sys
import webbrowser

from PySide6.QtCore import QByteArray, QLibraryInfo, Qt, QTimer, QTranslator
from PySide6.QtGui import QFont, QKeySequence, QPixmap, QShortcut
from PySide6.QtWidgets import (
    QApplication, QButtonGroup, QFrame, QHBoxLayout, QLabel, QMainWindow, QMessageBox, QPushButton,
    QStackedWidget,
    QVBoxLayout, QWidget,
)

import core
from i18n import LANGS, is_rtl, tr
from gui import theme
from gui.convert_page import ConvertPage
from gui.dialogs import AboutDialog, run_update_check
from gui.edit_page import EditPage
from gui.sign_page import SignPage
from gui.tools_page import ToolsPage
from gui.widgets import app_icon, button, label, publisher_logo, resource

PAGES = [
    ("sign", tr("توقيع PDF"), "Ctrl+1"),
    ("edit", tr("تعديل PDF"), "Ctrl+2"),
    ("convert", tr("تحويل الملفات"), "Ctrl+3"),
    ("tools", tr("أدوات PDF"), "Ctrl+4"),
]


class MainWindow(QMainWindow):
    def __init__(self, settings):
        super().__init__()
        self.settings = settings
        self.setWindowTitle(f"{core.APP_NAME} — {core.APP_TAGLINE}")
        self.setWindowIcon(app_icon())
        self.setMinimumSize(1100, 680)

        root = QWidget()
        rl = QHBoxLayout(root)
        rl.setContentsMargins(0, 0, 0, 0)
        rl.setSpacing(0)
        self.setCentralWidget(root)

        # ---------------- الشريط الجانبي (يظهر يمينًا لأن الاتجاه RTL)
        side = QFrame()
        side.setObjectName("sidebar")
        side.setFixedWidth(220)
        sl = QVBoxLayout(side)
        sl.setContentsMargins(14, 18, 14, 14)
        sl.setSpacing(6)
        brand = QHBoxLayout()
        logo = QLabel()
        logo.setPixmap(QPixmap(resource("assets", "icon.png")).scaled(36, 36, Qt.KeepAspectRatio, Qt.SmoothTransformation))
        brand.addWidget(logo)
        names = QVBoxLayout()
        names.setSpacing(0)
        name = QLabel(core.APP_NAME)
        name.setObjectName("appName")
        names.addWidget(name)
        tag = QLabel(core.APP_TAGLINE)
        tag.setObjectName("appTagline")
        names.addWidget(tag)
        brand.addLayout(names, 1)
        sl.addLayout(brand)
        sl.addSpacing(18)

        self.stack = QStackedWidget()
        # الصفحات تُنشأ عند أول فتح لها لتسريع تشغيل البرنامج
        self.factories = {"sign": SignPage, "edit": EditPage, "convert": ConvertPage, "tools": ToolsPage}
        self.pages = {}
        self.nav = QButtonGroup(self)
        self.nav_btns = {}
        for key, title, shortcut in PAGES:
            b = QPushButton(title)
            b.setObjectName("navBtn")
            b.setCheckable(True)
            b.setCursor(Qt.PointingHandCursor)
            b.setToolTip(f"{title} ({shortcut})")
            b.clicked.connect(lambda _=False, k=key: self.show_page(k))
            self.nav.addButton(b)
            self.nav_btns[key] = b
            sl.addWidget(b)
            QShortcut(QKeySequence(shortcut), self, activated=lambda k=key: self.show_page(k))
        sl.addStretch(1)
        self.theme_btn = QPushButton()
        self.theme_btn.setObjectName("sideSmall")
        self.theme_btn.setCursor(Qt.PointingHandCursor)
        self.theme_btn.clicked.connect(self.toggle_theme)
        sl.addWidget(self.theme_btn)
        other = "en" if is_rtl() else "ar"
        lang_btn = QPushButton(LANGS[other])
        lang_btn.setObjectName("sideSmall")
        lang_btn.setCursor(Qt.PointingHandCursor)
        lang_btn.setToolTip("Switch the interface to English" if other == "en" else "تحويل الواجهة إلى العربية")
        lang_btn.clicked.connect(lambda: self.switch_language(other))
        sl.addWidget(lang_btn)
        about = QPushButton(tr("حول البرنامج والتحديثات"))
        about.setObjectName("sideSmall")
        about.setCursor(Qt.PointingHandCursor)
        about.clicked.connect(self.about)
        sl.addWidget(about)
        sl.addSpacing(10)
        made = QLabel(tr("من إنتاج"))
        made.setObjectName("version")
        made.setAlignment(Qt.AlignCenter)
        sl.addWidget(made)
        sl.addWidget(publisher_logo(150, 34), 0, Qt.AlignHCenter)
        ver = QLabel(tr("{0}\nالإصدار {1}", core.PUBLISHER_AR, core.APP_VERSION))
        ver.setAlignment(Qt.AlignCenter)
        ver.setObjectName("version")
        sl.addWidget(ver)
        rl.addWidget(side)

        # ---------------- المحتوى
        content = QWidget()
        content.setObjectName("content")
        cl = QVBoxLayout(content)
        cl.setContentsMargins(0, 0, 0, 0)
        cl.setSpacing(0)
        self.banner = QFrame()
        self.banner.setObjectName("banner")
        bl = QHBoxLayout(self.banner)
        bl.setContentsMargins(14, 8, 14, 8)
        self.banner_lbl = label("", wrap=False)
        bl.addWidget(self.banner_lbl, 1)
        self.banner_url = None
        bl.addWidget(button(tr("صفحة التنزيل"), lambda: self.banner_url and webbrowser.open(self.banner_url), "primary"))
        bl.addWidget(button(tr("لاحقًا"), self.banner.hide, "flat"))
        self.banner.hide()
        bw = QWidget()
        bwl = QVBoxLayout(bw)
        bwl.setContentsMargins(24, 12, 24, 0)
        bwl.addWidget(self.banner)
        cl.addWidget(bw)
        cl.addWidget(self.stack, 1)
        rl.addWidget(content, 1)

        self._theme_text()
        geo = settings.get("geometry")
        if geo:
            self.restoreGeometry(QByteArray.fromBase64(geo.encode()))
        else:
            self.resize(1280, 800)
        self.show_page(settings.get("page") if settings.get("page") in self.factories else "sign")
        QTimer.singleShot(4000, self.auto_update_check)

    def page(self, key):
        if key not in self.pages:
            self.pages[key] = self.factories[key]()
            self.stack.addWidget(self.pages[key])
        return self.pages[key]

    def show_page(self, key):
        self.stack.setCurrentWidget(self.page(key))
        self.nav_btns[key].setChecked(True)
        self.settings["page"] = key

    def _theme_text(self):
        self.theme_btn.setText(tr("الوضع الفاتح ☀") if theme.is_dark() else tr("الوضع الداكن ☾"))

    def toggle_theme(self):
        name = "light" if theme.is_dark() else "dark"
        theme.apply(QApplication.instance(), name)
        self.settings["theme"] = name
        core.save_settings(self.settings)
        self._theme_text()
        if "sign" in self.pages:
            self.pages["sign"].apply_theme()

    def switch_language(self, code):
        self.settings["lang"] = code
        core.save_settings(self.settings)
        # الرسالة باللغة الجديدة حتى يفهمها من اختارها
        if code == "en":
            title, text, yes = "Change language", "The program will restart in English now.", "Restart"
        else:
            title, text, yes = "تغيير اللغة", "سيُعاد تشغيل البرنامج الآن باللغة العربية.", "إعادة التشغيل"
        box = QMessageBox(QMessageBox.Question, title, text, parent=self)
        box.setLayoutDirection(Qt.LeftToRight if code == "en" else Qt.RightToLeft)
        ok = box.addButton(yes, QMessageBox.AcceptRole)
        box.addButton("Later" if code == "en" else "لاحقًا", QMessageBox.RejectRole)
        box.exec()
        if box.clickedButton() is ok:
            restart_app()

    def about(self):
        AboutDialog(self, self.settings, self.show_update).exec()

    def auto_update_check(self):
        today = datetime.date.today().isoformat()
        s = self.settings
        if not core.update_url() or not s.get("auto_update", True) or s.get("last_update_check") == today:
            return
        s["last_update_check"] = today
        core.save_settings(s)
        run_update_check(self, lambda res, err: res and res["newer"] and self.show_update(res))

    def show_update(self, res):
        self.banner_url = res.get("url") or None
        self.banner_lbl.setText(tr("يتوفر إصدار جديد من البرنامج: {0} (لديك {1}).", res['version'], core.APP_VERSION))
        self.banner.show()

    def closeEvent(self, e):
        self.settings["geometry"] = bytes(self.saveGeometry().toBase64()).decode()
        core.save_settings(self.settings)
        super().closeEvent(e)


def restart_app():
    """يعيد تشغيل البرنامج (نسخة EXE أو من الكود)."""
    from PySide6.QtCore import QProcess
    args = sys.argv[1:] if getattr(sys, "frozen", False) else sys.argv
    QProcess.startDetached(sys.executable, args)
    QApplication.instance().quit()


def _close_splash():
    try:
        import pyi_splash  # موجود فقط داخل نسخة PyInstaller
        pyi_splash.close()
    except Exception:  # noqa: BLE001
        pass


def run():
    QApplication.setHighDpiScaleFactorRoundingPolicy(Qt.HighDpiScaleFactorRoundingPolicy.PassThrough)
    app = QApplication(sys.argv)
    app.setApplicationName(core.APP_NAME)
    app.setLayoutDirection(Qt.RightToLeft if is_rtl() else Qt.LeftToRight)
    if is_rtl():  # أزرار النوافذ القياسية بالعربية (نعم/لا/إلغاء، نوافذ اختيار الملفات)
        translator = QTranslator(app)
        if translator.load("qtbase_ar", QLibraryInfo.path(QLibraryInfo.TranslationsPath)):
            app.installTranslator(translator)
    app.setWindowIcon(app_icon())
    app.setFont(QFont("Segoe UI", 10))
    settings = core.load_settings()
    theme.apply(app, settings.get("theme", "light"))
    win = MainWindow(settings)
    win.show()
    _close_splash()
    return app.exec()
