import hashlib
import hmac
import json
import os
import re
import secrets
import smtplib
import ssl
from datetime import datetime, timedelta, timezone
from email.message import EmailMessage
from functools import wraps
from html import escape
from pathlib import Path
from urllib.parse import urlsplit

from flask import Flask, abort, g, jsonify, request, send_from_directory
from werkzeug.security import check_password_hash, generate_password_hash

from database import connect_db, is_production, start_database

PROJECT_FOLDER = Path(__file__).resolve().parent.parent
FRONTEND_FOLDER = PROJECT_FOLDER / "dist"
COOKIE_NAME = "cogito_session"
ADMIN_RESET_TOKEN_ENV = "ADMIN_RESET_TOKEN"
ADMIN_RESET_AUTH_COOKIE = "cogito_admin_reset"
ADMIN_RESET_AUTH_COOKIE_PATH = "/api/auth/admin-password-reset"
ADMIN_RESET_AUTH_SECONDS = 15 * 60
EMAIL_VERIFICATION_SECONDS = 24 * 60 * 60
EMAIL_RESEND_COOLDOWN_SECONDS = 60
PUBLIC_REGISTER_ROLES = {"student", "parent", "tutor"}
ROLE_LABELS = {
    "student": "Ученик",
    "tutor": "Репетитор",
    "parent": "Родитель",
    "mentor": "Наставник",
    "admin": "Администратор",
}
ROLE_COLORS = {
    "student": "#b39ddb",
    "tutor": "#9ebad5",
    "parent": "#e2b9c7",
    "mentor": "#a8cdbb",
    "admin": "#e6c48e",
}

# Статические файлы отдаём ниже через frontend(). Иначе встроенный маршрут
# Flask перехватывает адреса Vue, например /register, и возвращает 404.
app = Flask(__name__, static_folder=None)
app.config["JSON_AS_ASCII"] = False
app.config["MAX_CONTENT_LENGTH"] = 1024 * 1024
start_database()


def row_to_dict(row):
    item = dict(row)
    for key in ["materials", "video", "shots", "is_read"]:
        if key in item:
            item[key] = bool(item[key])
    if "lesson_date" in item:
        item["date"] = item.pop("lesson_date")
    if "lesson_time" in item:
        item["time"] = item.pop("lesson_time")
    if "created_time" in item:
        item["time"] = item.pop("created_time")
    if "sent_time" in item:
        item["time"] = item.pop("sent_time")
    if "tutor_initials" in item:
        item["tutorInitials"] = item.pop("tutor_initials")
    if "video_link" in item:
        item["videoLink"] = item.pop("video_link")
    if "submission_comment" in item:
        item["submissionComment"] = item.pop("submission_comment")
    if "submission_link" in item:
        item["submissionLink"] = item.pop("submission_link")
    if "review_comment" in item:
        item["reviewComment"] = item.pop("review_comment")
    if "is_read" in item:
        item["read"] = item.pop("is_read")
    return item


def goal_to_dict(row):
    item = dict(row)
    item["tasks"] = json.loads(item["tasks"])
    return item


def get_data():
    data = request.get_json(silent=True)
    return data if isinstance(data, dict) else {}


def text_field(data, key, limit=300):
    value = data.get(key, "")
    return value.strip()[:limit] if isinstance(value, str) else ""


# Подтверждение почты: настройки отправителя и одноразовые ссылки.
def email_token_fingerprint(token):
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


def configured_public_app_url():
    """Безопасный базовый URL для ссылки в письме.

    Адрес берётся только из окружения хостинга, а не из заголовка Host
    входящего запроса. Так нельзя разослать ссылку на чужой сайт через
    подменённый заголовок.
    """
    value = os.environ.get("APP_URL", "").strip().rstrip("/")
    if not value:
        return None
    try:
        parsed = urlsplit(value)
    except ValueError:
        return None
    if (
        parsed.scheme not in {"http", "https"}
        or not parsed.netloc
        or parsed.username
        or parsed.password
        or parsed.query
        or parsed.fragment
        or (is_production() and parsed.scheme != "https")
    ):
        return None
    return value


def smtp_configuration():
    """Возвращает SMTP-настройки только при полном безопасном наборе."""
    host = os.environ.get("SMTP_HOST", "").strip()
    username = os.environ.get("SMTP_USERNAME", "").strip()
    password = os.environ.get("SMTP_PASSWORD", "")
    sender = os.environ.get("SMTP_FROM_EMAIL", "").strip()
    if not host or not username or not password or not re.match(r"^\S+@\S+\.\S+$", sender):
        return None
    try:
        port = int(os.environ.get("SMTP_PORT", "587"))
    except ValueError:
        return None
    if not 1 <= port <= 65535:
        return None
    from_name = re.sub(
        r"[\r\n]", " ", os.environ.get("SMTP_FROM_NAME", "Cogito — Light Hearts")
    ).strip()
    return {
        "host": host,
        "port": port,
        "username": username,
        "password": password,
        "sender": sender,
        "from_name": from_name or "Cogito",
        "use_ssl": os.environ.get("SMTP_USE_SSL", "0").strip().lower() in {"1", "true", "yes"},
        "use_tls": os.environ.get("SMTP_USE_TLS", "1").strip().lower() not in {"0", "false", "no"},
    }


def email_verification_url(token):
    base_url = configured_public_app_url()
    if not base_url:
        return None
    # Fragment не отправляется серверу при переходе по ссылке и не попадает
    # в обычные access-логи. Vue прочитает его и отправит POST-запрос.
    return f"{base_url}/verify-email#token={token}"


def create_email_verification_token(db, user_id):
    """Выпускает новую одноразовую ссылку и аннулирует предыдущую."""
    token = secrets.token_urlsafe(32)
    now = datetime.now(timezone.utc)
    db.execute("DELETE FROM email_verification_tokens WHERE user_id = ?", (user_id,))
    db.execute(
        """INSERT INTO email_verification_tokens
        (user_id, token_fingerprint, expires_at, last_sent_at) VALUES (?, ?, ?, ?)""",
        (
            user_id,
            email_token_fingerprint(token),
            (now + timedelta(seconds=EMAIL_VERIFICATION_SECONDS)).isoformat(),
            now.isoformat(),
        ),
    )
    return token


def resend_allowed(row):
    """Ограничивает повторную отправку, не раскрывая существование почты."""
    try:
        last_sent = datetime.fromisoformat(row["last_sent_at"])
        if last_sent.tzinfo is None:
            last_sent = last_sent.replace(tzinfo=timezone.utc)
        return datetime.now(timezone.utc) - last_sent >= timedelta(
            seconds=EMAIL_RESEND_COOLDOWN_SECONDS
        )
    except (TypeError, ValueError):
        return True


def send_verification_email(user, token):
    """Отправляет письмо, не позволяя ошибке SMTP сорвать регистрацию."""
    settings = smtp_configuration()
    verification_url = email_verification_url(token)
    if not settings or not verification_url:
        return "not_configured"

    role_label = ROLE_LABELS.get(user["role"], "участник")
    recipient_name = user["first_name"].strip() or "друг"
    account_copy = (
        "После подтверждения команда Light Hearts проверит вашу заявку репетитора."
        if user["role"] == "tutor"
        else "После подтверждения вы сможете войти в личный кабинет."
    )
    text = (
        f"Здравствуйте, {recipient_name}!\n\n"
        f"Вы зарегистрировались в Cogito как {role_label.lower()}.\n"
        f"{account_copy}\n\n"
        f"Подтвердите электронную почту по ссылке:\n{verification_url}\n\n"
        "Ссылка действует 24 часа. Если это были не вы, просто проигнорируйте письмо."
    )
    html = (
        '<div style="font-family:Arial,sans-serif;color:#312b3d;line-height:1.55">'
        f'<h2 style="color:#6950a5">Здравствуйте, {escape(recipient_name)}!</h2>'
        f"<p>Вы зарегистрировались в <b>Cogito</b> как {escape(role_label.lower())}.</p>"
        f"<p>{escape(account_copy)}</p>"
        f'<p><a href="{escape(verification_url, quote=True)}" '
        'style="display:inline-block;padding:12px 18px;border-radius:9px;color:#fff;'
        'background:#6950a5;text-decoration:none;font-weight:bold">Подтвердить почту</a></p>'
        '<p style="font-size:13px;color:#716878">Ссылка действует 24 часа. Если вы не регистрировались, '
        "просто проигнорируйте это письмо.</p></div>"
    )
    message = EmailMessage()
    message["Subject"] = "Подтвердите регистрацию в Cogito"
    message["From"] = f'{settings["from_name"]} <{settings["sender"]}>'
    message["To"] = user["email"]
    message.set_content(text)
    message.add_alternative(html, subtype="html")

    try:
        if settings["use_ssl"]:
            smtp_client = smtplib.SMTP_SSL(
                settings["host"], settings["port"], timeout=10, context=ssl.create_default_context()
            )
        else:
            smtp_client = smtplib.SMTP(settings["host"], settings["port"], timeout=10)
        with smtp_client as smtp:
            smtp.ehlo()
            if not settings["use_ssl"] and settings["use_tls"]:
                smtp.starttls(context=ssl.create_default_context())
                smtp.ehlo()
            smtp.login(settings["username"], settings["password"])
            smtp.send_message(message)
    except (OSError, smtplib.SMTPException, ValueError):
        # Лог помогает владельцу настроить хостинг, но никогда не содержит
        # SMTP-пароль и не отправляется регистрирующемуся пользователю.
        app.logger.exception("Не удалось отправить письмо подтверждения регистрации")
        return "failed"
    return "sent"


