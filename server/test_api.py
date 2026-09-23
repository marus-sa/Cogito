import os
import sqlite3
from pathlib import Path
from tempfile import TemporaryDirectory

import database
from werkzeug.security import check_password_hash

os.environ["COGITO_DEMO_DATA"] = "1"


postgres_sessions_schema = next(
    statement for statement in database.POSTGRES_SCHEMA
    if "CREATE TABLE IF NOT EXISTS sessions" in statement
)
assert "created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP" in postgres_sessions_schema
assert "created_at TEXT DEFAULT CURRENT_TIMESTAMP" not in postgres_sessions_schema


def login(app, email, role, password="cogito123"):
    client = app.test_client()
    answer = client.post(
        "/api/auth/login",
        json={"email": email, "password": password, "role": role},
    )
    assert answer.status_code == 200
    assert "cogito_session=" in answer.headers["Set-Cookie"]
    assert "token" not in answer.json
    return client


with TemporaryDirectory() as folder:
    database.DATA_FOLDER = Path(folder)
    database.DATABASE_FILE = database.DATA_FOLDER / "test.db"
    database.start_database()

    from app import app

    guest = app.test_client()
    assert guest.get("/api/health").status_code == 200
    assert guest.get("/api/lessons").status_code == 401
    assert guest.get("/setup-admin").status_code == 200

    student = login(app, "student.demo@cogito.test", "student")
    assert student.get("/api/auth/me").status_code == 200
    assert student.post("/api/lessons", json={}).status_code == 403
    assert len(student.get("/api/lessons").json["items"]) == 2
    assert student.post("/api/messages", json={"dialogId": 1, "text": "Проверка сообщения"}).status_code == 201
    assert student.get("/api/messages?dialog_id=999").status_code == 403

    tutor = login(app, "maria@cogito.ru", "tutor")
    lesson = tutor.post(
        "/api/lessons",
        json={
            "student": "Тестовый Ученик",
            "tutor": "Мария Иванова",
            "subject": "Математика",
            "date": "5 августа",
            "time": "16:00–17:00",
            "duration": "60 мин",
            "topic": "Проверка API",
        },
    )
    assert lesson.status_code == 201

    review = tutor.post(
        "/api/review-lessons",
        json={
            "student": "Тестовый Ученик",
            "date": "5 августа, 16:00",
            "duration": "60 мин",
            "topic": "Проверка ссылки на запись",
            "videoLink": "https://drive.google.com/file/d/test-recording/view",
        },
    )
    assert review.status_code == 201
    assert review.json["item"]["video"] is True
    assert review.json["item"]["videoLink"] == "https://drive.google.com/file/d/test-recording/view"
    reports = tutor.get("/api/review-lessons")
    assert any(
        item["id"] == review.json["item"]["id"] and item["videoLink"] == review.json["item"]["videoLink"]
        for item in reports.json["items"]
    )
    bad_review = tutor.post("/api/review-lessons", json={"videoLink": "file:///private/video.mp4"})
    assert bad_review.status_code == 400

    mentor = login(app, "alexey@cogito.ru", "mentor")
    checked = mentor.patch("/api/review-lessons/1", json={"status": "Проверено"})
    assert checked.status_code == 200

    new_student = guest.post(
        "/api/auth/register",
        json={
            "firstName": "Новая",
            "lastName": "Ученица",
            "email": "new.student@example.ru",
            "password": "long-enough-password",
            "role": "student",
            "consent": True,
        },
    )
    assert new_student.status_code == 201
    assert new_student.json["needsApproval"] is False

    tutor_application = app.test_client().post(
        "/api/auth/register",
        json={
            "firstName": "Новый",
            "lastName": "Репетитор",
            "email": "new.tutor@example.ru",
            "password": "long-enough-password",
            "role": "tutor",
            "consent": True,
        },
    )
    assert tutor_application.status_code == 201
    assert tutor_application.json["needsApproval"] is True

    admin = login(app, "sofia@cogito.ru", "admin")
    dashboard = admin.get("/api/admin/dashboard")
    assert dashboard.status_code == 200
    assert dashboard.json["students"] >= 2
    assert dashboard.json["tutors"] >= 1
    assert isinstance(dashboard.json["subjects"], list)
    pending = admin.get("/api/admin/users?status=pending")
    assert pending.status_code == 200
    pending_tutor = next(item for item in pending.json["items"] if item["email"] == "new.tutor@example.ru")
    assert admin.patch(f"/api/admin/users/{pending_tutor['id']}", json={"accountStatus": "active"}).status_code == 200
    assert login(app, "new.tutor@example.ru", "tutor", "long-enough-password").get("/api/auth/me").status_code == 200
    assert any(item["title"] == "Новая заявка репетитора" for item in admin.get("/api/notifications").json["items"])

    new_student_client = login(app, "new.student@example.ru", "student", "long-enough-password")
    contacts = admin.get("/api/chat/contacts")
    assert contacts.status_code == 200
    assert any(item["id"] == new_student.json["user"]["id"] for item in contacts.json["items"])
    conversation = admin.post("/api/conversations", json={"recipientId": new_student.json["user"]["id"]})
    assert conversation.status_code == 201
    dialog_id = conversation.json["item"]["id"]
    student_dialogs = new_student_client.get("/api/conversations")
    assert any(item["id"] == dialog_id for item in student_dialogs.json["items"]), student_dialogs.json
    sent_message = new_student_client.post("/api/messages", json={"dialogId": dialog_id, "text": "Здравствуйте!"})
    assert sent_message.status_code == 201, sent_message.json
    incoming = admin.get(f"/api/messages?dialog_id={dialog_id}")
    assert incoming.status_code == 200
    assert incoming.json["items"][-1]["sender"] == "them"
    assert tutor.get(f"/api/messages?dialog_id={dialog_id}").status_code == 403


