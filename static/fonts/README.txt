Noto Sans Ethiopic
------------------
NotoSansEthiopic-Regular.ttf
NotoSansEthiopic-Bold.ttf

Source:  https://github.com/notofonts/ethiopic
Licence: SIL Open Font License 1.1 (OFL) - redistribution permitted.
Copyright 2022 The Noto Project Authors.

Why these files are here
------------------------
ReportLab's built-in fonts (Helvetica etc.) contain no Ethiopic glyphs, so
Amharic text in exported PDFs renders as empty boxes with no error raised.
These TTFs are registered at export time by apps/reports/exporters.py.

Note that this font is Ethiopic-only: it has no Latin letters or digits.
The exporter therefore tags only Ethiopic runs with it (see `_rich()`) and
leaves Latin text and numbers in Helvetica. Do not set it as the document
font wholesale.
