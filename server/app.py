import json
import os
import re
import secrets
from datetime import datetime, timedelta, timezone
from functools import wraps
from pathlib import Path
from urllib.parse import urlsplit

from flask import Flask, abort, g, jsonify, request, send_from_directory
from werkzeug.security import check_password_hash, generate_password_hash

from database import connect_db, is_production, start_database


PROJECT_FOLDER = Path(__file__).resolve().parent.parent
FRONTEND_FOLDER = PROJECT_FOLDER / "dist"
COOKIE_NAME = "cogito_session"
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
    if "is_read" in item:
        item["read"] = item.pop("is_read")
    return item


def goal_to_dict(row):
    item = dict(row)
    item["tasks"] = json.loads(item["tasks"])
    return item


def get_data():
    return request.get_json(silent=True) or {}


def video_link_from(value):
    """Проверяет необязательную ссылку на запись занятия.

    Разрешаем обычные HTTP(S)-ссылки, включая Google Drive и Яндекс Диск.
    Это исключает javascript:, data: и file: ссылки, которые нельзя безопасно
    показывать в интерфейсе.
    """
    if value is None or value == "":
        return None, None
    if not isinstance(value, str):
        return None, "Ссылка на видео должна быть текстом."

    link = value.strip()
    if not link:
        return None, None
    if len(link) > 2048 or any(char.isspace() for char in link):
        return None, "Укажите корректную ссылку на видео (http:// или https://)."

    try:
        parsed = urlsplit(link)
    except ValueError:
        return None, "Укажите корректную ссылку на видео (http:// или https://)."

    if parsed.scheme.lower() not in {"http", "https"} or not parsed.hostname or parsed.username or parsed.password:
        return None, "Укажите корректную ссылку на видео (http:// или https://)."
    return link, None


