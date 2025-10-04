import gspread
from oauth2client.service_account import ServiceAccountCredentials
from gspread.utils import rowcol_to_a1
from .config import (
    SPREADSHEET_ID, WORKSHEET_NAME, META_COLUMNS_OFFSET,
    EXCLUDE_COLUMNS_BY_NAME, EXCLUDE_COLUMNS_BY_QUESTION,
    SCORE_MAP, EVALUATION_THRESHOLD
)
import os, json
try:
    from service_account_info import SERVICE_ACCOUNT_INFO  # type: ignore
except Exception:  # pragma: no cover
    SERVICE_ACCOUNT_INFO = {}

_init_error = None
_sheet = None

SCOPE = [
    "https://spreadsheets.google.com/feeds",
    "https://www.googleapis.com/auth/drive"
]

try:
    sa_info = SERVICE_ACCOUNT_INFO
    if (not sa_info or not sa_info.get("private_key")):
        env_json = os.getenv("CERIA_SKM_SERVICE_ACCOUNT_JSON")
        if env_json:
            try:
                sa_info = json.loads(env_json)
            except json.JSONDecodeError as je:  # pragma: no cover
                _init_error = je
    if sa_info and sa_info.get("private_key"):
        creds = ServiceAccountCredentials.from_json_keyfile_dict(sa_info, SCOPE)
        gc = gspread.authorize(creds)
        sh = gc.open_by_key(SPREADSHEET_ID)
        _sheet = sh.worksheet(WORKSHEET_NAME)
    else:
        _init_error = RuntimeError("SERVICE_ACCOUNT_INFO belum diisi.")
except Exception as e:  # pragma: no cover
    _init_error = e


def get_sheet():
    if not _sheet:
        raise RuntimeError(f"Tidak bisa akses Google Sheets: {_init_error}")
    return _sheet


def fetch_all():
    sheet = get_sheet()
    data = sheet.get_all_values()
    headers = data[0] if data else []
    rows = data[1:] if len(data) > 1 else []
    return headers, rows


def get_question_columns(headers):
    start = META_COLUMNS_OFFSET if META_COLUMNS_OFFSET is not None else 0
    indices = list(range(start, len(headers)))
    lower_exclude = {n.lower() for n in EXCLUDE_COLUMNS_BY_NAME}
    lower_ex_q = {n.lower() for n in EXCLUDE_COLUMNS_BY_QUESTION}
    if headers and headers[-1].strip().lower() in lower_exclude:
        indices.pop(-1)
    filtered = []
    for i in indices:
        name = headers[i].strip().lower()
        if name in lower_exclude or name in lower_ex_q:
            continue
        filtered.append(i)
    return filtered


def map_score(val: str) -> float:
    v = val.strip().lower()
    try:
        return float(v)
    except ValueError:
        return SCORE_MAP.get(v, 0.0)


def compute_averages(headers, rows):
    qcols = get_question_columns(headers)
    sums = [0.0] * len(qcols)
    cnts = [0] * len(qcols)
    for r in rows:
        for j, c in enumerate(qcols):
            if c < len(r):
                s = map_score(r[c])
                if s > 0:
                    sums[j] += s
                    cnts[j] += 1
    avgs = [(sums[i] / cnts[i] if cnts[i] else 0.0) for i in range(len(qcols))]
    labels = [headers[i] for i in qcols]
    overall = sum(avgs) / len(avgs) if avgs else 0.0
    return labels, avgs, overall


def compute_group_overall(headers, rows):
    try:
        idx = next(i for i, h in enumerate(headers) if h.strip().lower() == "puskesmas")
    except StopIteration:
        return []
    groups = {}
    for r in rows:
        key = r[idx] if idx < len(r) and r[idx].strip() else "<Tanpa Nama>"
        groups.setdefault(key, []).append(r)
    summary = []
    for key in sorted(groups):
        _, _, ov = compute_averages(headers, groups[key])
        summary.append((key, ov))
    return summary


def a1_row_range_for_headers(row_idx, headers_len):
    last_col = rowcol_to_a1(1, headers_len)[:-1]
    return f"A{row_idx}:{last_col}{row_idx}"


def get_puskesmas_index(headers):
    try:
        return next(i for i, h in enumerate(headers) if h.strip().lower() == "puskesmas")
    except StopIteration:
        return None


def remark(avg: float) -> str:
    return "Evaluasi Diperlukan" if avg < EVALUATION_THRESHOLD else "OK"
