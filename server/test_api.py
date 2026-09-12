import os
from pathlib import Path
from tempfile import TemporaryDirectory

import database
from werkzeug.security import check_password_hash


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

    student = login(app, "anna@cogito.ru", "student")
    assert student.get("/api/auth/me").status_code == 200
    assert student.post("/api/lessons", json={}).status_code == 403
    assert len(student.get("/api/lessons").json["items"]) == 2
    assert student.post("/api/messages", json={"dialogId": 1, "text": "Проверка сообщения"}).status_code == 201
    assert student.get("/api/messages?dialog_id=999").status_code == 403

    tutor = login(app, "maria@cogito.ru", "tutor")
    lesson = tutor.post(
        "/api/lessons",
        json={
            "student": "Анна Смирнова",
            "tutor": "Мария Иванова",
            "subject": "Математика",
            "date": "5 августа",
            "time": "16:00–17:00",
            "duration": "60 мин",
            "topic": "Проверка API",
        },
    )
    assert lesson.status_code == 201

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
    pending = admin.get("/api/admin/users?status=pending")
    assert pending.status_code == 200
    pending_tutor = next(item for item in pending.json["items"] if item["email"] == "new.tutor@example.ru")
    assert admin.patch(f"/api/admin/users/{pending_tutor['id']}", json={"accountStatus": "active"}).status_code == 200
    assert login(app, "new.tutor@example.ru", "tutor", "long-enough-password").get("/api/auth/me").status_code == 200


saved_environment = {key: os.environ.get(key) for key in ["FLASK_ENV", "ADMIN_EMAIL", "ADMIN_BOOTSTRAP_PASSWORD", "DATABASE_URL"]}
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