# Служебное восстановление администратора. Проверки одноразовых кодов обязательны.
def configured_admin_reset_token():
    """Возвращает одноразовый код сброса только на опубликованном сайте.

    Локальная база не должна получить такой обходной путь: там администратора
    создают через форму только для этого компьютера. Сам код остаётся только в
    переменных окружения хостинга и никогда не отдаётся клиенту.
    """
    token = os.environ.get(ADMIN_RESET_TOKEN_ENV, "").strip()
    # Короткий код легко подобрать, поэтому форма намеренно остаётся скрытой,
    # пока в хостинге не задан случайный код хотя бы из 32 символов.
    return token if is_production() and len(token) >= 32 else None


def reset_token_fingerprint(token):
    """Фиксированная SHA-256-отметка без сохранения самого кода."""
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


def reset_token_matches(submitted_token, configured_token):
    """Сверяет коды за одинаковое время, не раскрывая код из окружения."""
    if not isinstance(submitted_token, str):
        return False
    return hmac.compare_digest(
        hashlib.sha256(submitted_token.strip().encode("utf-8")).digest(),
        hashlib.sha256(configured_token.encode("utf-8")).digest(),
    )


def reset_authorization_is_valid():
    """Проверяет короткую HTTP-only сессию для уже подтверждённого кода."""
    authorization = request.cookies.get(ADMIN_RESET_AUTH_COOKIE, "")
    if not authorization:
        return False

    db = connect_db()
    try:
        row = db.execute(
            """SELECT 1 FROM admin_password_reset_authorizations
            WHERE token_fingerprint = ? AND expires_at > ?""",
            (reset_token_fingerprint(authorization), datetime.now(timezone.utc).isoformat()),
        ).fetchone()
        return bool(row)
    except Exception:
        return False
    finally:
        db.close()


def set_reset_authorization_cookie(response, authorization):
    """Сохраняет подтверждение кода в браузере, не раскрывая его JavaScript."""
    response.set_cookie(
        ADMIN_RESET_AUTH_COOKIE,
        authorization,
        max_age=ADMIN_RESET_AUTH_SECONDS,
        httponly=True,
        secure=is_production(),
        samesite="Strict",
        path=ADMIN_RESET_AUTH_COOKIE_PATH,
    )
    return response


def clear_reset_authorization_cookie(response):
    response.delete_cookie(ADMIN_RESET_AUTH_COOKIE, path=ADMIN_RESET_AUTH_COOKIE_PATH)
    return response


def admin_reset_error(status=403):
    """Один ответ для неверного кода, почты и повторного использования."""
    return (
        jsonify({"error": "Не удалось сбросить пароль. Проверьте данные и попробуйте снова."}),
        status,
    )


def admin_reset_available(configured_token):
    """Показывает форму, только пока код действительно можно применить."""
    if not configured_token:
        return False
    db = connect_db()
    try:
        used = db.execute(
            "SELECT 1 FROM admin_password_reset_tokens WHERE token_fingerprint = ?",
            (reset_token_fingerprint(configured_token),),
        ).fetchone()
        active_admins = db.execute("""SELECT COUNT(*) AS count FROM users
            WHERE role = 'admin' AND account_status = 'active'""").fetchone()
        return not bool(used) and active_admins["count"] == 1
    except Exception:
        # Не заявляем о доступности аварийной формы, если базу нельзя
        # проверить. Детали ошибки не отправляем и не логируем.
        return False
    finally:
        db.close()


def http_link_from(value, label="ссылку"):
    """Проверяет необязательную внешнюю HTTP(S)-ссылку для интерфейса."""
    if value is None or value == "":
        return None, None
    if not isinstance(value, str):
        return None, f"Укажите корректную {label}."

    link = value.strip()
    if not link:
        return None, None
    if len(link) > 2048 or any(char.isspace() for char in link):
        return None, f"Укажите корректную {label} (http:// или https://)."

    try:
        parsed = urlsplit(link)
    except ValueError:
        return None, f"Укажите корректную {label} (http:// или https://)."

    if (
        parsed.scheme.lower() not in {"http", "https"}
        or not parsed.hostname
        or parsed.username
        or parsed.password
    ):
        return None, f"Укажите корректную {label} (http:// или https://)."
    return link, None


def video_link_from(value):
    """Проверяет ссылку на запись занятия, включая Google Drive и Яндекс Диск."""
    return http_link_from(value, "ссылку на видео")


# Доступ: узнаём пользователя по cookie и проверяем его роль.
def get_user_from_token():
    header = request.headers.get("Authorization", "")
    token = header.replace("Bearer ", "") or request.cookies.get(COOKIE_NAME, "")
    if not token:
        return None
    db = connect_db()
    user = db.execute(
        """SELECT users.* FROM sessions
        JOIN users ON users.id = sessions.user_id
        WHERE sessions.token = ? AND sessions.expires_at > ?
        AND users.account_status = 'active' AND users.email_verified_at IS NOT NULL""",
        (token, datetime.now(timezone.utc).isoformat()),
    ).fetchone()
    db.close()
    return user


def need_login(view):
    @wraps(view)
    def wrapped(*args, **kwargs):
        user = get_user_from_token()
        if not user:
            return jsonify({"error": "Сначала войдите в аккаунт"}), 401
        g.user = user
        return view(*args, **kwargs)

    return wrapped


def role_error(*allowed_roles):
    if g.user["role"] in allowed_roles:
        return None
    return jsonify({"error": "У этой роли нет доступа к этому действию"}), 403


def full_name(user):
    return f"{user['first_name']} {user['last_name']}"


def notify_admins_about_verified_tutor(db, user):
    """Показывает заявку только после подтверждения почты репетитора."""
    admin_rows = db.execute(
        "SELECT id FROM users WHERE role = 'admin' AND account_status = 'active'"
    ).fetchall()
    for admin in admin_rows:
        db.execute(
            """INSERT INTO notifications (user_id, icon, tone, title, text, created_time, is_read)
            VALUES (?, ?, ?, ?, ?, ?, ?)""",
            (
                admin["id"],
                "UsersRound",
                "warning",
                "Новая заявка репетитора",
                f"{full_name(user)} подтвердил(а) почту и ждёт проверки аккаунта.",
                "Только что",
                0,
            ),
        )


def initials(user):
    return f"{user['first_name'][:1]}{user['last_name'][:1]}".upper()


def chat_user(user):
    """Безопасная карточка человека для списка контактов и диалогов."""
    return {
        "id": user["id"],
        "name": full_name(user),
        "initials": initials(user),
        "role": ROLE_LABELS.get(user["role"], "Участник"),
        "color": ROLE_COLORS.get(user["role"], "#b39ddb"),
        "accountStatus": user["account_status"],
    }


