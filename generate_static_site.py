"""Generate static snapshot (read-only) of CERIA SKM dashboard for GitHub Pages.

This script:
 1. Connects to Google Sheets using service account JSON from env
 2. Computes metrics (per question, overall, per Puskesmas)
 3. Emits docs/ directory with:
    - index.html (landing + quick summary + link dashboard)
    - dashboard.html (interactive chart using Chart.js fed by data.json)
    - data.json (metrics & raw processed data)
    - summary.csv (ringkasan per pertanyaan + overall)
    - full.csv (seluruh baris sheet)
    - qr.png (QR kode menuju Google Form)
    - style.css (copied from app static for consistent styling)

Secrets / Inputs (provide as GitHub Actions secrets):
  CERIA_SKM_SERVICE_ACCOUNT_JSON   -> full JSON (multiline accepted)
  CERIA_SKM_SPREADSHEET_ID         -> sheet ID
  CERIA_SKM_WORKSHEET_NAME         -> worksheet/tab name

NOTE: Do NOT publish the service account JSON; this script only uses it runtime.
"""
from __future__ import annotations
import os, json, textwrap, csv, io, statistics
from pathlib import Path
import qrcode
import gspread
from oauth2client.service_account import ServiceAccountCredentials

SCOPE = [
    "https://spreadsheets.google.com/feeds",
    "https://www.googleapis.com/auth/drive"
]

SPREADSHEET_ID = os.getenv("CERIA_SKM_SPREADSHEET_ID") or os.getenv("SPREADSHEET_ID")
WORKSHEET_NAME = os.getenv("CERIA_SKM_WORKSHEET_NAME", "Form Responses 2")
THRESHOLD = float(os.getenv("CERIA_SKM_THRESHOLD", "3.0"))
FORM_URL = os.getenv("CERIA_SKM_FORM_URL", "https://forms.gle/9wdnAW4BkxVRGcKp7")

if not SPREADSHEET_ID:
    raise SystemExit("Missing CERIA_SKM_SPREADSHEET_ID environment variable")

sa_raw = os.getenv("CERIA_SKM_SERVICE_ACCOUNT_JSON")
if not sa_raw:
    raise SystemExit("Missing CERIA_SKM_SERVICE_ACCOUNT_JSON secret")
try:
    sa_info = json.loads(sa_raw)
except json.JSONDecodeError as e:  # pragma: no cover
    raise SystemExit(f"Invalid service account JSON: {e}")

creds = ServiceAccountCredentials.from_json_keyfile_dict(sa_info, SCOPE)
gc = gspread.authorize(creds)
ws = gc.open_by_key(SPREADSHEET_ID).worksheet(WORKSHEET_NAME)
values = ws.get_all_values()
headers = values[0] if values else []
rows = values[1:] if len(values) > 1 else []

# Configuration borrowed from app/config.py (ensure consistency)
META_COLUMNS_OFFSET = 8
EXCLUDE_COLUMNS_BY_NAME = {n.lower() for n in {
    "Saran", "Saran/masukan", "Komentar", "Feedback", "Umpan Balik", "Kritik", "Catatan",
    "Saran Bapak/Ibu untuk peningkatan pelayanan Puskesmas ini", "Puskesmas"
}}
EXCLUDE_COLUMNS_BY_QUESTION = {n.lower() for n in {
    "Sarana Bayak/buruk untuk peningkatan pelayanan Puskesmas ini",
    "Petugas kurang sabar, ramah, dan menghargai pasien"
}}
SCORE_MAP = {
    "tidak baik": 1, "kurang baik": 2, "baik": 3, "sangat baik": 4,
    "tidak mudah": 1, "kurang mudah": 2, "mudah": 3, "sangat mudah": 4,
    "tidak sesuai": 1, "kurang sesuai": 2, "sesuai": 3, "sangat sesuai": 4,
    "tidak ramah": 1, "kurang ramah": 2, "ramah": 3, "sangat ramah": 4,
    "tidak ditanggapi": 1, "kurang ditanggapi": 2, "ditanggapi": 3, "sangat ditanggapi": 4,
}

def question_columns():
    start = META_COLUMNS_OFFSET if META_COLUMNS_OFFSET is not None else 0
    idxs = list(range(start, len(headers)))
    if headers and headers[-1].strip().lower() in EXCLUDE_COLUMNS_BY_NAME:
        idxs.pop(-1)
    filtered = []
    for i in idxs:
        name = headers[i].strip().lower()
        if name in EXCLUDE_COLUMNS_BY_NAME or name in EXCLUDE_COLUMNS_BY_QUESTION:
            continue
        filtered.append(i)
    return filtered