with TemporaryDirectory() as folder:
    os.environ.pop("COGITO_DEMO_DATA", None)
    database.DATA_FOLDER = Path(folder)
    database.DATABASE_FILE = database.DATA_FOLDER / "legacy-review-lessons.db"
    legacy = sqlite3.connect(database.DATABASE_FILE)
    legacy.execute(
        """CREATE TABLE review_lessons (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        tutor TEXT NOT NULL,
        tutor_id INTEGER,
        tutor_initials TEXT NOT NULL,
        student TEXT NOT NULL,
        lesson_date TEXT NOT NULL,
        duration TEXT NOT NULL,
        video INTEGER DEFAULT 0,
        shots INTEGER DEFAULT 0,
        status TEXT NOT NULL,
        topic TEXT NOT NULL
        )"""
    )
    legacy.execute(
        """INSERT INTO review_lessons
        (tutor, tutor_id, tutor_initials, student, lesson_date, duration, video, shots, status, topic)
        VALUES ('Старый репетитор', 1, 'СР', 'Старый ученик', '1 сентября', '60 мин', 0, 0, 'Проверено', 'Старая запись')"""
    )
    legacy.commit()
    legacy.close()

    database.start_database()
    db = database.connect_db()
    migrated = db.execute("SELECT video_link FROM review_lessons WHERE id = 1").fetchone()
    db.close()
    assert migrated["video_link"] is None


with TemporaryDirectory() as folder:
    os.environ.pop("COGITO_DEMO_DATA", None)
    database.DATA_FOLDER = Path(folder)
    database.DATABASE_FILE = database.DATA_FOLDER / "local-setup.db"
    database.start_database()
    local = app.test_client()
    local.post(
        "/api/auth/register",
        json={
            "firstName": "Обычный",
            "lastName": "Пользователь",
            "email": "local.user@example.test",
            "password": "safe-local-password",
            "role": "student",
            "consent": True,
        },
    )
    assert local.get("/api/setup/local-admin").json["available"] is True
    created = local.post(
        "/api/setup/local-admin",
        json={
            "firstName": "Локальный",
            "lastName": "Администратор",
            "email": "local.user@example.test",
            "password": "safe-local-password",
        },
    )
    assert created.status_code == 201
    assert created.json["user"]["role"] == "admin"
    assert local.get("/api/setup/local-admin").json["available"] is False


saved_environment = {key: os.environ.get(key) for key in ["FLASK_ENV", "ADMIN_EMAIL", "ADMIN_BOOTSTRAP_PASSWORD", "DATABASE_URL", "COGITO_DEMO_DATA"]}
try:
    os.environ["FLASK_ENV"] = "production"
    os.environ["ADMIN_EMAIL"] = "owner@example.ru"
    os.environ["ADMIN_BOOTSTRAP_PASSWORD"] = "a-strong-private-password"
    os.environ.pop("DATABASE_URL", None)

    with TemporaryDirectory() as folder:
        database.DATA_FOLDER = Path(folder)
        database.DATABASE_FILE = database.DATA_FOLDER / "production.db"
        database.start_database()
        db = database.connect_db()
        users = db.execute("SELECT email, password_hash, role FROM users").fetchall()
        db.close()

        assert len(users) == 1
        assert users[0]["email"] == "owner@example.ru"
        assert users[0]["role"] == "admin"
        assert check_password_hash(users[0]["password_hash"], "a-strong-private-password")
finally:
    for key, value in saved_environment.items():
        if value is None:
            os.environ.pop(key, None)
        else:
            os.environ[key] = value

print("API работает: сессии в защищённых cookie, роли, заявки и разделение данных.")