def chat_contact_rows(db):
    """Возвращает только тех, с кем текущий пользователь вправе начать чат."""
    current_id = g.user["id"]
    role = g.user["role"]

    if role == "admin":
        return db.execute(
            """SELECT * FROM users
            WHERE id != ? AND account_status IN ('active', 'pending')
            ORDER BY account_status, first_name, last_name""",
            (current_id,),
        ).fetchall()

    contact_ids = set()
    admin_rows = db.execute(
        "SELECT id FROM users WHERE role = 'admin' AND account_status = 'active'"
    ).fetchall()
    contact_ids.update(row["id"] for row in admin_rows)

    if role == "student":
        rows = db.execute(
            "SELECT DISTINCT tutor_id AS id FROM lessons WHERE student_id = ? AND tutor_id IS NOT NULL",
            (current_id,),
        ).fetchall()
        contact_ids.update(row["id"] for row in rows)
    elif role == "tutor":
        student_rows = db.execute(
            "SELECT DISTINCT student_id AS id FROM lessons WHERE tutor_id = ? AND student_id IS NOT NULL",
            (current_id,),
        ).fetchall()
        mentor_rows = db.execute(
            "SELECT mentor_id AS id FROM tutor_mentors WHERE tutor_id = ?",
            (current_id,),
        ).fetchall()
        contact_ids.update(row["id"] for row in [*student_rows, *mentor_rows])
    elif role == "parent":
        child_rows = db.execute(
            "SELECT student_id AS id FROM parent_students WHERE parent_id = ?",
            (current_id,),
        ).fetchall()
        tutor_rows = db.execute(
            """SELECT DISTINCT lessons.tutor_id AS id FROM lessons
            JOIN parent_students ON parent_students.student_id = lessons.student_id
            WHERE parent_students.parent_id = ? AND lessons.tutor_id IS NOT NULL""",
            (current_id,),
        ).fetchall()
        contact_ids.update(row["id"] for row in [*child_rows, *tutor_rows])
    elif role == "mentor":
        rows = db.execute(
            "SELECT tutor_id AS id FROM tutor_mentors WHERE mentor_id = ?",
            (current_id,),
        ).fetchall()
        contact_ids.update(row["id"] for row in rows)

    contact_ids.discard(current_id)
    if not contact_ids:
        return []
    placeholders = ", ".join("?" for _ in contact_ids)
    return db.execute(
        f"SELECT * FROM users WHERE id IN ({placeholders}) AND account_status = 'active' ORDER BY first_name, last_name",
        tuple(contact_ids),
    ).fetchall()


def conversation_to_dict(db, conversation, current_id):
    members = db.execute(
        """SELECT users.* FROM users
        JOIN conversation_members ON conversation_members.user_id = users.id
        WHERE conversation_members.conversation_id = ? AND users.id != ?""",
        (conversation["id"], current_id),
    ).fetchall()
    other_people = [chat_user(member) for member in members]
    last_message = db.execute(
        "SELECT * FROM messages WHERE dialog_id = ? ORDER BY id DESC LIMIT 1",
        (conversation["id"],),
    ).fetchone()
    unread = db.execute(
        """SELECT COUNT(*) AS count FROM messages
        WHERE dialog_id = ? AND sender_id != ? AND is_read = 0""",
        (conversation["id"], current_id),
    ).fetchone()["count"]

    if len(other_people) == 1:
        person = other_people[0]
    else:
        person = {
            "name": conversation["title"] or "Групповой чат",
            "initials": "ЧТ",
            "role": "Групповой чат",
            "color": "#b39ddb",
            "accountStatus": "active",
        }
    return {
        **person,
        "id": conversation["id"],
        "last": last_message["text"] if last_message else "Сообщений пока нет",
        "time": last_message["sent_time"] if last_message else "",
        "unread": unread,
    }


def student_scope():
    """Условие, которое не позволяет увидеть чужие учебные данные."""
    role = g.user["role"]
    user_id = g.user["id"]
    if role == "admin":
        return "1 = 1", ()
    if role == "student":
        return "student_id = ?", (user_id,)
    if role == "parent":
        return "student_id IN (SELECT student_id FROM parent_students WHERE parent_id = ?)", (
            user_id,
        )
    if role == "tutor":
        return "tutor_id = ?", (user_id,)
    if role == "mentor":
        return "tutor_id IN (SELECT tutor_id FROM tutor_mentors WHERE mentor_id = ?)", (user_id,)
    return "1 = 0", ()


def scoped_rows(db, table):
    where, params = student_scope()
    return db.execute(f"SELECT * FROM {table} WHERE {where} ORDER BY id DESC", params).fetchall()


def scoped_item(db, table, item_id):
    where, params = student_scope()
    return db.execute(
        f"SELECT * FROM {table} WHERE id = ? AND {where}", (item_id, *params)
    ).fetchone()


def student_by_name(db, name):
    return user_by_name(db, name, "student")


def mentor_can_manage_tutor(db, tutor_id):
    if g.user["role"] != "mentor":
        return True
    return bool(
        db.execute(
            "SELECT 1 FROM tutor_mentors WHERE mentor_id = ? AND tutor_id = ?",
            (g.user["id"], tutor_id),
        ).fetchone()
    )


def user_by_name(db, name, role):
    return db.execute(
        "SELECT * FROM users WHERE first_name || ' ' || last_name = ? AND role = ? AND account_status = 'active'",
        (name.strip(), role),
    ).fetchone()


def create_session(user_id, days=30):
    token = secrets.token_urlsafe(32)
    db = connect_db()
    expires_at = (datetime.now(timezone.utc) + timedelta(days=days)).isoformat()
    db.execute(
        "DELETE FROM sessions WHERE expires_at <= ?", (datetime.now(timezone.utc).isoformat(),)
    )
    db.execute(
        "INSERT INTO sessions (token, user_id, expires_at) VALUES (?, ?, ?)",
        (token, user_id, expires_at),
    )
    db.commit()
    db.close()
    return token


def set_session_cookie(response, token, days=30, remember=True):
    response.set_cookie(
        COOKIE_NAME,
        token,
        max_age=60 * 60 * 24 * days if remember else None,
        httponly=True,
        secure=is_production(),
        samesite="Lax",
        path="/",
    )
    return response


def user_for_frontend(row):
    user = dict(row)
    user["name"] = f"{user.pop('first_name')} {user.pop('last_name')}"
    user["availableTime"] = user.pop("available_time")
    user["childName"] = user.pop("child_name")
    user["accountStatus"] = user.pop("account_status")
    user["emailVerified"] = bool(user.pop("email_verified_at", None))
    user["avatarColor"] = user.pop("avatar_color", None)
    raw_preferences = user.pop("notification_preferences", "{}") or "{}"
    try:
        preferences = json.loads(raw_preferences)
    except (TypeError, json.JSONDecodeError):
        preferences = {}
    user["notificationPreferences"] = preferences if isinstance(preferences, dict) else {}
    user.pop("password_hash", None)
    return user


def local_admin_setup_allowed():
    """Первого администратора локально создаёт только владелец компьютера.

    На опубликованном сайте этот маршрут недоступен: там первого администратора
    создают переменные ADMIN_EMAIL и ADMIN_BOOTSTRAP_PASSWORD. Локально доступ
    закрывается сразу после создания первого админа.
    """
    return not is_production() and request.remote_addr in {"127.0.0.1", "::1"}


# Маршруты API. Каждый маршрут ниже отвечает за одно действие в интерфейсе.
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


