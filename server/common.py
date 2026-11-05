"""Общие проверки доступа, сессии и преобразование данных."""

import json
import secrets
from datetime import datetime, timedelta, timezone
from flask import g, jsonify, request
from functools import wraps
from urllib.parse import urlsplit
from database import connect_db, is_production


COOKIE_NAME = "cogito_session"
MOSCOW_TIME = timezone(timedelta(hours=3))


def message_time(value):
    """Показывает время сообщения по Москве, независимо от часового пояса сервера."""
    try:
        moment = datetime.fromisoformat(value)
    except (TypeError, ValueError):
        return value
    return moment.astimezone(MOSCOW_TIME).strftime("%H:%M")


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


def row_to_dict(row):
    item = dict(row)
    for key in ["materials", "video", "shots", "is_read"]:
        if key in item:
            item[key] = bool(item[key])

    # Слева — имя поля в базе, справа — то же поле для страницы.
    field_names = {
        "lesson_date": "date",
        "lesson_time": "time",
        "created_time": "time",
        "sent_time": "time",
        "tutor_initials": "tutorInitials",
        "video_link": "videoLink",
        "submission_comment": "submissionComment",
        "submission_link": "submissionLink",
        "review_comment": "reviewComment",
        "is_read": "read",
    }
    for database_name, page_name in field_names.items():
        if database_name not in item:
            continue
        value = item.pop(database_name)
        if database_name in ["created_time", "sent_time"]:
            value = message_time(value)
        item[page_name] = value
    return item


def get_data():
    data = request.get_json(silent=True)
    return data if isinstance(data, dict) else {}


def text_field(data, key, limit=300):
    value = data.get(key, "")
    return value.strip()[:limit] if isinstance(value, str) else ""


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


def initials(user):
    return f"{user['first_name'][:1]}{user['last_name'][:1]}".upper()


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
        return (
            "tutor_id = ? AND student_id IN (SELECT student_id FROM student_tutors WHERE tutor_id = ?)",
            (user_id, user_id),
        )
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


def tutor_has_student(db, tutor_id, student_id):
    return bool(
        db.execute(
            "SELECT 1 FROM student_tutors WHERE tutor_id = ? AND student_id = ?",
            (tutor_id, student_id),
        ).fetchone()
    )


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
    if not isinstance(name, str):
        return None
    return db.execute(
        """SELECT * FROM users WHERE first_name || ' ' || last_name = ? AND role = ?
        AND account_status = 'active' AND email_verified_at IS NOT NULL""",
        (name.strip(), role),
    ).fetchone()


def user_by_id(db, user_id, role):
    return db.execute(
        """SELECT * FROM users WHERE id = ? AND role = ?
        AND account_status = 'active' AND email_verified_at IS NOT NULL""",
        (user_id, role),
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
