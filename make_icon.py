"""يولّد صور البرنامج في assets: الأيقونة، شاشة البداية، أسهم القوائم، وشعار Codpact المؤقت.

شعار Codpact الحقيقي: ضعه في assets/codpact_logo.png (يفضّل PNG بخلفية شفافة، عرض 600px تقريبًا)
وسيُستخدم تلقائيًا في الشريط الجانبي ونافذة «حول» وشاشة البداية. هذا السكربت لا يستبدله إن وُجد.
"""
import os

from PIL import Image, ImageDraw, ImageFont

here = os.path.dirname(os.path.abspath(__file__))
assets = os.path.join(here, "assets")
os.makedirs(assets, exist_ok=True)
FONTS = os.path.join(os.environ.get("WINDIR", r"C:\Windows"), "Fonts")


def font(name, size):
    try:
        return ImageFont.truetype(os.path.join(FONTS, name), size)
    except OSError:
        return ImageFont.load_default()


# ---------------------------------------------------------------- أيقونة PDFYA
S = 512
img = Image.new("RGBA", (S, S), (0, 0, 0, 0))
d = ImageDraw.Draw(img)
d.rounded_rectangle([16, 16, S - 16, S - 16], radius=110, fill=(31, 95, 191, 255))
d.polygon([(140, 92), (318, 92), (378, 152), (378, 420), (140, 420)], fill=(255, 255, 255, 255))
d.polygon([(318, 92), (318, 152), (378, 152)], fill=(200, 215, 240, 255))
for y in (170, 210, 250):
    d.rounded_rectangle([172, y, 340, y + 14], radius=7, fill=(205, 214, 228, 255))
pts = [(170, 360), (195, 318), (215, 352), (240, 300), (262, 362), (290, 322), (312, 350), (348, 336)]
d.line(pts, fill=(20, 40, 120, 255), width=16, joint="curve")
d.line([(166, 384), (352, 384)], fill=(31, 95, 191, 255), width=6)
img.resize((256, 256), Image.LANCZOS).save(os.path.join(assets, "icon.png"))
img.save(os.path.join(assets, "icon.ico"), sizes=[(16, 16), (24, 24), (32, 32), (48, 48), (64, 64), (128, 128), (256, 256)])

# ---------------------------------------------------------------- أسهم القوائم المنسدلة (فاتح/داكن)
for name, color in (("arrow_light.png", (102, 112, 133, 255)), ("arrow_dark.png", (154, 163, 175, 255))):
    a = Image.new("RGBA", (24, 16), (0, 0, 0, 0))
    ImageDraw.Draw(a).polygon([(2, 3), (22, 3), (12, 14)], fill=color)
    a.save(os.path.join(assets, name))

# ---------------------------------------------------------------- شعار Codpact (مؤقت إن لم يوجد الحقيقي)
logo_path = os.path.join(assets, "codpact_logo.png")
if not os.path.exists(logo_path):
    logo = Image.new("RGBA", (600, 160), (0, 0, 0, 0))
    ld = ImageDraw.Draw(logo)
    ld.rounded_rectangle([10, 20, 130, 140], radius=30, fill=(15, 35, 64, 255))
    ld.text((70, 80), "</>", font=font("consolab.ttf", 50), fill=(76, 141, 240, 255), anchor="mm")
    ld.text((150, 80), "Codpact", font=font("segoeuib.ttf", 96), fill=(15, 35, 64, 255), anchor="lm")
    logo = logo.crop(logo.getbbox())
    logo.save(logo_path)
    print("assets/codpact_logo.png (مؤقت — استبدله بالشعار الحقيقي)")
logo = Image.open(logo_path).convert("RGBA")

# ---------------------------------------------------------------- شاشة البداية
splash = Image.new("RGB", (460, 280), (255, 255, 255))
sd = ImageDraw.Draw(splash)
sd.rectangle([0, 0, 460, 6], fill=(31, 95, 191))
ic = img.resize((96, 96), Image.LANCZOS)
splash.paste(ic, (182, 30), ic)
sd.text((230, 150), "PDFYA", font=font("segoeuib.ttf", 34), fill=(16, 35, 63), anchor="mm")
sd.text((230, 205), "by", font=font("segoeui.ttf", 13), fill=(102, 112, 133), anchor="mm")
lg = logo.copy()
lg.thumbnail((180, 40), Image.LANCZOS)
splash.paste(lg, ((460 - lg.width) // 2, 220), lg)
splash.save(os.path.join(assets, "splash.png"))
print("assets/icon.ico, assets/icon.png, assets/splash.png")