@app.route("/api/setup/local-admin", methods=["GET", "POST"])
def local_admin_setup():
    if not local_admin_setup_allowed():
        return jsonify({"error": "Настройка доступна только на локальном компьютере"}), 403

    db = connect_db()
    has_admin = db.execute("SELECT id FROM users WHERE role = 'admin' LIMIT 1").fetchone()
    if request.method == "GET":
        db.close()
        return jsonify({"available": not bool(has_admin)})
    if has_admin:
        db.close()
        return jsonify({"error": "Первый администратор уже создан"}), 409

    data = get_data()
    first_name = data.get("firstName", "").strip()
    last_name = data.get("lastName", "").strip()
    email = data.get("email", "").strip().lower()
    password = data.get("password", "")
    if not first_name or not last_name or not re.match(r"^\S+@\S+\.\S+$", email):
        db.close()
        return jsonify({"error": "Укажите имя, фамилию и корректную почту"}), 400
    if len(password) < 12:
        db.close()
        return (
            jsonify({"error": "Пароль администратора должен содержать не менее 12 символов"}),
            400,
        )

    existing_user = db.execute("SELECT * FROM users WHERE email = ?", (email,)).fetchone()
    try:
        if existing_user:
            # У пользователя уже есть локальный аккаунт: сохраняем его записи,
            # но назначаем владельцем проекта по его явному действию в этой форме.
            db.execute(
                """UPDATE users SET first_name = ?, last_name = ?, password_hash = ?, role = 'admin',
                account_status = 'active', subjects = 'Управление проектом', email_verified_at = ? WHERE id = ?""",
                (
                    first_name,
                    last_name,
                    generate_password_hash(password),
                    datetime.now(timezone.utc).isoformat(),
                    existing_user["id"],
                ),
            )
        else:
            db.execute(
                """INSERT INTO users
                (first_name, last_name, email, password_hash, role, account_status, grade, subjects, available_time, child_name, bio,
                 email_verified_at, avatar_color, notification_preferences)
                VALUES (?, ?, ?, ?, 'admin', 'active', '', 'Управление проектом', '', '', '', ?, '', '{}')""",
                (
                    first_name,
                    last_name,
                    email,
                    generate_password_hash(password),
                    datetime.now(timezone.utc).isoformat(),
                ),
            )
        db.commit()
    except Exception:
        db.rollback()
        db.close()
        return jsonify({"error": "Не удалось создать администратора. Попробуйте ещё раз."}), 500
    user = db.execute("SELECT * FROM users WHERE email = ?", (email,)).fetchone()
    db.close()
    response = jsonify({"user": user_for_frontend(user)})
    return set_session_cookie(response, create_session(user["id"])), 201


@app.post("/api/auth/admin-password-reset/authorize")
def authorize_admin_password_reset():
    """Меняет верный код на короткую защищённую сессию для формы сброса."""
    configured_token = configured_admin_reset_token()
    submitted_token = get_data().get("token")
    if not configured_token or not reset_token_matches(submitted_token, configured_token):
        return admin_reset_error()
    if not admin_reset_available(configured_token):
        return admin_reset_error()

    authorization = secrets.token_urlsafe(32)
    expires_at = (
        datetime.now(timezone.utc) + timedelta(seconds=ADMIN_RESET_AUTH_SECONDS)
    ).isoformat()
    db = connect_db()
    try:
        # Держим только одну короткую сессию: повторный выпуск кода сразу
        # отменяет предыдущую форму восстановления.
        db.execute("DELETE FROM admin_password_reset_authorizations")
        db.execute(
            """INSERT INTO admin_password_reset_authorizations
            (token_fingerprint, expires_at) VALUES (?, ?)""",
            (reset_token_fingerprint(authorization), expires_at),
        )
        db.commit()
    except Exception:
        db.rollback()
        app.logger.exception("Не удалось подтвердить код восстановления администратора")
        return admin_reset_error()
    finally:
        db.close()
    return set_reset_authorization_cookie(jsonify({"authorized": True}), authorization)


@app.route("/api/auth/admin-password-reset", methods=["GET", "POST"])
def admin_password_reset():
    """Одноразово возвращает владельцу доступ к активному администратору.

    Этот аварийный путь включается только явной переменной окружения на
    хостинге. GET ничего не раскрывает, кроме того, доступна ли форма.
    POST не сообщает, что именно оказалось неверным, чтобы не позволять
    подбирать код или проверять использованный код. Почта из формы становится
    новой почтой входа: прежняя служебная почта могла быть недоступна владельцу.
    """
    configured_token = configured_admin_reset_token()
    if request.method == "GET":
        available = admin_reset_available(configured_token)
        result = {"available": available}
        if available and reset_authorization_is_valid():
            result["authorized"] = True
        return jsonify(result)
    if not configured_token:
        return admin_reset_error(404)

    data = get_data()
    submitted_token = data.get("token")
    email = data.get("email")
    new_password = data.get("newPassword")
    authorized = reset_authorization_is_valid()
    if not authorized and not reset_token_matches(submitted_token, configured_token):
        return admin_reset_error()
    if not isinstance(email, str) or not isinstance(new_password, str):
        return admin_reset_error()
    if len(new_password) < 12:
        return (
            jsonify({"error": "Новый пароль администратора должен содержать не менее 12 символов"}),
            400,
        )

    # Сброс не умеет выбирать между администраторами: он работает, только
    # когда в базе ровно один активный админ. Но прежняя почта владельцу
    # неизвестна, поэтому указанная почта становится новой почтой входа.
    submitted_email = email.strip().lower()
    if not re.match(r"^\S+@\S+\.\S+$", submitted_email):
        return jsonify({"error": "Укажите корректную электронную почту"}), 400

    db = connect_db()
    try:
        admins = db.execute("""SELECT id, email FROM users
            WHERE role = 'admin' AND account_status = 'active'
            ORDER BY id""").fetchall()
        if len(admins) != 1:
            return admin_reset_error()
        admin = admins[0]
        fingerprint = reset_token_fingerprint(configured_token)

        # Не оставляем повторное применение кода на откуп ошибке уникальности:
        # так оно выглядит для владельца как обычный безопасный отказ, а не
        # как внутренняя ошибка сервера.
        already_used = db.execute(
            "SELECT 1 FROM admin_password_reset_tokens WHERE token_fingerprint = ?",
            (fingerprint,),
        ).fetchone()
        if already_used:
            return admin_reset_error()

        # Нельзя перезаписать почту другого человека. В этом случае владелец
        # выбирает свободную почту, а токен остаётся действительным.
        occupied = db.execute("SELECT id FROM users WHERE email = ?", (submitted_email,)).fetchone()
        if occupied and occupied["id"] != admin["id"]:
            return (
                jsonify(
                    {
                        "error": "Эта почта уже используется. Укажите другую для входа администратора."
                    }
                ),
                409,
            )

        # PRIMARY KEY не даёт применить один код дважды. Вставка, смена
        # почты и пароля, а также закрытие старых сессий происходят в одной
        # транзакции.
        db.execute(
            """INSERT INTO admin_password_reset_tokens
            (token_fingerprint, admin_user_id, used_at) VALUES (?, ?, ?)""",
            (fingerprint, admin["id"], datetime.now(timezone.utc).isoformat()),
        )
        db.execute("DELETE FROM admin_password_reset_authorizations")
        changed = db.execute(
            """UPDATE users SET email = ?, password_hash = ?, email_verified_at = ?
            WHERE id = ? AND role = 'admin' AND account_status = 'active'""",
            (
                submitted_email,
                generate_password_hash(new_password),
                datetime.now(timezone.utc).isoformat(),
                admin["id"],
            ),
        )
        if changed.rowcount != 1:
            raise RuntimeError("Admin account changed during password reset")
        db.execute("DELETE FROM sessions WHERE user_id = ?", (admin["id"],))
        db.commit()
    except Exception:
        db.rollback()
        app.logger.exception("Не удалось выполнить сброс доступа администратора")
        return admin_reset_error()
    finally:
        db.close()
    return clear_reset_authorization_cookie(jsonify({"ok": True}))


# Аккаунты и профиль.
@app.post("/api/auth/login")
def login():
    data = get_data()
    email = text_field(data, "email").lower()
    password = data.get("password", "")
    if not email or not isinstance(password, str) or not 1 <= len(password) <= 512:
        return jsonify({"error": "Введите почту и пароль"}), 400
    db = connect_db()
    user = db.execute("SELECT * FROM users WHERE email = ?", (email,)).fetchone()
    db.close()
    if not user or not check_password_hash(user["password_hash"], password):
        return jsonify({"error": "Неверная почта или пароль"}), 400
    # Роль берём из базы, а не из выбранной кнопки на устройстве.
    if not user["email_verified_at"]:
        return (
            jsonify(
                {
                    "error": "Сначала подтвердите почту по ссылке из письма.",
                    "code": "email_not_verified",
                }
            ),
            403,
        )
    if user["account_status"] == "pending":
        return jsonify({"error": "Заявка ещё ожидает подтверждения администратора"}), 403
    if user["account_status"] != "active":
        return jsonify({"error": "Этот аккаунт сейчас недоступен"}), 403

    remember = data.get("remember", True) is True
    days = 30 if remember else 1
    response = jsonify({"user": user_for_frontend(user)})
    return set_session_cookie(response, create_session(user["id"], days), days, remember)


