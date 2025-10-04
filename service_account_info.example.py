# Contoh struktur service account (GANTI dengan data asli Anda lalu simpan sebagai service_account_info.py)
# File ini aman untuk di-commit. File sebenarnya (service_account_info.py) ada di .gitignore.

SERVICE_ACCOUNT_INFO = {
    "type": "service_account",
    "project_id": "YOUR_PROJECT_ID",
    "private_key_id": "YOUR_PRIVATE_KEY_ID",
    "private_key": "-----BEGIN PRIVATE KEY-----\nYOUR_KEY\n-----END PRIVATE KEY-----\n",
    "client_email": "your-service@your-project.iam.gserviceaccount.com",
    "client_id": "12345678901234567890",
    "auth_uri": "https://accounts.google.com/o/oauth2/auth",
    "token_uri": "https://oauth2.googleapis.com/token",
    "auth_provider_x509_cert_url": "https://www.googleapis.com/oauth2/v1/certs",
    "client_x509_cert_url": "https://www.googleapis.com/robot/v1/metadata/x509/your-service%40your-project.iam.gserviceaccount.com"
}
