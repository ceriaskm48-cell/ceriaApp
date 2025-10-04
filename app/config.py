import os

# Konfigurasi dasar aplikasi web CERIA SKM
SPREADSHEET_ID = os.getenv("CERIA_SKM_SPREADSHEET_ID", "1MuNz33zko8kk-OTWz8lR_Lug9kkeJ-UgRkJmNz1TtfU")
WORKSHEET_NAME = os.getenv("CERIA_SKM_WORKSHEET_NAME", "Form Responses 2")
EVALUATION_THRESHOLD = float(os.getenv("CERIA_SKM_THRESHOLD", "3.0"))
FORM_URL = os.getenv("CERIA_SKM_FORM_URL", "https://forms.gle/9wdnAW4BkxVRGcKp7")

COLOR_PRIMARY   = "#ff8c42"
COLOR_SECONDARY = "#1e3a8a"
COLOR_INFO      = "#247ba0"
COLOR_BG        = "#f9fafb"

META_COLUMNS_OFFSET = 8

EXCLUDE_COLUMNS_BY_NAME = {
    "Saran", "Saran/masukan", "Komentar", "Feedback",
    "Umpan Balik", "Kritik", "Catatan",
    "Saran Bapak/Ibu untuk peningkatan pelayanan Puskesmas ini",
    "Puskesmas"
}
EXCLUDE_COLUMNS_BY_QUESTION = {
    "Sarana Bayak/buruk untuk peningkatan pelayanan Puskesmas ini",
    "Petugas kurang sabar, ramah, dan menghargai pasien"
}

SCORE_MAP = {
    "tidak baik": 1, "kurang baik": 2, "baik": 3, "sangat baik": 4,
    "tidak mudah": 1, "kurang mudah": 2, "mudah": 3, "sangat mudah": 4,
    "tidak sesuai": 1, "kurang sesuai": 2, "sesuai": 3, "sangat sesuai": 4,
    "tidak ramah": 1, "kurang ramah": 2, "ramah": 3, "sangat ramah": 4,
    "tidak ditanggapi": 1, "kurang ditanggapi": 2, "ditanggapi": 3, "sangat ditanggapi": 4,
}