@app.post("/api/auth/register")
def register():
    data = get_data()
    for key in [
        "firstName",
        "lastName",
        "email",
        "role",
        "grade",
        "subjects",
        "subject",
        "time",
        "child",
        "about",
    ]:
        data[key] = text_field(data, key, 2000 if key == "about" else 300)
    data["email"] = data["email"].lower()
    required = ["firstName", "lastName", "email", "password", "role"]
    if any(not isinstance(data.get(field), str) or not data[field].strip() for field in required):
        return jsonify({"error": "Заполните обязательные поля"}), 400
    if not 6 <= len(data["password"]) <= 512:
        return jsonify({"error": "Пароль должен содержать от 6 до 512 символов"}), 400
    if not re.match(r"^\S+@\S+\.\S+$", data["email"]):
        return jsonify({"error": "Проверьте формат электронной почты"}), 400
    if data["role"] not in PUBLIC_REGISTER_ROLES:
        return (
            jsonify({"error": "Служебную роль назначает администратор после подтверждения почты"}),
            403,
        )
    if data.get("consent") is not True:
        return jsonify({"error": "Нужно согласие на обработку персональных данных"}), 400

    account_status = "pending" if data["role"] == "tutor" else "active"
    db = connect_db()
    try:
        db.execute(
            """INSERT INTO users
            (first_name, last_name, email, password_hash, role, account_status, grade, subjects, available_time, child_name, bio,
             email_verified_at, avatar_color, notification_preferences)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, NULL, '', '{}')""",
            (
                data["firstName"].strip(),
                data["lastName"].strip(),
                data["email"].strip().lower(),
                generate_password_hash(data["password"]),
                data["role"],
                account_status,
                data.get("grade", ""),
                data["subjects"] or data["subject"],
                data.get("time", ""),
                data.get("child", ""),
                data.get("about", ""),
            ),
        )
        user = db.execute(
            "SELECT * FROM users WHERE email = ?", (data["email"].strip().lower(),)
        ).fetchone()
        verification_token = create_email_verification_token(db, user["id"])
        db.commit()
    except Exception:
        db.rollback()
        db.close()
        return jsonify({"error": "Эта электронная почта уже зарегистрирована"}), 400
    db.close()
    email_status = send_verification_email(user, verification_token)
    return (
        jsonify(
            {
                "user": user_for_frontend(user),
                "needsApproval": account_status == "pending",
                "verificationRequired": True,
                "emailStatus": email_status,
            }
        ),
        201,
    )


@app.post("/api/auth/resend-email-verification")
def resend_email_verification():
    """Отправляет свежую ссылку, не раскрывая зарегистрированные адреса."""
    email = get_data().get("email", "")
    delivery_available = bool(smtp_configuration() and configured_public_app_url())
    answer = {
        "ok": True,
        "deliveryAvailable": delivery_available,
        "message": "Если этому адресу нужно подтверждение, письмо отправлено.",
    }
    if not isinstance(email, str) or not re.match(r"^\S+@\S+\.\S+$", email.strip()):
        return jsonify(answer), 202

    db = connect_db()
    try:
        user = db.execute(
            "SELECT * FROM users WHERE email = ?", (email.strip().lower(),)
        ).fetchone()
        if not user or user["email_verified_at"]:
            return jsonify(answer), 202
        existing = db.execute(
            "SELECT * FROM email_verification_tokens WHERE user_id = ?", (user["id"],)
        ).fetchone()
        if existing and not resend_allowed(existing):
            return jsonify(answer), 202
        verification_token = create_email_verification_token(db, user["id"])
        db.commit()
    except Exception:
        db.rollback()
        app.logger.exception("Не удалось подготовить повторную ссылку подтверждения")
        return jsonify(answer), 202
    finally:
        db.close()

    send_verification_email(user, verification_token)
    return jsonify(answer), 202


@app.post("/api/auth/verify-email")
def verify_email():
    token = get_data().get("token")
    if not isinstance(token, str) or len(token) < 32:
        return jsonify({"error": "Эта ссылка недействительна или уже устарела."}), 400

    fingerprint = email_token_fingerprint(token)
    now = datetime.now(timezone.utc).isoformat()
    db = connect_db()
    try:
        row = db.execute(
            """DELETE FROM email_verification_tokens
            WHERE token_fingerprint = ? AND expires_at > ? RETURNING user_id""",
            (fingerprint, now),
        ).fetchone()
        if not row:
            return jsonify({"error": "Эта ссылка недействительна или уже устарела."}), 400
        db.execute("UPDATE users SET email_verified_at = ? WHERE id = ?", (now, row["user_id"]))
        user = db.execute("SELECT * FROM users WHERE id = ?", (row["user_id"],)).fetchone()
        if user["role"] == "tutor" and user["account_status"] == "pending":
            notify_admins_about_verified_tutor(db, user)
        db.commit()
    except Exception:
        db.rollback()
        app.logger.exception("Не удалось подтвердить почту пользователя")
        return (
            jsonify(
                {
                    "error": "Не удалось подтвердить почту. Запросите новое письмо и попробуйте снова."
                }
            ),
            500,
        )
    finally:
        db.close()

    result = {
        "verified": True,
        "needsApproval": user["account_status"] == "pending",
        "user": user_for_frontend(user),
    }
    response = jsonify(result)
    if user["account_status"] == "active":
        return set_session_cookie(response, create_session(user["id"]))
    return response


@app.get("/api/auth/me")
@need_login
def current_user():
    return jsonify({"user": user_for_frontend(g.user)})


@app.post("/api/auth/logout")
def logout():
    # Даже просроченную cookie можно удалить, не требуя повторного входа.
    token = request.headers.get("Authorization", "").replace("Bearer ", "") or request.cookies.get(
        COOKIE_NAME, ""
    )
    db = connect_db()
    db.execute("DELETE FROM sessions WHERE token = ?", (token,))
    db.commit()
    db.close()
    response = jsonify({"ok": True})
    response.delete_cookie(COOKIE_NAME, path="/")
    return response


@app.route("/api/profile", methods=["GET", "PUT"])
@need_login
def profile():
    if request.method == "GET":
        return jsonify({"user": user_for_frontend(g.user)})
    data = get_data()
    requested_email = data.get("email", g.user["email"])
    if not isinstance(requested_email, str) or requested_email.strip().lower() != g.user["email"]:
        return (
            jsonify(
                {"error": "Смену почты пока выполняет координатор после проверки нового адреса."}
            ),
            400,
        )

    def profile_text(key, fallback, limit=500):
        value = data.get(key, fallback)
        if not isinstance(value, str):
            raise ValueError(key)
        return value.strip()[:limit]

    try:
        first_name = profile_text("firstName", g.user["first_name"], 80)
        last_name = profile_text("lastName", g.user["last_name"], 100)
        grade = profile_text("grade", g.user["grade"] or "", 30)
        subjects = profile_text("subjects", g.user["subjects"] or "", 300)
        available_time = profile_text("time", g.user["available_time"] or "", 300)
        child_name = profile_text("childName", g.user["child_name"] or "", 200)
        bio = profile_text("bio", g.user["bio"] or "", 2000)
    except ValueError:
        return jsonify({"error": "Проверьте формат данных профиля."}), 400
    if not first_name or not last_name:
        return jsonify({"error": "Укажите имя и фамилию."}), 400

    preferences = data.get("notificationPreferences")
    if preferences is None:
        preferences_json = g.user["notification_preferences"] or "{}"
    elif isinstance(preferences, dict) and all(
        isinstance(key, str) and isinstance(value, bool) for key, value in preferences.items()
    ):
        preferences_json = json.dumps(preferences, ensure_ascii=False)
    else:
        return jsonify({"error": "Проверьте настройки уведомлений."}), 400

    avatar_color = data.get("avatarColor", g.user["avatar_color"] or "")
    if not isinstance(avatar_color, str) or (
        avatar_color and not re.fullmatch(r"#[0-9a-fA-F]{6}", avatar_color)
    ):
        return jsonify({"error": "Выберите цвет из предложенной палитры."}), 400
    db = connect_db()
    try:
        db.execute(
            """UPDATE users SET first_name = ?, last_name = ?, grade = ?, subjects = ?,
            available_time = ?, child_name = ?, bio = ?, avatar_color = ?, notification_preferences = ? WHERE id = ?""",
            (
                first_name,
                last_name,
                grade,
                subjects,
                available_time,
                child_name,
                bio,
                avatar_color,
                preferences_json,
                g.user["id"],
            ),
        )
        db.commit()
        user = db.execute("SELECT * FROM users WHERE id = ?", (g.user["id"],)).fetchone()
    except Exception:
        db.rollback()
        app.logger.exception("Не удалось обновить профиль")
        return jsonify({"error": "Не удалось сохранить профиль. Попробуйте ещё раз."}), 500
    finally:
        db.close()
    return jsonify({"user": user_for_frontend(user)})


