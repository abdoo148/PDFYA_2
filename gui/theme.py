"""ألوان وأنماط الواجهة (فاتح/داكن) عبر Qt Style Sheets."""
import os
import sys

from PySide6.QtGui import QColor, QPalette


def _asset(name):
    base = getattr(sys, "_MEIPASS", os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    return os.path.join(base, "assets", name).replace("\\", "/")

LIGHT = dict(
    bg="#F3F5F9", surface="#FFFFFF", surface2="#EEF1F6", border="#DCE1E8", text="#1B2430",
    muted="#667085", accent="#1F5FBF", accent_hover="#184EA0", accent_soft="#E5EDFB",
    success="#1A7F37", success_hover="#146C2E", danger="#C62828", danger_hover="#A12020",
    warn="#B26A00", warn_soft="#FFF4E0", info_soft="#E8F1FD", canvas="#D9DDE4",
    sidebar="#10233F", sidebar_text="#C7D3E6", sidebar_hover="#1B3459",
)
DARK = dict(
    bg="#14171C", surface="#1D2128", surface2="#262B33", border="#363C47", text="#E6E9EE",
    muted="#9AA3AF", accent="#4C8DF0", accent_hover="#3A78D8", accent_soft="#1F3049",
    success="#2EA043", success_hover="#268A39", danger="#E05252", danger_hover="#C43F3F",
    warn="#E3A33B", warn_soft="#3A2E17", info_soft="#1E2B3D", canvas="#101215",
    sidebar="#0C1626", sidebar_text="#B8C4D6", sidebar_hover="#172740",
)

_current = {"name": "light"}


def colors():
    return DARK if _current["name"] == "dark" else LIGHT


def is_dark():
    return _current["name"] == "dark"


def apply(app, name):
    _current["name"] = "dark" if name == "dark" else "light"
    c = colors()
    pal = QPalette()
    for role, key in ((QPalette.Window, "bg"), (QPalette.Base, "surface"), (QPalette.AlternateBase, "surface2"),
                      (QPalette.Text, "text"), (QPalette.WindowText, "text"), (QPalette.Button, "surface2"),
                      (QPalette.ButtonText, "text"), (QPalette.Highlight, "accent"),
                      (QPalette.ToolTipBase, "surface"), (QPalette.ToolTipText, "text"),
                      (QPalette.PlaceholderText, "muted")):
        pal.setColor(role, QColor(c[key]))
    pal.setColor(QPalette.HighlightedText, QColor("#FFFFFF"))
    app.setPalette(pal)
    from i18n import is_rtl
    app.setStyleSheet(QSS.format(arrow=_asset("arrow_dark.png" if is_dark() else "arrow_light.png"),
                                 align="right" if is_rtl() else "left", **c))


QSS = """
QMainWindow, QDialog, #content {{ background: {bg}; }}
QToolTip {{ background: {surface}; color: {text}; border: 1px solid {border}; padding: 6px; border-radius: 6px; }}

/* ---- الشريط الجانبي */
#sidebar {{ background: {sidebar}; }}
#sidebar QLabel {{ color: {sidebar_text}; }}
#appName {{ color: #FFFFFF; font-size: 18pt; font-weight: 800; }}
#appTagline {{ color: {sidebar_text}; font-size: 9pt; }}
#publisherLogo {{ background: #FFFFFF; border-radius: 8px; padding: 6px 10px; }}
#navBtn {{ background: transparent; color: {sidebar_text}; border: none; border-radius: 10px;
          padding: 11px 14px; text-align: {align}; font-size: 11pt; }}
#navBtn:hover {{ background: {sidebar_hover}; }}
#navBtn:checked {{ background: {accent}; color: #FFFFFF; font-weight: 600; }}
#sideSmall {{ background: transparent; color: {sidebar_text}; border: 1px solid {sidebar_hover};
             border-radius: 8px; padding: 7px 10px; }}
#sideSmall:hover {{ background: {sidebar_hover}; }}

/* ---- العناوين والنصوص */
#h1 {{ font-size: 17pt; font-weight: 700; }}
#h2 {{ font-size: 11.5pt; font-weight: 700; }}
#muted, #subtitle {{ color: {muted}; }}
#subtitle {{ font-size: 10.5pt; }}
#small {{ color: {muted}; font-size: 9pt; }}
#errorText {{ color: {danger}; font-weight: 600; }}
#status {{ color: {muted}; }}
#status[tone="ok"] {{ color: {success}; }}
#status[tone="error"] {{ color: {danger}; }}
#status[tone="warn"] {{ color: {warn}; }}
#helpIcon {{ font-size: 13pt; }}
#version {{ font-size: 8.5pt; }}
#preview {{ background: #FFFFFF; border-radius: 8px; }}
#dropZone {{ color: {muted}; border: 2px dashed {border}; border-radius: 10px; padding: 20px; background: {surface}; }}

/* ---- البطاقات */
#card {{ background: {surface}; border: 1px solid {border}; border-radius: 12px; }}
#help {{ background: {info_soft}; border-radius: 10px; }}
#help[tone="warn"] {{ background: {warn_soft}; }}
#banner {{ background: {accent_soft}; border: 1px solid {accent}; border-radius: 10px; }}

/* ---- خطوات */
#step {{ background: {surface2}; color: {muted}; border-radius: 14px; padding: 5px 12px; }}
#step[state="active"] {{ background: {accent}; color: #FFFFFF; font-weight: 600; }}
#step[state="done"] {{ background: {accent_soft}; color: {accent}; }}

/* ---- مربعات الاختيار (بلاطات) */
#tile {{ background: {surface}; border: 1px solid {border}; border-radius: 10px; padding: 10px; text-align: {align}; }}
#tile:hover {{ border-color: {accent}; }}
#tile:checked {{ background: {accent_soft}; border: 2px solid {accent}; }}
#toolBtn {{ padding: 7px 6px; }}
#toolBtn:checked {{ background: {accent}; color: #FFFFFF; border: none; font-weight: 600; }}
#tileTitle {{ font-weight: 700; font-size: 10.5pt; background: transparent; }}
#tileDesc {{ color: {muted}; font-size: 9pt; background: transparent; }}

/* ---- الأزرار */
QPushButton {{ background: {surface2}; border: 1px solid {border}; border-radius: 8px; padding: 7px 14px; }}
QPushButton:hover {{ border-color: {accent}; }}
QPushButton:pressed {{ background: {accent_soft}; }}
QPushButton:disabled {{ color: {muted}; background: {surface2}; border-color: {surface2}; }}
QPushButton[kind="primary"] {{ background: {accent}; color: #FFFFFF; border: none; font-weight: 600; }}
QPushButton[kind="primary"]:hover {{ background: {accent_hover}; }}
QPushButton[kind="success"] {{ background: {success}; color: #FFFFFF; border: none; font-weight: 600; }}
QPushButton[kind="success"]:hover {{ background: {success_hover}; }}
QPushButton[kind="danger"] {{ background: transparent; color: {danger}; border: 1px solid {danger}; }}
QPushButton[kind="danger"]:hover {{ background: {danger}; color: #FFFFFF; }}
QPushButton[kind="flat"] {{ background: transparent; border: none; color: {accent}; padding: 4px 6px; }}
QPushButton[kind="flat"]:hover {{ text-decoration: underline; }}
QPushButton[kind="primary"]:disabled, QPushButton[kind="success"]:disabled {{ background: {border}; color: {muted}; }}
QPushButton[size="big"] {{ padding: 11px 18px; font-size: 11pt; }}

/* ---- الحقول */
QLineEdit, QComboBox, QSpinBox, QTextEdit, QPlainTextEdit {{
    background: {surface}; border: 1px solid {border}; border-radius: 8px; padding: 6px 8px; }}
QLineEdit:focus, QComboBox:focus, QSpinBox:focus, QTextEdit:focus {{ border-color: {accent}; }}
QComboBox::drop-down {{ border: none; width: 24px; }}
QComboBox::down-arrow {{ image: url({arrow}); width: 10px; height: 7px; }}
QComboBox QAbstractItemView {{ background: {surface}; border: 1px solid {border}; selection-background-color: {accent}; }}
QCheckBox {{ spacing: 8px; }}

QListWidget {{ background: {surface}; border: 1px solid {border}; border-radius: 10px; padding: 4px; outline: none; }}
QListWidget::item {{ padding: 6px; border-radius: 6px; }}
QListWidget::item:selected {{ background: {accent_soft}; color: {text}; }}
QListWidget::item:hover {{ background: {surface2}; }}
#thumbs {{ background: {bg}; border: none; }}
#thumbs::item {{ border: 2px solid transparent; }}
#thumbs::item:selected {{ border: 2px solid {accent}; background: {accent_soft}; }}

QProgressBar {{ background: {surface2}; border: none; border-radius: 5px; height: 10px; text-align: center; color: transparent; }}
QProgressBar::chunk {{ background: {accent}; border-radius: 5px; }}

QSlider::groove:horizontal {{ height: 6px; background: {surface2}; border-radius: 3px; }}
QSlider::sub-page:horizontal {{ background: {accent}; border-radius: 3px; }}
QSlider::handle:horizontal {{ background: {surface}; border: 2px solid {accent}; width: 14px; height: 14px; margin: -6px 0; border-radius: 9px; }}

QScrollArea {{ border: none; background: transparent; }}
QScrollArea > QWidget > QWidget {{ background: transparent; }}
QScrollBar:vertical {{ background: transparent; width: 10px; margin: 2px; }}
QScrollBar::handle:vertical {{ background: {border}; border-radius: 4px; min-height: 30px; }}
QScrollBar:horizontal {{ background: transparent; height: 10px; margin: 2px; }}
QScrollBar::handle:horizontal {{ background: {border}; border-radius: 4px; min-width: 30px; }}
QScrollBar::add-line, QScrollBar::sub-line {{ width: 0; height: 0; }}
QGraphicsView {{ background: {canvas}; border: none; border-radius: 10px; }}
#emptyState {{ background: {canvas}; border-radius: 10px; }}
QMenu {{ background: {surface}; border: 1px solid {border}; }}
QMenu::item:selected {{ background: {accent_soft}; }}
"""
