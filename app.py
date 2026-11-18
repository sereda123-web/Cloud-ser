import logging
import os
import secrets

import psycopg
from psycopg.rows import dict_row
from flask import Flask, jsonify, request
from dotenv import load_dotenv

load_dotenv()

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(message)s",
)

app = Flask(__name__)
app.json.ensure_ascii = False  # кирилиця у JSON без \uXXXX

DATABASE_URL = os.getenv("DATABASE_URL", "")
ADMIN_TOKEN = os.getenv("ADMIN_TOKEN", "")
APP_TITLE = os.getenv("APP_TITLE", "Електронний журнал")
APP_VERSION = os.getenv("APP_VERSION", "1.0")

ALLOWED_STATUSES = {"present", "absent", "late"}


def get_connection():
    if not DATABASE_URL:
        raise RuntimeError("DATABASE_URL is not configured")
    return psycopg.connect(DATABASE_URL, row_factory=dict_row)


def is_admin_request():
    header = request.headers.get("Authorization", "")
    prefix = "Bearer "

    if not header.startswith(prefix) or not ADMIN_TOKEN:
        return False

    provided_token = header[len(prefix):].strip()
    return secrets.compare_digest(provided_token, ADMIN_TOKEN)


def database_unavailable(error):
    # У журнал пишемо лише тип помилки: без connection string і без токенів
    app.logger.error("Database error: %s", type(error).__name__)
    return jsonify({"error": "database unavailable"}), 503


@app.after_request
def log_request(response):
    # Заголовок Authorization у журнал не потрапляє
    app.logger.info(
        "%s %s -> %s", request.method, request.path, response.status_code
    )
    return response


@app.get("/")
def index():
    return jsonify({
        "application": APP_TITLE,
        "version": APP_VERSION,
        "status": "running",
        "endpoints": [
            "/health",
            "/api/records",
            "/api/admin/stats"
        ]
    })


@app.get("/health")
def health():
    try:
        with get_connection() as connection:
            with connection.cursor() as cursor:
                cursor.execute("SELECT 1 AS ok;")
                cursor.fetchone()

        return jsonify({
            "status": "ok",
            "database": "ok",
            "version": APP_VERSION
        }), 200

    except Exception as error:
        app.logger.error("Health check failed: %s", type(error).__name__)
        return jsonify({
            "status": "degraded",
            "database": "error",
            "version": APP_VERSION
        }), 503


@app.get("/api/records")
def get_records():
    try:
        with get_connection() as connection:
            with connection.cursor() as cursor:
                cursor.execute(
                    """
                    SELECT id, student_name, subject, status, created_at
                    FROM journal_records
                    ORDER BY id DESC;
                    """
                )
                records = cursor.fetchall()
    except (psycopg.Error, RuntimeError) as error:
        return database_unavailable(error)

    return jsonify(records)


@app.post("/api/records")
def create_record():
    if not is_admin_request():
        app.logger.warning("Unauthorized POST /api/records")
        return jsonify({"error": "Unauthorized"}), 401

    data = request.get_json(silent=True) or {}
    student_name = str(data.get("student_name", "")).strip()
    subject = str(data.get("subject", "")).strip()
    status = str(data.get("status", "present")).strip()

    if not student_name or not subject:
        return jsonify({
            "error": "student_name and subject are required"
        }), 400

    if status not in ALLOWED_STATUSES:
        return jsonify({"error": "invalid status"}), 400

    try:
        with get_connection() as connection:
            with connection.cursor() as cursor:
                cursor.execute(
                    """
                    INSERT INTO journal_records (student_name, subject, status)
                    VALUES (%s, %s, %s)
                    RETURNING id, student_name, subject, status, created_at;
                    """,
                    (student_name, subject, status)
                )
                record = cursor.fetchone()
    except (psycopg.Error, RuntimeError) as error:
        return database_unavailable(error)

    return jsonify(record), 201


@app.get("/api/admin/stats")
def admin_stats():
    if not is_admin_request():
        app.logger.warning("Unauthorized GET /api/admin/stats")
        return jsonify({"error": "Unauthorized"}), 401

    try:
        with get_connection() as connection:
            with connection.cursor() as cursor:
                cursor.execute(
                    """
                    SELECT status, COUNT(*) AS count
                    FROM journal_records
                    GROUP BY status
                    ORDER BY status;
                    """
                )
                stats = cursor.fetchall()
    except (psycopg.Error, RuntimeError) as error:
        return database_unavailable(error)

    return jsonify({
        "application": APP_TITLE,
        "version": APP_VERSION,
        "statistics": stats
    })


if __name__ == "__main__":
    # Лише для локального запуску. На Render застосунок стартує через gunicorn.
    port = int(os.getenv("PORT", "5000"))
    debug = os.getenv("FLASK_DEBUG", "0") == "1"
    app.run(host="127.0.0.1", port=port, debug=debug)