def get_user_from_token():
    header = request.headers.get("Authorization", "")
    token = header.replace("Bearer ", "") or request.cookies.get(COOKIE_NAME, "")
    if not token:
        return None
    db = connect_db()
    user = db.execute(
        """SELECT users.* FROM sessions
        JOIN users ON users.id = sessions.user_id
        WHERE sessions.token = ? AND sessions.expires_at > ? AND users.account_status = 'active'""",
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
        return "student_id IN (SELECT student_id FROM parent_students WHERE parent_id = ?)", (user_id,)
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
    return db.execute(f"SELECT * FROM {table} WHERE id = ? AND {where}", (item_id, *params)).fetchone()


def student_by_name(db, name):
    return user_by_name(db, name, "student")


def user_by_name(db, name, role):
    return db.execute(
        "SELECT * FROM users WHERE first_name || ' ' || last_name = ? AND role = ? AND account_status = 'active'",
        (name.strip(), role),
    ).fetchone()


def create_session(user_id, days=30):
    token = secrets.token_urlsafe(32)
    db = connect_db()
    expires_at = (datetime.now(timezone.utc) + timedelta(days=days)).isoformat()
    db.execute("DELETE FROM sessions WHERE expires_at <= ?", (datetime.now(timezone.utc).isoformat(),))
    db.execute("INSERT INTO sessions (token, user_id, expires_at) VALUES (?, ?, ?)", (token, user_id, expires_at))
    db.commit()
    db.close()
    return token


def set_session_cookie(response, token, days=30):
    response.set_cookie(
        COOKIE_NAME,
        token,
        max_age=60 * 60 * 24 * days,
        httponly=True,
        secure=os.environ.get("FLASK_ENV") == "production",
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
    user.pop("password_hash", None)
    return user


def local_admin_setup_allowed():
    """Первого администратора локально создаёт только владелец компьютера.

    На опубликованном сайте этот маршрут недоступен: там первого администратора
    создают переменные ADMIN_EMAIL и ADMIN_BOOTSTRAP_PASSWORD. Локально доступ
    закрывается сразу после создания первого админа.
    """
    return not is_production() and request.remote_addr in {"127.0.0.1", "::1"}


@app.get("/api/health")
def health():
    return jsonify({"ok": True})


@app.after_request
def add_security_headers(response):
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
        return jsonify({"error": "Пароль администратора должен содержать не менее 12 символов"}), 400

    existing_user = db.execute("SELECT * FROM users WHERE email = ?", (email,)).fetchone()
    try:
        if existing_user:
            # У пользователя уже есть локальный аккаунт: сохраняем его записи,
            # но назначаем владельцем проекта по его явному действию в этой форме.
            db.execute(
                """UPDATE users SET first_name = ?, last_name = ?, password_hash = ?, role = 'admin',
                account_status = 'active', subjects = 'Управление проектом' WHERE id = ?""",
                (first_name, last_name, generate_password_hash(password), existing_user["id"]),
            )
        else:
            db.execute(
                """INSERT INTO users
                (first_name, last_name, email, password_hash, role, account_status, grade, subjects, available_time, child_name, bio)
                VALUES (?, ?, ?, ?, 'admin', 'active', '', 'Управление проектом', '', '', '')""",
                (first_name, last_name, email, generate_password_hash(password)),
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


@app.post("/api/auth/login")
def login():
    data = get_data()
    email = data.get("email", "").strip().lower()
    password = data.get("password", "")
    role = data.get("role", "")
    db = connect_db()
    user = db.execute("SELECT * FROM users WHERE email = ?", (email,)).fetchone()
    db.close()
    if not user or not check_password_hash(user["password_hash"], password):
        return jsonify({"error": "Неверная почта или пароль"}), 400
    if role and user["role"] != role:
        return jsonify({"error": "Выберите роль, которая указана у этого аккаунта"}), 400
    if user["account_status"] == "pending":
        return jsonify({"error": "Заявка ещё ожидает подтверждения администратора"}), 403
    if user["account_status"] != "active":
        return jsonify({"error": "Этот аккаунт сейчас недоступен"}), 403

    days = 30 if data.get("remember", True) else 1
    response = jsonify({"user": user_for_frontend(user)})
    return set_session_cookie(response, create_session(user["id"], days), days)


@app.post("/api/auth/register")
def register():
    data = get_data()
    required = ["firstName", "lastName", "email", "password", "role"]
    if any(not data.get(field, "").strip() for field in required):
        return jsonify({"error": "Заполните обязательные поля"}), 400
    if len(data["password"]) < 6:
        return jsonify({"error": "Пароль должен содержать не менее 6 символов"}), 400
    if not re.match(r"^\S+@\S+\.\S+$", data["email"]):
        return jsonify({"error": "Проверьте формат электронной почты"}), 400
    if data["role"] not in PUBLIC_REGISTER_ROLES:
        return jsonify({"error": "Наставника и администратора добавляет глава проекта по приглашению"}), 403
    if not data.get("consent"):
        return jsonify({"error": "Нужно согласие на обработку персональных данных"}), 400

    account_status = "pending" if data["role"] == "tutor" else "active"
    db = connect_db()
    try:
        db.execute(
            """INSERT INTO users
            (first_name, last_name, email, password_hash, role, account_status, grade, subjects, available_time, child_name, bio)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                data["firstName"].strip(), data["lastName"].strip(), data["email"].strip().lower(),
                generate_password_hash(data["password"]), data["role"], account_status, data.get("grade", ""),
                data.get("subjects", data.get("subject", "")), data.get("time", ""), data.get("child", ""), data.get("about", ""),
            ),
        )
        db.commit()
    except Exception:
        db.close()
        return jsonify({"error": "Эта электронная почта уже зарегистрирована"}), 400
    user = db.execute("SELECT * FROM users WHERE email = ?", (data["email"].strip().lower(),)).fetchone()
    if account_status == "pending":
        admin_rows = db.execute("SELECT id FROM users WHERE role = 'admin' AND account_status = 'active'").fetchall()
        for admin in admin_rows:
            db.execute(
                """INSERT INTO notifications (user_id, icon, tone, title, text, created_time, is_read)
                VALUES (?, ?, ?, ?, ?, ?, ?)""",
                (
                    admin["id"],
                    "UsersRound",
                    "warning",
                    "Новая заявка репетитора",
                    f"{full_name(user)} ждёт подтверждения аккаунта.",
                    "Только что",
                    0,
                ),
            )
        db.commit()
    db.close()
    if account_status == "pending":
        return jsonify({"user": user_for_frontend(user), "needsApproval": True}), 201

    response = jsonify({"user": user_for_frontend(user), "needsApproval": False})
    set_session_cookie(response, create_session(user["id"]))
    return response, 201


@app.get("/api/auth/me")
@need_login
def current_user():
    return jsonify({"user": user_for_frontend(g.user)})


@app.post("/api/auth/logout")
@need_login
def logout():
    token = request.headers.get("Authorization", "").replace("Bearer ", "") or request.cookies.get(COOKIE_NAME, "")
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
    name = data.get("name", "").strip().split(" ", 1)
    first_name = data.get("firstName", name[0] if name else g.user["first_name"])
    last_name = data.get("lastName", name[1] if len(name) > 1 else g.user["last_name"])
    db = connect_db()
    db.execute(
        """UPDATE users SET first_name = ?, last_name = ?, email = ?, grade = ?, subjects = ?,
        available_time = ?, child_name = ?, bio = ? WHERE id = ?""",
        (first_name, last_name, data.get("email", g.user["email"]), data.get("grade", g.user["grade"]),
         data.get("subjects", g.user["subjects"]), data.get("time", g.user["available_time"]),
         data.get("childName", g.user["child_name"]), data.get("bio", g.user["bio"]), g.user["id"]),
    )
    db.commit()
    user = db.execute("SELECT * FROM users WHERE id = ?", (g.user["id"],)).fetchone()
    db.close()
    return jsonify({"user": user_for_frontend(user)})


@app.get("/api/admin/users")
@need_login
def admin_users():
    error = role_error("admin")
    if error:
        return error
    status = request.args.get("status", "")
    db = connect_db()
    if status:
        rows = db.execute("SELECT * FROM users WHERE account_status = ? ORDER BY id DESC", (status,)).fetchall()
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
    if new_status not in allowed_statuses:
        return jsonify({"error": "Укажите корректный статус аккаунта"}), 400
    if user_id == g.user["id"] and new_status != "active":
        return jsonify({"error": "Нельзя заблокировать собственный аккаунт"}), 400
    db = connect_db()
    db.execute("UPDATE users SET account_status = ? WHERE id = ?", (new_status, user_id))
    db.commit()
    user = db.execute("SELECT * FROM users WHERE id = ?", (user_id,)).fetchone()
    db.close()
    if not user:
        return jsonify({"error": "Пользователь не найден"}), 404
    return jsonify({"user": user_for_frontend(user)})


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
    tutor = g.user if g.user["role"] == "tutor" else user_by_name(db, data.get("tutor", ""), "tutor")
    if not student or not tutor:
        db.close()
        return jsonify({"error": "Выберите зарегистрированных ученика и репетитора"}), 400
    db.execute(
        """INSERT INTO lessons
        (student, tutor, student_id, tutor_id, subject, lesson_date, lesson_time, duration, status, link, topic, materials)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, 'Запланировано', ?, ?, 0)""",
        (full_name(student), full_name(tutor), student["id"], tutor["id"], data.get("subject", ""), data.get("date", ""), data.get("time", ""), data.get("duration", "60 мин"), data.get("link", ""), data.get("topic", "")),
    )
    db.commit()
    row = db.execute("SELECT * FROM lessons ORDER BY id DESC LIMIT 1").fetchone()
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
    db.execute("UPDATE lessons SET status = ? WHERE id = ?", (data.get("status", "Запланировано"), lesson_id))
    db.commit()
    row = db.execute("SELECT * FROM lessons WHERE id = ?", (lesson_id,)).fetchone()
    db.close()
    return jsonify({"item": row_to_dict(row)})


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
    tutor = g.user if g.user["role"] == "tutor" else user_by_name(db, data.get("tutor", ""), "tutor")
    if not student or not tutor:
        db.close()
        return jsonify({"error": "Выберите зарегистрированных ученика и репетитора"}), 400
    db.execute(
        """INSERT INTO homework
        (title, subject, student, tutor, student_id, tutor_id, issued, deadline, status, attachment, score, description)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, 'Новые', '', NULL, ?)""",
        (data.get("title", ""), data.get("subject", ""), full_name(student), full_name(tutor), student["id"], tutor["id"], "Сегодня", data.get("deadline", ""), data.get("description", "")),
    )
    db.commit()
    row = db.execute("SELECT * FROM homework ORDER BY id DESC LIMIT 1").fetchone()
    db.close()
    return jsonify({"item": row_to_dict(row)}), 201


@app.patch("/api/homework/<int:homework_id>/submit")
@need_login
def submit_homework(homework_id):
    error = role_error("student", "parent")
    if error:
        return error
    db = connect_db()
    row = scoped_item(db, "homework", homework_id)
    if not row:
        db.close()
        return jsonify({"error": "Задание не найдено или недоступно"}), 404
    db.execute("UPDATE homework SET status = 'Сданы' WHERE id = ?", (homework_id,))
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
    db = connect_db()
    row = scoped_item(db, "homework", homework_id)
    if not row:
        db.close()
        return jsonify({"error": "Задание не найдено или недоступно"}), 404
    db.execute("UPDATE homework SET status = 'Проверено', score = ? WHERE id = ?", (data.get("score", ""), homework_id))
    db.commit()
    row = db.execute("SELECT * FROM homework WHERE id = ?", (homework_id,)).fetchone()
    db.close()
    return jsonify({"item": row_to_dict(row)})


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
    db.execute(
        """INSERT INTO goals (title, subject, deadline, tutor, student_id, tutor_id, description, tasks)
        VALUES (?, ?, ?, ?, ?, NULL, ?, ?)""",
        (data.get("title", ""), data.get("subject", ""), data.get("deadline", ""), "Не назначен", g.user["id"], data.get("description", ""), json.dumps(data.get("tasks", []), ensure_ascii=False)),
    )
    db.commit()
    row = db.execute("SELECT * FROM goals ORDER BY id DESC LIMIT 1").fetchone()
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
    db.execute("UPDATE goals SET tasks = ? WHERE id = ?", (json.dumps(tasks, ensure_ascii=False), goal_id))
    db.commit()
    updated = db.execute("SELECT * FROM goals WHERE id = ?", (goal_id,)).fetchone()
    db.close()
    return jsonify({"item": goal_to_dict(updated)})


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
        conversation = db.execute("SELECT * FROM conversations WHERE id = ?", (existing["conversation_id"],)).fetchone()
        item = conversation_to_dict(db, conversation, g.user["id"])
        db.close()
        return jsonify({"item": item, "created": False})

    recipient = db.execute("SELECT * FROM users WHERE id = ?", (recipient_id,)).fetchone()
    db.execute("INSERT INTO conversations (title) VALUES (?)", (full_name(recipient),))
    conversation = db.execute("SELECT * FROM conversations ORDER BY id DESC LIMIT 1").fetchone()
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
    dialog_id = request.args.get("dialog_id", type=int) if request.method == "GET" else get_data().get("dialogId")
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
        rows = db.execute("SELECT * FROM messages WHERE dialog_id = ? ORDER BY id", (dialog_id,)).fetchall()
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
    db.execute(
        "INSERT INTO messages (dialog_id, sender, sender_id, text, sent_time, is_read) VALUES (?, 'me', ?, ?, ?, 0)",
        (dialog_id, g.user["id"], text, now),
    )
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
    row = db.execute("SELECT * FROM messages ORDER BY id DESC LIMIT 1").fetchone()
    db.close()
    item = row_to_dict(row)
    item["sender"] = "me"
    return jsonify({"item": item}), 201


@app.route("/api/notifications", methods=["GET", "PATCH"])
@need_login
def notifications():
    db = connect_db()
    if request.method == "GET":
        rows = db.execute("SELECT * FROM notifications WHERE user_id = ? ORDER BY id DESC", (g.user["id"],)).fetchall()
        db.close()
        return jsonify({"items": [row_to_dict(row) for row in rows]})
    data = get_data()
    if data.get("all"):
        db.execute("UPDATE notifications SET is_read = 1 WHERE user_id = ?", (g.user["id"],))
    elif data.get("id"):
        db.execute("UPDATE notifications SET is_read = 1 WHERE id = ? AND user_id = ?", (data["id"], g.user["id"]))
    db.commit()
    db.close()
    return jsonify({"ok": True})


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
            rows = db.execute("SELECT * FROM review_lessons WHERE tutor_id = ? ORDER BY id DESC", (g.user["id"],)).fetchall()
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
    db.execute(
        """INSERT INTO review_lessons
        (tutor, tutor_id, tutor_initials, student, lesson_date, duration, video, video_link, shots, status, topic)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, 'Ожидает проверки', ?)""",
        (full_name(g.user), g.user["id"], "".join([g.user["first_name"][0], g.user["last_name"][0]]), data.get("student", ""), data.get("date", ""), data.get("duration", "60 мин"), int(bool(data.get("video")) or bool(video_link)), video_link, int(bool(data.get("shots"))), data.get("topic", "")),
    )
    db.commit()
    row = db.execute("SELECT * FROM review_lessons ORDER BY id DESC LIMIT 1").fetchone()
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
    db.execute("UPDATE review_lessons SET status = ? WHERE id = ?", (data.get("status", "Проверено"), lesson_id))
    db.commit()
    row = db.execute("SELECT * FROM review_lessons WHERE id = ?", (lesson_id,)).fetchone()
    db.close()
    return jsonify({"item": row_to_dict(row)})


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
    app.run(host=os.environ.get("HOST", "0.0.0.0"), port=int(os.environ.get("PORT", "5000")), debug=False)