def map_score(v: str) -> float:
    v2 = v.strip().lower()
    try:
        return float(v2)
    except ValueError:
        return SCORE_MAP.get(v2, 0.0)

def compute():
    qcols = question_columns()
    per_q = []
    for c in qcols:
        scores = [map_score(r[c]) for r in rows if c < len(r)]
        scores = [s for s in scores if s > 0]
        avg = (sum(scores)/len(scores)) if scores else 0.0
        per_q.append((headers[c], avg))
    labels = [x[0] for x in per_q]
    avgs = [x[1] for x in per_q]
    overall = (sum(avgs)/len(avgs)) if avgs else 0.0
    # Group by Puskesmas
    try:
        p_idx = next(i for i,h in enumerate(headers) if h.strip().lower()=="puskesmas")
    except StopIteration:
        p_idx = None
    grouped = []
    if p_idx is not None:
        groups = {}
        for r in rows:
            key = r[p_idx] if p_idx < len(r) and r[p_idx].strip() else "<Tanpa Nama>"
            groups.setdefault(key, []).append(r)
        for k in sorted(groups):
            # recompute avg for group
            g_scores = []
            for r in groups[k]:
                row_vals = []
                for c in question_columns():
                    if c < len(r):
                        sc = map_score(r[c])
                        if sc>0: row_vals.append(sc)
                if row_vals:
                    g_scores.append(sum(row_vals)/len(row_vals))
            g_avg = statistics.mean(g_scores) if g_scores else 0.0
            grouped.append({"name": k, "avg": g_avg, "remark": ("OK" if g_avg >= THRESHOLD else "Evaluasi Diperlukan")})
    data = {
        "labels": labels,
        "averages": avgs,
        "overall": overall,
        "overall_remark": "OK" if overall >= THRESHOLD else "Evaluasi Diperlukan",
        "grouped": grouped,
        "threshold": THRESHOLD,
        "puskesmas_list": sorted({ (r[p_idx] if p_idx is not None and p_idx < len(r) and r[p_idx].strip() else "<Tanpa Nama>") for r in rows }) if p_idx is not None else []
    }
    return data

data = compute()

docs = Path('docs')
docs.mkdir(exist_ok=True)

# data.json
(docs / 'data.json').write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding='utf-8')

# CSV summary
with open(docs / 'summary.csv', 'w', newline='', encoding='utf-8') as f:
    w = csv.writer(f)
    w.writerow(['Pertanyaan','Rata-rata','Keterangan'])
    for label, avg in zip(data['labels'], data['averages']):
        w.writerow([label, f"{avg:.2f}", 'OK' if avg >= THRESHOLD else 'Evaluasi Diperlukan'])
    w.writerow([])
    w.writerow(['Rata-rata Keseluruhan', f"{data['overall']:.2f}", data['overall_remark']])

# CSV full
with open(docs / 'full.csv', 'w', newline='', encoding='utf-8') as f:
    w = csv.writer(f)
    w.writerow(headers)
    for r in rows:
        w.writerow(r + [''] * (len(headers) - len(r)))

# QR code PNG
qr_img = qrcode.make(FORM_URL)
qr_img.save(docs / 'qr.png')

# Copy style (minimal) from app/static/style.css if exists
style_src = Path('app/static/style.css')
if style_src.exists():
    (docs / 'style.css').write_text(style_src.read_text(encoding='utf-8'), encoding='utf-8')
else:
    (docs / 'style.css').write_text("body{font-family:system-ui,sans-serif;margin:20px;} .badge{display:inline-block;padding:2px 6px;border-radius:4px;background:#eee;} .ok{background:#16a34a;color:#fff;} .warn{background:#dc2626;color:#fff;} table{border-collapse:collapse;width:100%;} th,td{border:1px solid #ddd;padding:6px;} th{background:#f3f4f6;} ", encoding='utf-8')

