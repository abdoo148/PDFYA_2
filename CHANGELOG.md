# Changelog

## 1.5.0
- **Much faster OCR and PDF → Word**: pages are processed in parallel on several CPU cores (a 12-page PDF → Word went from ~49 s to ~13 s), with page-by-page progress and instant cancel.
- **Word / Excel / PowerPoint → PDF** is faster and safer: one Office instance per batch, silent opening (no hidden dialogs or macros), a time estimate while converting, real cancel and timeouts, and password-protected files fail quickly with a clear message.
- The app stays responsive during Office conversions.
- Update check now reads the latest GitHub release.

## 1.4.0
- **Edit PDF** page: edit existing text, add text and images, highlight / underline / strikethrough, freehand drawing, rectangles, ellipses, lines, arrows, whiteout, permanent redaction, sticky notes, undo.
- **English interface** with a full left-to-right layout; switch languages from the sidebar.
- Output file names follow the interface language.

## 1.3.0
- New interface built with Qt (PySide6): instant page switching, sidebar navigation, cards and step-by-step guidance on every page.
- Clear inline validation and friendly error messages.
- New name: **PDFYA**, by Codpact.

## 1.2.0
- Arabic + English OCR (searchable PDF, Word, plain text) using Tesseract.
- PDF → Excel (table extraction) and PDF → PowerPoint.
- Visual page organizer.
- Windows installer, portable build and update check.

## 1.1.0
- Signature library, multiple items per file, text and date stamps, batch signing.
- Page thumbnails, zoom, drag & drop, dark mode, progress with cancel.
- Password protect / unlock, rotate, delete and reorder pages, compression levels, watermark.

## 1.0.0
- First version: sign PDFs, convert between PDF / Word / Office / images, merge, split and compress.
