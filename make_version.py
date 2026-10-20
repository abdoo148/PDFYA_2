"""يولّد version_info.txt (خصائص ملف EXE في ويندوز) من core.APP_VERSION، ويطبع رقم الإصدار."""
import os

import core

here = os.path.dirname(os.path.abspath(__file__))
nums = core.parse_version(core.APP_VERSION) + (0,)
text = f"""VSVersionInfo(
  ffi=FixedFileInfo(filevers={nums}, prodvers={nums}, mask=0x3f, flags=0x0, OS=0x40004,
                    fileType=0x1, subtype=0x0, date=(0, 0)),
  kids=[
    StringFileInfo([StringTable('040904B0', [
      StringStruct('CompanyName', '{core.PUBLISHER}'),
      StringStruct('FileDescription', '{core.APP_NAME} - PDF signer and converter'),
      StringStruct('FileVersion', '{core.APP_VERSION}'),
      StringStruct('InternalName', '{core.APP_NAME}'),
      StringStruct('LegalCopyright', '(C) 2026 {core.PUBLISHER} - {core.APP_LICENSE}'),
      StringStruct('OriginalFilename', '{core.APP_NAME}.exe'),
      StringStruct('ProductName', '{core.APP_NAME}'),
      StringStruct('ProductVersion', '{core.APP_VERSION}')])]),
    VarFileInfo([VarStruct('Translation', [1033, 1200])])
  ]
)
"""
with open(os.path.join(here, "version_info.txt"), "w", encoding="utf-8") as fh:
    fh.write(text)
print(core.APP_VERSION)