# index.html (landing)
index_html = f"""<!DOCTYPE html>
<html lang=\"id\">\n<meta charset=\"utf-8\"/>\n<title>CERIA SKM – Snapshot</title>\n<link rel=\"stylesheet\" href=\"style.css\"/>\n<body>\n<h1>CERIA SKM (Snapshot Statis)</h1>\n<p>Halaman ini adalah versi <strong>read-only</strong> yang dibangun otomatis dari Google Sheets.\n Data terakhir diambil saat build workflow GitHub Actions.</p>\n<p><a href=\"dashboard.html\">Lihat Dashboard Interaktif</a> | <a href=\"summary.csv\">Unduh Ringkasan CSV</a> | <a href=\"full.csv\">Unduh Data Penuh CSV</a></p>\n<section>\n<h2>Ringkasan Cepat</h2>\n<p>Rata-rata keseluruhan: <span class=\"badge {'ok' if data['overall_remark']=='OK' else 'warn'}\">{data['overall']:.2f} – {data['overall_remark']}</span></p>\n<img src=\"qr.png\" alt=\"QR Form\" style=\"width:160px;border:1px solid #ddd;padding:6px;background:#fff;\"/>\n<p><small>Form: <a href=\"{FORM_URL}\" target=\"_blank\">{FORM_URL}</a></small></p>\n</section>\n<hr/>\n<p style=\"font-size:12px;opacity:.7;\">Dibuat otomatis oleh generate_static_site.py</p>\n</body></html>"""
(docs / 'index.html').write_text(index_html, encoding='utf-8')

# dashboard.html (client fetches data.json and renders)
dashboard_html = """<!DOCTYPE html><html lang=\"id\"><meta charset=\"utf-8\"/><title>Dashboard – CERIA SKM</title>
<link rel=\"stylesheet\" href=\"style.css\"/>
<script src=\"https://cdn.jsdelivr.net/npm/chart.js\"></script>
<body><h1 style='margin-top:0'>Dashboard (Snapshot)</h1>
<p><a href='index.html'>&larr; Kembali</a></p>
<div id='overview'></div>
<canvas id='chart' height='120'></canvas>
<h2>Ringkasan per Pertanyaan</h2>
<table id='tblSummary'><thead><tr><th>Pertanyaan</th><th>Rata-rata</th><th>Keterangan</th></tr></thead><tbody></tbody></table>
<h2>Ringkasan per Puskesmas</h2>
<table id='tblGroup'><thead><tr><th>Puskesmas</th><th>Rata-rata</th><th>Keterangan</th></tr></thead><tbody></tbody></table>
<script>
async function load(){
  const res = await fetch('data.json');
  const d = await res.json();
  const ov = document.getElementById('overview');
  const cls = d.overall_remark==='OK' ? 'ok':'warn';
  ov.innerHTML = `<p>Rata-rata keseluruhan: <span class="badge ${cls}">${d.overall.toFixed(2)} – ${d.overall_remark}</span></p>`;
  const ctx = document.getElementById('chart').getContext('2d');
  new Chart(ctx,{type:'bar',data:{labels:d.labels,datasets:[{label:'Rata-rata',data:d.averages,backgroundColor:d.labels.map(()=> '#2563eb')}]},options:{scales:{y:{beginAtZero:true,max:4}}}});
  const tbody = document.querySelector('#tblSummary tbody');
  d.labels.forEach((l,i)=>{const avg=d.averages[i]; const rk=avg<d.threshold?'Evaluasi Diperlukan':'OK'; const c=rk==='OK'?'ok':'warn'; tbody.innerHTML+=`<tr><td>${l}</td><td>${avg.toFixed(2)}</td><td><span class='badge ${c}'>${rk}</span></td></tr>`});
  tbody.innerHTML+=`<tr><td><strong>Rata-rata Keseluruhan</strong></td><td><strong>${d.overall.toFixed(2)}</strong></td><td><span class='badge ${cls}'>${d.overall_remark}</span></td></tr>`;
  const tbodyG=document.querySelector('#tblGroup tbody');
  d.grouped.forEach(g=>{const c=g.remark==='OK'?'ok':'warn'; tbodyG.innerHTML+=`<tr><td>${g.name}</td><td>${g.avg.toFixed(2)}</td><td><span class='badge ${c}'>${g.remark}</span></td></tr>`});
}
load();
</script>
<p style='font-size:11px;opacity:.6'>Snapshot statis – fitur edit/CRUD dinonaktifkan.</p>
</body></html>"""
(docs / 'dashboard.html').write_text(dashboard_html, encoding='utf-8')

print("Static snapshot generated in ./docs")
