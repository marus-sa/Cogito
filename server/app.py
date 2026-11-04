"""Запуск Cogito. Обработчики запросов находятся в файлах по разделам."""

import os
from flask import Flask, abort, jsonify, request, send_from_directory
from pathlib import Path
from accounts import accounts
from admin import admin
from chat import chat
from database import start_database
from study import study


PROJECT_FOLDER = Path(__file__).resolve().parent.parent


FRONTEND_FOLDER = PROJECT_FOLDER / "dist"


app = Flask(__name__, static_folder=None)
app.config["JSON_AS_ASCII"] = False
app.config["MAX_CONTENT_LENGTH"] = 1024 * 1024
start_database()

# Каждый Blueprint — обычный набор обработчиков из одного файла.
app.register_blueprint(accounts)
app.register_blueprint(admin)
app.register_blueprint(study)
app.register_blueprint(chat)


@app.errorhandler(413)
def request_too_large(error):
    return jsonify({"error": "Запрос слишком большой. Уменьшите размер прикреплённых файлов."}), 413


@app.get("/api/health")
def health():
    return jsonify({"ok": True})


@app.after_request
def add_security_headers(response):
    # Браузер и прокси не должны сохранять чужой кабинет или старую сессию.
    if request.path.startswith("/api/"):
        response.headers["Cache-Control"] = "no-store"
        response.vary.add("Cookie")
    elif response.mimetype == "text/html":
        response.headers["Cache-Control"] = "no-cache"
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
    response.headers["Permissions-Policy"] = "camera=(), microphone=(), geolocation=()"
    return response


@app.get("/")
@app.get("/<path:filename>")
def frontend(filename=""):
    """После сборки Vue и Flask работают на одном публичном адресе."""
    if filename.startswith("api/"):
        abort(404)

    requested_file = FRONTEND_FOLDER / filename
    if filename and requested_file.is_file():
        return send_from_directory(FRONTEND_FOLDER, filename)
    return send_from_directory(FRONTEND_FOLDER, "index.html")


if __name__ == "__main__":
    app.run(
        host=os.environ.get("HOST", "0.0.0.0"),
        port=int(os.environ.get("PORT", "5000")),
        debug=False,
    )