# Управление заявками и показатели администратора.
@app.get("/api/admin/users")
@need_login
def admin_users():
    error = role_error("admin")
    if error:
        return error
    status = request.args.get("status", "")
    db = connect_db()
    if status:
        rows = db.execute(
            "SELECT * FROM users WHERE account_status = ? ORDER BY id DESC", (status,)
        ).fetchall()
    else:
        rows = db.execute("SELECT * FROM users ORDER BY id DESC").fetchall()
    db.close()
    return jsonify({"items": [user_for_frontend(row) for row in rows]})


@app.get("/api/admin/dashboard")
@need_login
def admin_dashboard():
    """Реальные цифры для главной страницы администратора."""
    error = role_error("admin")
    if error:
        return error

    db = connect_db()
    students = db.execute(
        "SELECT COUNT(*) AS count FROM users WHERE role = 'student' AND account_status = 'active'"
    ).fetchone()["count"]
    tutors = db.execute(
        "SELECT COUNT(*) AS count FROM users WHERE role = 'tutor' AND account_status = 'active'"
    ).fetchone()["count"]
    lessons = db.execute("SELECT COUNT(*) AS count FROM lessons").fetchone()["count"]
    pending_applications = db.execute(
        "SELECT COUNT(*) AS count FROM users WHERE role = 'tutor' AND account_status = 'pending'"
    ).fetchone()["count"]
    pending_reviews = db.execute(
        "SELECT COUNT(*) AS count FROM review_lessons WHERE status = 'Ожидает проверки'"
    ).fetchone()["count"]
    subjects = db.execute(
        """SELECT COALESCE(NULLIF(subject, ''), 'Не указан') AS name, COUNT(*) AS count
        FROM lessons GROUP BY COALESCE(NULLIF(subject, ''), 'Не указан')
        ORDER BY count DESC, name ASC"""
    ).fetchall()
    db.close()
    return jsonify(
        {
            "students": students,
            "tutors": tutors,
            "lessons": lessons,
            "pendingApplications": pending_applications,
            "pendingReviews": pending_reviews,
            "subjects": [row_to_dict(row) for row in subjects],
        }
    )


@app.patch("/api/admin/users/<int:user_id>")
@need_login
def update_admin_user(user_id):
    error = role_error("admin")
    if error:
        return error
    data = get_data()
    allowed_statuses = {"active", "pending", "blocked"}
    new_status = data.get("accountStatus")
    new_role = data.get("role")
    if new_status is not None and (
        not isinstance(new_status, str) or new_status not in allowed_statuses
    ):
        return jsonify({"error": "Укажите корректный статус аккаунта"}), 400
    if new_role is not None and (not isinstance(new_role, str) or new_role not in ROLE_LABELS):
        return jsonify({"error": "Укажите корректную роль"}), 400
    if not data or not any(key in data for key in ["role", "accountStatus"]):
        return jsonify({"error": "Укажите роль или статус"}), 400
    db = connect_db()
    target_user = db.execute("SELECT * FROM users WHERE id = ?", (user_id,)).fetchone()
    if not target_user:
        db.close()
        return jsonify({"error": "Пользователь не найден"}), 404
    new_status = new_status or target_user["account_status"]
    new_role = new_role or target_user["role"]
    if user_id == g.user["id"] and (new_status != "active" or new_role != "admin"):
        db.close()
        return (
            jsonify({"error": "Нельзя менять свою роль или блокировать собственный аккаунт"}),
            400,
        )
    if (new_status == "active" or new_role in {"mentor", "admin"}) and not target_user[
        "email_verified_at"
    ]:
        db.close()
        return jsonify({"error": "Сначала пользователь должен подтвердить почту."}), 400
    role_changed = new_role != target_user["role"]
    db.execute(
        "UPDATE users SET role = ?, account_status = ? WHERE id = ?",
        (new_role, new_status, user_id),
    )
    if role_changed:
        db.execute(
            "DELETE FROM parent_students WHERE parent_id = ? OR student_id = ?", (user_id, user_id)
        )
        db.execute(
            "DELETE FROM tutor_mentors WHERE tutor_id = ? OR mentor_id = ?", (user_id, user_id)
        )
    if new_status != "active" or role_changed:
        db.execute("DELETE FROM sessions WHERE user_id = ?", (user_id,))
    db.commit()
    user = db.execute("SELECT * FROM users WHERE id = ?", (user_id,)).fetchone()
    db.close()
    return jsonify({"user": user_for_frontend(user)})


@app.route("/api/admin/relationships", methods=["GET", "POST", "DELETE"])
@need_login
def admin_relationships():
    error = role_error("admin")
    if error:
        return error
    db = connect_db()
    try:
        if request.method == "GET":
            parents = db.execute("SELECT parent_id, student_id FROM parent_students").fetchall()
            mentors = db.execute("SELECT mentor_id, tutor_id FROM tutor_mentors").fetchall()
            return jsonify(
                {
                    "parents": [dict(row) for row in parents],
                    "mentors": [dict(row) for row in mentors],
                }
            )

        data = get_data()
        # Имена таблиц и столбцов выбираются только из этого списка, не из запроса.
        kinds = {
            "parent_student": ("parent_students", "parent_id", "student_id", "parent", "student"),
            "mentor_tutor": ("tutor_mentors", "mentor_id", "tutor_id", "mentor", "tutor"),
        }
        kind = data.get("kind")
        if not isinstance(kind, str) or kind not in kinds:
            return jsonify({"error": "Выберите тип связи"}), 400
        first_id, second_id = data.get("firstId"), data.get("secondId")
        if type(first_id) is not int or type(second_id) is not int:
            return jsonify({"error": "Выберите двух участников"}), 400
        table, first_column, second_column, first_role, second_role = kinds[kind]
        if request.method == "POST":
            for user_id, role in [(first_id, first_role), (second_id, second_role)]:
                user = db.execute("SELECT * FROM users WHERE id = ?", (user_id,)).fetchone()
                if (
                    not user
                    or user["role"] != role
                    or user["account_status"] != "active"
                    or not user["email_verified_at"]
                ):
                    return (
                        jsonify(
                            {
                                "error": "Выберите активных участников с подтверждённой почтой и нужными ролями"
                            }
                        ),
                        400,
                    )
            db.execute(
                f"INSERT INTO {table} ({first_column}, {second_column}) VALUES (?, ?) ON CONFLICT DO NOTHING",
                (first_id, second_id),
            )
        else:
            db.execute(
                f"DELETE FROM {table} WHERE {first_column} = ? AND {second_column} = ?",
                (first_id, second_id),
            )
        db.commit()
        return jsonify({"ok": True}), 201 if request.method == "POST" else 200
    finally:
        db.close()


# Расписание занятий.
@app.route("/api/lessons", methods=["GET", "POST"])
@need_login
def lesson_list():
    if request.method == "POST":
        error = role_error("tutor", "mentor", "admin")
        if error:
            return error
    db = connect_db()
    if request.method == "GET":
        rows = scoped_rows(db, "lessons")
        db.close()
        return jsonify({"items": [row_to_dict(row) for row in rows]})
    data = get_data()
    student = student_by_name(db, data.get("student", ""))
    tutor = (
        g.user if g.user["role"] == "tutor" else user_by_name(db, data.get("tutor", ""), "tutor")
    )
    if not student or not tutor:
        db.close()
        return jsonify({"error": "Выберите зарегистрированных ученика и репетитора"}), 400
    if not mentor_can_manage_tutor(db, tutor["id"]):
        db.close()
        return jsonify({"error": "Этот репетитор не закреплён за вами"}), 403
    lesson_link, link_error = http_link_from(data.get("link"), "ссылку на занятие")
    if link_error:
        db.close()
        return jsonify({"error": link_error}), 400
    # RETURNING отдаёт именно нашу новую запись, а не последнюю запись другого запроса.
    row = db.execute(
        """INSERT INTO lessons
        (student, tutor, student_id, tutor_id, subject, lesson_date, lesson_time, duration, status, link, topic, materials)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, 'Запланировано', ?, ?, 0) RETURNING *""",
        (
            full_name(student),
            full_name(tutor),
            student["id"],
            tutor["id"],
            data.get("subject", ""),
            data.get("date", ""),
            data.get("time", ""),
            data.get("duration", "60 мин"),
            lesson_link or "",
            data.get("topic", ""),
        ),
    ).fetchone()
    db.commit()
    db.close()
    return jsonify({"item": row_to_dict(row)}), 201


