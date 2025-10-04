from flask import Blueprint, render_template, jsonify, request, redirect, url_for, flash, send_file, make_response
import io, csv, time
from .config import (
    FORM_URL, EVALUATION_THRESHOLD, WORKSHEET_NAME
)
from . import config
from .sheets import (
    fetch_all, compute_averages, compute_group_overall,
    a1_row_range_for_headers, get_puskesmas_index, remark, get_sheet
)

bp = Blueprint('main', __name__)

@bp.route('/')
def index():
    return render_template('index.html', form_url=FORM_URL, worksheet=WORKSHEET_NAME)

_qr_cache = {"png": None, "ts": 0}

@bp.route('/qr')
def qr_code():
    """Generate (and lightly cache) QR code PNG for the Google Form URL."""
    # Cache 5 minutes to avoid regenerating each request
    now = time.time()
    if not _qr_cache['png'] or now - _qr_cache['ts'] > 300:
        import qrcode
        img = qrcode.make(FORM_URL)
        buf = io.BytesIO()
        img.save(buf, format='PNG')
        _qr_cache['png'] = buf.getvalue()
        _qr_cache['ts'] = now
    resp = make_response(_qr_cache['png'])
    resp.headers['Content-Type'] = 'image/png'
    resp.headers['Cache-Control'] = 'public, max-age=300'
    return resp

@bp.route('/dashboard')
def dashboard():
    return render_template('dashboard.html')

@bp.route('/api/dashboard-data')
def dashboard_data():
    headers, rows = fetch_all()
    labels, avgs, overall = compute_averages(headers, rows)
    grouped = compute_group_overall(headers, rows)
    puskesmas_idx = get_puskesmas_index(headers)
    puskesmas_values = []
    if puskesmas_idx is not None:
        names = {(r[puskesmas_idx] or '<Tanpa Nama>') for r in rows if len(r) > puskesmas_idx}
        puskesmas_values = sorted(names)
    return jsonify({
        'labels': labels,
        'averages': avgs,
        'overall': overall,
        'overall_remark': remark(overall),
        'grouped': [ {'name': g[0], 'avg': g[1], 'remark': remark(g[1])} for g in grouped ],
        'threshold': EVALUATION_THRESHOLD,
        'puskesmas_list': puskesmas_values
    })

@bp.route('/manage')
def manage():
    headers, rows = fetch_all()
    return render_template('manage.html', headers=headers, rows=rows)

@bp.route('/edit/<int:rownum>', methods=['GET','POST'])
def edit_row(rownum):
    # rownum = nomor baris data (1-based, tanpa header). Di sheet actual baris = rownum + 1
    headers, rows = fetch_all()
    if rownum < 1 or rownum > len(rows):
        flash('Baris tidak ditemukan', 'error')
        return redirect(url_for('main.manage'))
    sheet_row_index = rownum + 1  # plus header
    sheet = get_sheet()
    current = sheet.row_values(sheet_row_index + 1)  # +1 untuk header offset
    if request.method == 'POST':
        new_values = [request.form.get(f'col_{i}', '') for i in range(len(headers))]
        rng = a1_row_range_for_headers(sheet_row_index + 1, len(headers))
        sheet.update(rng, [new_values])
        flash(f'Baris {rownum} diperbarui.', 'success')
        return redirect(url_for('main.manage'))
    return render_template('edit_row.html', headers=headers, current=current, rownum=rownum)

@bp.route('/delete/<int:rownum>', methods=['POST'])
def delete_row(rownum):
    headers, rows = fetch_all()
    if rownum < 1 or rownum > len(rows):
        return jsonify({'error': 'Baris tidak ditemukan'}), 404
    sheet = get_sheet()
    sheet.delete_rows(rownum + 1)  # +1 untuk header
    return jsonify({'status': 'ok'})

@bp.route('/export/summary.csv')
def export_summary():
    headers, rows = fetch_all()
    labels, avgs, overall = compute_averages(headers, rows)
    si = io.StringIO()
    writer = csv.writer(si)
    writer.writerow(['Pertanyaan','Rata-rata','Keterangan'])
    for q,a in zip(labels, avgs):
        writer.writerow([q, f"{a:.2f}", remark(a)])
    writer.writerow([])
    writer.writerow(['Rata-rata Keseluruhan', f"{overall:.2f}", remark(overall)])
    mem = io.BytesIO(si.getvalue().encode('utf-8'))
    mem.seek(0)
    return send_file(mem, as_attachment=True, download_name='CERIA_SKM_Ringkasan.csv', mimetype='text/csv')

@bp.route('/export/full.csv')
def export_full():
    headers, rows = fetch_all()
    si = io.StringIO()
    writer = csv.writer(si)
    writer.writerow(headers)
    for r in rows:
        vals = r + [''] * (len(headers) - len(r))
        writer.writerow(vals)
    mem = io.BytesIO(si.getvalue().encode('utf-8'))
    mem.seek(0)
    return send_file(mem, as_attachment=True, download_name='CERIA_SKM_DataPenuh.csv', mimetype='text/csv')
