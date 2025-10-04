# syntax=docker/dockerfile:1
FROM python:3.13-slim AS base
ENV PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PYTHONDONTWRITEBYTECODE=1

WORKDIR /app

# System deps (optional: build tools if needed)
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

# Copy application
COPY app ./app
COPY run_server.py ./
COPY service_account_info.example.py ./
# real service_account_info.py akan di-mount atau dibangun via secret

ENV CERIA_SKM_SPREADSHEET_ID="" \
    CERIA_SKM_WORKSHEET_NAME="Form Responses 2" \
    CERIA_SKM_THRESHOLD="3.0"

EXPOSE 8000
CMD ["gunicorn", "app:create_app()", "-b", "0.0.0.0:8000", "--workers", "3", "--threads", "4", "--timeout", "90"]