@app.patch("/api/lessons/<int:lesson_id>")
@need_login
def lesson_update(lesson_id):
    error = role_error("tutor", "mentor", "admin")
    if error:
        return error
    data = get_data()
    db = connect_db()
    row = scoped_item(db, "lessons", lesson_id)
    if not row:
        db.close()
        return jsonify({"error": "Занятие не найдено или недоступно"}), 404
    status = data.get("status", row["status"])
    if status not in {"Запланировано", "Проведено", "Отменено", "Перенесено"}:
        db.close()
        return jsonify({"error": "Укажите корректный статус занятия"}), 400
    date = data.get("date", row["lesson_date"])
    time = data.get("time", row["lesson_time"])
    if (
        not isinstance(date, str)
        or not date.strip()
        or not isinstance(time, str)
        or not time.strip()
    ):
        db.close()
        return jsonify({"error": "Укажите новую дату и время занятия"}), 400
    db.execute(
        "UPDATE lessons SET status = ?, lesson_date = ?, lesson_time = ? WHERE id = ?",
        (status, date.strip(), time.strip(), lesson_id),
    )
    db.commit()
    row = db.execute("SELECT * FROM lessons WHERE id = ?", (lesson_id,)).fetchone()
    db.close()
    return jsonify({"item": row_to_dict(row)})


# Домашние задания: создать, сдать, проверить.
@app.route("/api/homework", methods=["GET", "POST"])
@need_login
def homework_list():
    if request.method == "POST":
        error = role_error("tutor", "mentor", "admin")
        if error:
            return error
    db = connect_db()
    if request.method == "GET":
        rows = scoped_rows(db, "homework")
        db.close()
        return jsonify({"items": [row_to_dict(row) for row in rows]})
    data = get_data()
    student = student_by_name(db, data.get("student", ""))
    tutor = (
        g.user if g.user["role"] == "tutor" else user_by_name(db, data.get("tutor", ""), "tutor")
    )
    if not student or not tutor:
        db.close()
        return jsonify({"error": "Выберите зарегистрированных ученика и репетитора"}), 400
    if not mentor_can_manage_tutor(db, tutor["id"]):
        db.close()
        return jsonify({"error": "Этот репетитор не закреплён за вами"}), 403
    attachment, link_error = http_link_from(data.get("attachment"), "ссылку на материалы")
    if link_error:
        db.close()
        return jsonify({"error": link_error}), 400
    row = db.execute(
        """INSERT INTO homework
        (title, subject, student, tutor, student_id, tutor_id, issued, deadline, status, attachment, score, description)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, 'Новые', ?, NULL, ?) RETURNING *""",
        (
            data.get("title", ""),
            data.get("subject", ""),
            full_name(student),
            full_name(tutor),
            student["id"],
            tutor["id"],
            "Сегодня",
            data.get("deadline", ""),
            attachment or "",
            data.get("description", ""),
        ),
    ).fetchone()
    db.commit()
    db.close()
    return jsonify({"item": row_to_dict(row)}), 201


@app.patch("/api/homework/<int:homework_id>/submit")
@need_login
def submit_homework(homework_id):
    error = role_error("student", "parent")
    if error:
        return error
    data = get_data()
    comment = data.get("comment", "")
    if not isinstance(comment, str) or len(comment.strip()) > 2000:
        return jsonify({"error": "Комментарий не должен превышать 2000 символов."}), 400
    submission_link, link_error = http_link_from(
        data.get("submissionLink"), "ссылку на выполненную работу"
    )
    if link_error:
        return jsonify({"error": link_error}), 400
    db = connect_db()
    row = scoped_item(db, "homework", homework_id)
    if not row:
        db.close()
        return jsonify({"error": "Задание не найдено или недоступно"}), 404
    db.execute(
        """UPDATE homework SET status = 'Сданы', submission_comment = ?, submission_link = ?
        WHERE id = ?""",
        (comment.strip(), submission_link or "", homework_id),
    )
    db.commit()
    row = db.execute("SELECT * FROM homework WHERE id = ?", (homework_id,)).fetchone()
    db.close()
    return jsonify({"item": row_to_dict(row)})


@app.patch("/api/homework/<int:homework_id>/grade")
@need_login
def grade_homework(homework_id):
    error = role_error("tutor", "mentor", "admin")
    if error:
        return error
    data = get_data()
    decision = data.get("decision", "accept")
    if decision not in {"accept", "revise"}:
        return jsonify({"error": "Выберите корректное решение по работе."}), 400
    review_comment = data.get("comment", "")
    if not isinstance(review_comment, str) or len(review_comment.strip()) > 2000:
        return jsonify({"error": "Комментарий не должен превышать 2000 символов."}), 400
    score = data.get("score", "")
    if decision == "accept":
        if isinstance(score, (int, float)):
            score = str(score)
        if not isinstance(score, str) or not re.fullmatch(
            r"\d+(?:[.,]\d+)?\s*/\s*\d+(?:[.,]\d+)?", score.strip()
        ):
            return jsonify({"error": "Укажите балл в формате «8 / 10»."}), 400
        saved_score = score.strip()
        status = "Проверено"
    else:
        saved_score = None
        status = "В работе"
    db = connect_db()
    row = scoped_item(db, "homework", homework_id)
    if not row:
        db.close()
        return jsonify({"error": "Задание не найдено или недоступно"}), 404
    db.execute(
        """UPDATE homework SET status = ?, score = ?, review_comment = ? WHERE id = ?""",
        (status, saved_score, review_comment.strip(), homework_id),
    )
    db.commit()
    row = db.execute("SELECT * FROM homework WHERE id = ?", (homework_id,)).fetchone()
    db.close()
    return jsonify({"item": row_to_dict(row)})


# Учебные цели и подзадачи.
@app.route("/api/goals", methods=["GET", "POST"])
@need_login
def goals():
    if request.method == "POST":
        error = role_error("student")
        if error:
            return error
    db = connect_db()
    if request.method == "GET":
        rows = scoped_rows(db, "goals")
        db.close()
        return jsonify({"items": [goal_to_dict(row) for row in rows]})
    data = get_data()
    row = db.execute(
        """INSERT INTO goals (title, subject, deadline, tutor, student_id, tutor_id, description, tasks)
        VALUES (?, ?, ?, ?, ?, NULL, ?, ?) RETURNING *""",
        (
            data.get("title", ""),
            data.get("subject", ""),
            data.get("deadline", ""),
            "Не назначен",
            g.user["id"],
            data.get("description", ""),
            json.dumps(data.get("tasks", []), ensure_ascii=False),
        ),
    ).fetchone()
    db.commit()
    db.close()
    return jsonify({"item": goal_to_dict(row)}), 201


@app.patch("/api/goals/<int:goal_id>/tasks/<int:task_id>")
@need_login
def toggle_goal_task(goal_id, task_id):
    error = role_error("student", "tutor", "mentor", "admin")
    if error:
        return error
    db = connect_db()
    row = scoped_item(db, "goals", goal_id)
    if not row:
        db.close()
        return jsonify({"error": "Цель не найдена"}), 404
    tasks = json.loads(row["tasks"])
    for task in tasks:
        if task["id"] == task_id:
            task["done"] = not task["done"]
    db.execute(
        "UPDATE goals SET tasks = ? WHERE id = ?", (json.dumps(tasks, ensure_ascii=False), goal_id)
    )
    db.commit()
    updated = db.execute("SELECT * FROM goals WHERE id = ?", (goal_id,)).fetchone()
    db.close()
    return jsonify({"item": goal_to_dict(updated)})


# Личные чаты и уведомления.
@app.get("/api/chat/contacts")
@need_login
def chat_contacts():
    db = connect_db()
    rows = chat_contact_rows(db)
    db.close()
    return jsonify({"items": [chat_user(row) for row in rows]})


