"""الترجمة: النص العربي هو المفتاح، والإنجليزية في i18n_en.py.

tr("تم تحويل {0} ملف", n) يرجع النص باللغة الحالية بعد التنسيق.
اللغة تُقرأ من settings.json عند الاستيراد، وتغييرها يتطلب إعادة تشغيل البرنامج
(لأن بعض القوائم تُبنى مرة واحدة عند تحميل الوحدات).
"""
import json
import os

LANGS = {"ar": "العربية", "en": "English"}
_state = {"lang": "ar"}
_EN = None


def _settings_lang():
    base = os.environ.get("APPDATA") or os.path.expanduser("~")
    for name in ("PDFYA", "Pedo", "SignConvert"):
        try:
            with open(os.path.join(base, name, "settings.json"), encoding="utf-8") as fh:
                return json.load(fh).get("lang")
        except (OSError, ValueError):
            continue
    return None


def set_lang(code):
    _state["lang"] = code if code in LANGS else "ar"


def lang():
    return _state["lang"]


def is_rtl():
    return _state["lang"] == "ar"


def tr(text, *args, **kwargs):
    global _EN
    if _state["lang"] == "en":
        if _EN is None:
            from i18n_en import EN
            _EN = EN
        text = _EN.get(text, text)
    return text.format(*args, **kwargs) if (args or kwargs) else text


set_lang(_settings_lang() or "ar")
