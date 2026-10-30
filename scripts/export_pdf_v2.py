"""Convert REFIT_Analysis_export.html to a clean submission PDF using headless Edge."""
import subprocess, pathlib, sys, time

ROOT    = pathlib.Path(r"C:\Users\Admin\OneDrive\Desktop\refit-nilm")
HTML_IN = ROOT / "REFIT_Analysis_export.html"
PDF_OUT = ROOT / "REFIT_TakeHome_Submission.pdf"

# Embed all figure images as base64 so they survive the PDF conversion
import base64, re

html = HTML_IN.read_text(encoding="utf-8")

# Also inject print CSS: A4, black text, no headers/footers, page breaks
PRINT_CSS = """
<style>
@page { size: A4; margin: 18mm 16mm 18mm 16mm; }
body { font-family: Calibri, Arial, sans-serif; font-size: 11pt; color: #000 !important;
       background: #fff !important; max-width: 100%; }
h1 { font-size: 18pt; font-weight: bold; }
h2 { font-size: 14pt; font-weight: bold; margin-top: 24pt; }
h3 { font-size: 12pt; font-weight: bold; }
table { border-collapse: collapse; width: 100%; font-size: 10pt; }
th, td { border: 1px solid #999; padding: 4px 8px; text-align: left; }
th { background: #f0f0f0 !important; }
img { max-width: 100%; height: auto; page-break-inside: avoid; }
pre, code { font-size: 9pt; background: #f8f8f8 !important; }
.jp-OutputArea-output { page-break-inside: avoid; }
a { color: #000 !important; text-decoration: underline; }
* { color: #000 !important; background-color: transparent !important; }
</style>
"""

# Inject CSS before </head>
html = html.replace("</head>", PRINT_CSS + "\n</head>")

# Save patched HTML
patched = ROOT / "REFIT_Analysis_print.html"
patched.write_text(html, encoding="utf-8")
print(f"Patched HTML: {patched} ({patched.stat().st_size/1024:.0f} KB)")

# Use headless Edge to print to PDF
edge_paths = [
    r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe",
    r"C:\Program Files\Microsoft\Edge\Application\msedge.exe",
]
edge = next((p for p in edge_paths if pathlib.Path(p).exists()), None)
if edge is None:
    print("ERROR: Edge not found")
    sys.exit(1)

print(f"Using Edge: {edge}")
print(f"Output PDF: {PDF_OUT}")

cmd = [
    edge,
    "--headless",
    "--disable-gpu",
    "--no-sandbox",
    "--run-all-compositor-stages-before-draw",
    f"--print-to-pdf={PDF_OUT}",
    f"--print-to-pdf-no-header",
    patched.as_uri(),
]

result = subprocess.run(cmd, capture_output=True, text=True, timeout=120)
time.sleep(3)

if PDF_OUT.exists():
    size_mb = PDF_OUT.stat().st_size / 1024 / 1024
    print(f"SUCCESS: {PDF_OUT.name} ({size_mb:.2f} MB)")
else:
    print("PDF not created. stderr:", result.stderr[:500])
    sys.exit(1)