@app.route("/api/conversations", methods=["GET", "POST"])
@need_login
def conversations():
    db = connect_db()
    if request.method == "GET":
        rows = db.execute(
            """SELECT conversations.* FROM conversations
            JOIN conversation_members ON conversation_members.conversation_id = conversations.id
            WHERE conversation_members.user_id = ? ORDER BY conversations.id DESC""",
            (g.user["id"],),
        ).fetchall()
        items = [conversation_to_dict(db, row, g.user["id"]) for row in rows]
        db.close()
        return jsonify({"items": items})

    recipient_id = get_data().get("recipientId")
    if not isinstance(recipient_id, int):
        db.close()
        return jsonify({"error": "Выберите получателя"}), 400
    allowed = {row["id"] for row in chat_contact_rows(db)}
    if recipient_id not in allowed:
        db.close()
        return jsonify({"error": "С этим пользователем пока нельзя начать диалог"}), 403

    existing = db.execute(
        """SELECT conversation_id FROM conversation_members
        WHERE conversation_id IN (SELECT conversation_id FROM conversation_members WHERE user_id = ?)
        GROUP BY conversation_id
        HAVING COUNT(*) = 2
        AND SUM(CASE WHEN user_id = ? OR user_id = ? THEN 1 ELSE 0 END) = 2
        LIMIT 1""",
        (g.user["id"], g.user["id"], recipient_id),
    ).fetchone()
    if existing:
        conversation = db.execute(
            "SELECT * FROM conversations WHERE id = ?", (existing["conversation_id"],)
        ).fetchone()
        item = conversation_to_dict(db, conversation, g.user["id"])
        db.close()
        return jsonify({"item": item, "created": False})

    recipient = db.execute("SELECT * FROM users WHERE id = ?", (recipient_id,)).fetchone()
    conversation = db.execute(
        "INSERT INTO conversations (title) VALUES (?) RETURNING *", (full_name(recipient),)
    ).fetchone()
    db.executemany(
        "INSERT INTO conversation_members (conversation_id, user_id) VALUES (?, ?)",
        [(conversation["id"], g.user["id"]), (conversation["id"], recipient_id)],
    )
    db.commit()
    item = conversation_to_dict(db, conversation, g.user["id"])
    db.close()
    return jsonify({"item": item, "created": True}), 201


@app.route("/api/messages", methods=["GET", "POST"])
@need_login
def messages():
    db = connect_db()
    dialog_id = (
        request.args.get("dialog_id", type=int)
        if request.method == "GET"
        else get_data().get("dialogId")
    )
    if not isinstance(dialog_id, int):
        db.close()
        return jsonify({"error": "Выберите диалог"}), 400
    member = db.execute(
        "SELECT 1 FROM conversation_members WHERE conversation_id = ? AND user_id = ?",
        (dialog_id, g.user["id"]),
    ).fetchone()
    if not member:
        db.close()
        return jsonify({"error": "Этот диалог недоступен"}), 403
    if request.method == "GET":
        db.execute(
            "UPDATE messages SET is_read = 1 WHERE dialog_id = ? AND sender_id != ?",
            (dialog_id, g.user["id"]),
        )
        db.commit()
        rows = db.execute(
            "SELECT * FROM messages WHERE dialog_id = ? ORDER BY id", (dialog_id,)
        ).fetchall()
        db.close()
        items = []
        for row in rows:
            item = row_to_dict(row)
            item["sender"] = "me" if row["sender_id"] == g.user["id"] else "them"
            items.append(item)
        return jsonify({"items": items})
    data = get_data()
    text = data.get("text", "").strip()
    if not text or len(text) > 4000:
        db.close()
        return jsonify({"error": "Сообщение должно быть от 1 до 4000 символов"}), 400
    now = datetime.now().strftime("%H:%M")
    row = db.execute(
        "INSERT INTO messages (dialog_id, sender, sender_id, text, sent_time, is_read) VALUES (?, 'me', ?, ?, ?, 0) RETURNING *",
        (dialog_id, g.user["id"], text, now),
    ).fetchone()
    recipient_rows = db.execute(
        "SELECT user_id FROM conversation_members WHERE conversation_id = ? AND user_id != ?",
        (dialog_id, g.user["id"]),
    ).fetchall()
    for recipient in recipient_rows:
        db.execute(
            """INSERT INTO notifications (user_id, icon, tone, title, text, created_time, is_read)
            VALUES (?, ?, ?, ?, ?, ?, ?)""",
            (
                recipient["user_id"],
                "MessageCircle",
                "primary",
                "Новое сообщение",
                f"{full_name(g.user)} написал(а) вам.",
                now,
                0,
            ),
        )
    db.commit()
    db.close()
    item = row_to_dict(row)
    item["sender"] = "me"
    return jsonify({"item": item}), 201


@app.route("/api/notifications", methods=["GET", "PATCH"])
@need_login
def notifications():
    db = connect_db()
    if request.method == "GET":
        rows = db.execute(
            "SELECT * FROM notifications WHERE user_id = ? ORDER BY id DESC", (g.user["id"],)
        ).fetchall()
        db.close()
        return jsonify({"items": [row_to_dict(row) for row in rows]})
    data = get_data()
    if data.get("all"):
        db.execute("UPDATE notifications SET is_read = 1 WHERE user_id = ?", (g.user["id"],))
    elif data.get("id"):
        db.execute(
            "UPDATE notifications SET is_read = 1 WHERE id = ? AND user_id = ?",
            (data["id"], g.user["id"]),
        )
    db.commit()
    db.close()
    return jsonify({"ok": True})


# Отчёты репетиторов и подтверждение волонтёрских часов.
@app.route("/api/review-lessons", methods=["GET", "POST"])
@need_login
def review_lessons():
    if request.method == "POST":
        error = role_error("tutor")
        if error:
            return error
        data = get_data()
        video_link, error = video_link_from(data.get("videoLink"))
        if error:
            return jsonify({"error": error}), 400
    db = connect_db()
    if request.method == "GET":
        if g.user["role"] == "admin":
            rows = db.execute("SELECT * FROM review_lessons ORDER BY id DESC").fetchall()
        elif g.user["role"] == "tutor":
            rows = db.execute(
                "SELECT * FROM review_lessons WHERE tutor_id = ? ORDER BY id DESC", (g.user["id"],)
            ).fetchall()
        elif g.user["role"] == "mentor":
            rows = db.execute(
                """SELECT * FROM review_lessons WHERE tutor_id IN
                (SELECT tutor_id FROM tutor_mentors WHERE mentor_id = ?) ORDER BY id DESC""",
                (g.user["id"],),
            ).fetchall()
        else:
            rows = []
        db.close()
        return jsonify({"items": [row_to_dict(row) for row in rows]})
    row = db.execute(
        """INSERT INTO review_lessons
        (tutor, tutor_id, tutor_initials, student, lesson_date, duration, video, video_link, shots, status, topic)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, 'Ожидает проверки', ?) RETURNING *""",
        (
            full_name(g.user),
            g.user["id"],
            "".join([g.user["first_name"][0], g.user["last_name"][0]]),
            data.get("student", ""),
            data.get("date", ""),
            data.get("duration", "60 мин"),
            int(bool(data.get("video")) or bool(video_link)),
            video_link,
            int(bool(data.get("shots"))),
            data.get("topic", ""),
        ),
    ).fetchone()
    db.commit()
    db.close()
    return jsonify({"item": row_to_dict(row)}), 201


@app.patch("/api/review-lessons/<int:lesson_id>")
@need_login
def review_lesson_update(lesson_id):
    error = role_error("mentor", "admin")
    if error:
        return error
    data = get_data()
    db = connect_db()
    if g.user["role"] == "mentor":
        row = db.execute(
            """SELECT * FROM review_lessons WHERE id = ? AND tutor_id IN
            (SELECT tutor_id FROM tutor_mentors WHERE mentor_id = ?)""",
            (lesson_id, g.user["id"]),
        ).fetchone()
    else:
        row = db.execute("SELECT * FROM review_lessons WHERE id = ?", (lesson_id,)).fetchone()
    if not row:
        db.close()
        return jsonify({"error": "Отчёт не найден или недоступен"}), 404
    db.execute(
        "UPDATE review_lessons SET status = ? WHERE id = ?",
        (data.get("status", "Проверено"), lesson_id),
    )
    db.commit()
    row = db.execute("SELECT * FROM review_lessons WHERE id = ?", (lesson_id,)).fetchone()
    db.close()
    return jsonify({"item": row_to_dict(row)})


# Собранный Vue-интерфейс на том же адресе, что и API.
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
