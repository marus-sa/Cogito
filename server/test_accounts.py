"""Проверка аккаунтов на временной базе. Реальные пользователи не меняются."""

import os
import unittest
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch

import database

# Импорт app тоже запускает подготовку базы, поэтому сначала задаём временный путь.
for key in [
    "DATABASE_URL",
    "FLASK_ENV",
    "ADMIN_EMAIL",
    "ADMIN_BOOTSTRAP_PASSWORD",
    "SMTP_HOST",
    "SMTP_PASSWORD",
]:
    os.environ.pop(key, None)
os.environ["COGITO_DEMO_DATA"] = "1"
test_folder = TemporaryDirectory()
database.DATA_FOLDER = Path(test_folder.name)
database.DATABASE_FILE = database.DATA_FOLDER / "initial.db"
import app as app_module
import accounts

app = app_module.app
app.config["TESTING"] = True
ACCOUNTS = {
    "student": "student.demo@cogito.test",
    "tutor": "maria@cogito.ru",
    "parent": "elena@cogito.ru",
    "mentor": "alexey@cogito.ru",
    "admin": "sofia@cogito.ru",
}


def sign_in(role, remember=True):
    client = app.test_client()
    answer = client.post(
        "/api/auth/login",
        json={
            "email": f"  {ACCOUNTS[role].upper()}  ",
            "password": "cogito123",
            "remember": remember,
            # Старая версия клиента может прислать роль, но она не меняет права.
            "role": "admin",
        },
    )
    assert answer.status_code == 200, answer.json
    assert answer.json["user"]["role"] == role
    return client, answer


def new_student():
    client = app.test_client()
    with patch.object(accounts, "send_verification_email", return_value="sent") as send:
        registered = client.post(
            "/api/auth/register",
            json={
                "firstName": "Новый",
                "lastName": "Ученик",
                "email": "new.student@example.test",
                "password": "safe-test-password",
                "role": "student",
                "consent": True,
            },
        )
        assert registered.status_code == 201, registered.json
        token = send.call_args.args[1]
    confirmed = client.post("/api/auth/verify-email", json={"token": token})
    assert confirmed.status_code == 200, confirmed.json
    return client, confirmed.json["user"]


class AccountTests(unittest.TestCase):
    def setUp(self):
        database.DATABASE_FILE = database.DATA_FOLDER / f"{self._testMethodName}.db"
        database.start_database()

    def test_all_roles_on_two_devices(self):
        for role in ACCOUNTS:
            with self.subTest(role=role):
                first, answer = sign_in(role)
                second, _ = sign_in(role)
                self.assertNotEqual(
                    first.get_cookie("cogito_session").value,
                    second.get_cookie("cogito_session").value,
                )
                self.assertIn("HttpOnly", answer.headers["Set-Cookie"])
                self.assertIn("SameSite=Lax", answer.headers["Set-Cookie"])
                self.assertNotIn("password_hash", answer.json["user"])
                self.assertNotIn("token", answer.json)
                for client in [first, second]:
                    me = client.get("/api/auth/me")
                    self.assertEqual(me.status_code, 200)
                    self.assertEqual(me.headers["Cache-Control"], "no-store")
                    for path in [
                        "/profile",
                        "/lessons",
                        "/homework",
                        "/goals",
                        "/conversations",
                        "/chat/contacts",
                    ]:
                        self.assertEqual(client.get(f"/api{path}").status_code, 200, path)
                    for path in ["/admin/users", "/admin/dashboard", "/admin/relationships"]:
                        self.assertEqual(
                            client.get(f"/api{path}").status_code, 200 if role == "admin" else 403
                        )
                # Данные общие, cookie независимые. Перезапуск не удаляет сессии.
                first.put(
                    "/api/profile", json={"bio": "Изменено на первом устройстве", "role": "admin"}
                )
                database.start_database()
                me = second.get("/api/auth/me").json["user"]
                self.assertEqual(me["bio"], "Изменено на первом устройстве")
                self.assertEqual(me["role"], role)
                self.assertEqual(first.post("/api/auth/logout").status_code, 200)
                self.assertEqual(first.get("/api/auth/me").status_code, 401)
                self.assertEqual(second.get("/api/auth/me").status_code, 200)

    def test_remember_and_expiry(self):
        short, answer = sign_in("student", remember=False)
        self.assertNotIn("Max-Age", answer.headers["Set-Cookie"])
        self.assertNotIn("Expires", answer.headers["Set-Cookie"])
        long, answer = sign_in("student")
        self.assertIn("Max-Age=2592000", answer.headers["Set-Cookie"])
        db = database.connect_db()
        db.execute(
            "UPDATE sessions SET expires_at = ? WHERE token = ?",
            ("2000-01-01T00:00:00+00:00", short.get_cookie("cogito_session").value),
        )
        db.commit()
        db.close()
        self.assertEqual(short.get("/api/auth/me").status_code, 401)
        self.assertEqual(short.post("/api/auth/logout").status_code, 200)
        self.assertEqual(long.get("/api/auth/me").status_code, 200)

    def test_blocking_revokes_all_sessions(self):
        admin, _ = sign_in("admin")
        first, answer = sign_in("tutor")
        second, _ = sign_in("tutor")
        user_id = answer.json["user"]["id"]
        self.assertEqual(
            admin.patch(
                f"/api/admin/users/{user_id}", json={"accountStatus": "blocked"}
            ).status_code,
            200,
        )
        self.assertEqual(first.get("/api/auth/me").status_code, 401)
        self.assertEqual(second.get("/api/auth/me").status_code, 401)
        self.assertEqual(
            admin.patch(
                f"/api/admin/users/{user_id}", json={"accountStatus": "active"}
            ).status_code,
            200,
        )
        self.assertEqual(first.get("/api/auth/me").status_code, 401)
        self.assertEqual(second.get("/api/auth/me").status_code, 401)
        sign_in("tutor")

    def test_admin_assigns_mentor_role(self):
        admin, _ = sign_in("admin")
        student, answer = sign_in("student")
        user_id = answer.json["user"]["id"]
        self.assertEqual(
            student.patch(f"/api/admin/users/{user_id}", json={"role": "admin"}).status_code, 403
        )
        changed = admin.patch(f"/api/admin/users/{user_id}", json={"role": "mentor"})
        self.assertEqual(changed.status_code, 200)
        self.assertEqual(student.get("/api/auth/me").status_code, 401)
        again = app.test_client().post(
            "/api/auth/login",
            json={"email": ACCOUNTS["student"], "password": "cogito123", "role": "student"},
        )
        self.assertEqual(again.json["user"]["role"], "mentor")
        self.assertEqual(admin.get("/api/admin/relationships").json["parents"], [])
        own_id = admin.get("/api/auth/me").json["user"]["id"]
        self.assertEqual(
            admin.patch(f"/api/admin/users/{own_id}", json={"role": "student"}).status_code, 400
        )
        self.assertEqual(
            admin.patch(
                f"/api/admin/users/{own_id}", json={"accountStatus": "blocked"}
            ).status_code,
            400,
        )

    def test_relationships_control_data_access(self):
        admin, _ = sign_in("admin")
        parent, parent_answer = sign_in("parent")
        student, student_answer = sign_in("student")
        mentor, mentor_answer = sign_in("mentor")
        tutor, tutor_answer = sign_in("tutor")
        pairs = [
            (
                {
                    "kind": "parent_student",
                    "firstId": parent_answer.json["user"]["id"],
                    "secondId": student_answer.json["user"]["id"],
                },
                parent,
                "/api/lessons",
            ),
            (
                {
                    "kind": "mentor_tutor",
                    "firstId": mentor_answer.json["user"]["id"],
                    "secondId": tutor_answer.json["user"]["id"],
                },
                mentor,
                "/api/review-lessons",
            ),
        ]
        for payload, client, path in pairs:
            self.assertGreater(len(client.get(path).json["items"]), 0)
            self.assertEqual(client.post("/api/admin/relationships", json=payload).status_code, 403)
            self.assertEqual(
                admin.delete("/api/admin/relationships", json=payload).status_code, 200
            )
            self.assertEqual(client.get(path).json["items"], [])
            self.assertEqual(admin.post("/api/admin/relationships", json=payload).status_code, 201)
            self.assertEqual(admin.post("/api/admin/relationships", json=payload).status_code, 201)
            self.assertGreater(len(client.get(path).json["items"]), 0)
        wrong_roles = {
            "kind": "parent_student",
            "firstId": tutor_answer.json["user"]["id"],
            "secondId": student_answer.json["user"]["id"],
        }
        self.assertEqual(admin.post("/api/admin/relationships", json=wrong_roles).status_code, 400)

    def test_registration_confirmation_on_another_device(self):
        first, second = app.test_client(), app.test_client()
        with patch.object(accounts, "send_verification_email", return_value="sent") as send:
            answer = first.post(
                "/api/auth/register",
                json={
                    "firstName": "Новый",
                    "lastName": "Родитель",
                    "email": "  NEW.PARENT@example.test  ",
                    "password": "safe-test-password",
                    "role": "parent",
                    "consent": True,
                },
            )
            self.assertEqual(answer.status_code, 201)
            token = send.call_args.args[1]
        self.assertEqual(
            first.post(
                "/api/auth/login",
                json={"email": "new.parent@example.test", "password": "safe-test-password"},
            ).status_code,
            403,
        )
        verified = second.post("/api/auth/verify-email", json={"token": token})
        self.assertEqual(verified.status_code, 200)
        self.assertEqual(verified.json["user"]["role"], "parent")
        self.assertEqual(second.get("/api/lessons").json["items"], [])
        self.assertEqual(
            first.post(
                "/api/auth/login",
                json={"email": "new.parent@example.test", "password": "safe-test-password"},
            ).status_code,
            200,
        )
        self.assertEqual(
            first.post("/api/auth/verify-email", json={"token": token}).status_code, 400
        )

    def test_student_tutor_link_before_first_lesson(self):
        admin, _ = sign_in("admin")
        tutor, tutor_answer = sign_in("tutor")
        student, person = new_student()
        tutor_id = tutor_answer.json["user"]["id"]
        payload = {"kind": "student_tutor", "firstId": person["id"], "secondId": tutor_id}
        lesson = {
            "student": person["name"], "subject": "Математика",
            "date": "2026-11-04", "time": "16:00",
        }

        def contacts(client):
            return {item["id"] for item in client.get("/api/chat/contacts").json["items"]}

        self.assertNotIn(tutor_id, contacts(student))
        self.assertNotIn(person["id"], contacts(tutor))
        self.assertEqual(
            student.post("/api/conversations", json={"recipientId": tutor_id}).status_code, 403
        )
        for endpoint in ["/api/lessons", "/api/homework"]:
            self.assertEqual(tutor.post(endpoint, json=lesson).status_code, 403)
        for role in ["student", "tutor", "parent", "mentor"]:
            other, _ = sign_in(role)
            self.assertEqual(
                other.post("/api/admin/relationships", json=payload).status_code, 403
            )
            self.assertEqual(
                other.delete("/api/admin/relationships", json=payload).status_code, 403
            )

        self.assertEqual(admin.post("/api/admin/relationships", json=payload).status_code, 201)
        self.assertEqual(admin.post("/api/admin/relationships", json=payload).status_code, 201)
        links = admin.get("/api/admin/relationships").json["students"]
        self.assertEqual(sum(link["student_id"] == person["id"] for link in links), 1)
        database.start_database()
        self.assertIn(tutor_id, contacts(student))
        self.assertIn(person["id"], contacts(tutor))
        dialog = student.post("/api/conversations", json={"recipientId": tutor_id})
        self.assertEqual(dialog.status_code, 201)
        dialog_id = dialog.json["item"]["id"]
        sent = student.post(
            "/api/messages", json={"dialogId": dialog_id, "text": "Здравствуйте!"}
        )
        self.assertEqual(sent.status_code, 201)
        received = tutor.get(f"/api/messages?dialog_id={dialog_id}").json["items"]
        self.assertEqual(received[0]["text"], "Здравствуйте!")
        for endpoint in ["/api/lessons", "/api/homework"]:
            self.assertEqual(tutor.post(endpoint, json=lesson).status_code, 201)
            self.assertEqual(len(student.get(endpoint).json["items"]), 1)
        unrelated, _ = sign_in("student")
        unrelated_lessons = unrelated.get("/api/lessons").json["items"]
        self.assertNotIn(person["id"], {row["student_id"] for row in unrelated_lessons})

        self.assertEqual(admin.delete("/api/admin/relationships", json=payload).status_code, 200)
        database.start_database()
        self.assertNotIn(tutor_id, contacts(student))
        self.assertNotIn(person["id"], contacts(tutor))
        self.assertEqual(
            student.post("/api/conversations", json={"recipientId": tutor_id}).status_code, 403
        )
        for endpoint in ["/api/lessons", "/api/homework"]:
            self.assertEqual(tutor.post(endpoint, json=lesson).status_code, 403)
            rows = tutor.get(endpoint).json["items"]
            self.assertNotIn(person["id"], {row["student_id"] for row in rows})
            self.assertEqual(len(student.get(endpoint).json["items"]), 1)

    def test_student_tutor_link_requires_verified_active_roles(self):
        admin, _ = sign_in("admin")
        tutor, tutor_answer = sign_in("tutor")
        _, person = new_student()
        tutor_id = tutor_answer.json["user"]["id"]
        payload = {"kind": "student_tutor", "firstId": person["id"], "secondId": tutor_id}
        wrong = {**payload, "firstId": tutor_id, "secondId": person["id"]}
        self.assertEqual(admin.post("/api/admin/relationships", json=wrong).status_code, 400)
        self.assertEqual(
            admin.post("/api/admin/relationships", json={**payload, "secondId": 9999}).status_code,
            400,
        )
        for status in ["pending", "blocked"]:
            admin.patch(f'/api/admin/users/{person["id"]}', json={"accountStatus": status})
            self.assertEqual(
                admin.post("/api/admin/relationships", json=payload).status_code, 400
            )
        admin.patch(f'/api/admin/users/{person["id"]}', json={"accountStatus": "active"})
        db = database.connect_db()
        db.execute("UPDATE users SET email_verified_at = NULL WHERE id = ?", (person["id"],))
        db.commit()
        self.assertEqual(admin.post("/api/admin/relationships", json=payload).status_code, 400)
        db.execute(
            "UPDATE users SET email_verified_at = ? WHERE id = ?",
            ("2026-11-04T00:00:00+00:00", person["id"]),
        )
        db.commit()
        db.close()
        self.assertEqual(admin.post("/api/admin/relationships", json=payload).status_code, 201)
        changed = admin.patch(f'/api/admin/users/{person["id"]}', json={"role": "parent"})
        self.assertEqual(changed.status_code, 200)
        contacts = tutor.get("/api/chat/contacts").json["items"]
        self.assertNotIn(person["id"], {item["id"] for item in contacts})
        links = admin.get("/api/admin/relationships").json["students"]
        self.assertFalse(any(link["student_id"] == person["id"] for link in links))

    def test_existing_student_tutor_links_migrate_only_once(self):
        db = database.connect_db()
        expected = [dict(row) for row in db.execute("SELECT * FROM student_tutors").fetchall()]
        db.execute("DELETE FROM student_tutors")
        db.execute("DELETE FROM app_migrations WHERE migration_key = 'student-tutors-v1'")
        db.commit()
        db.close()
        database.start_database()
        db = database.connect_db()
        actual = [dict(row) for row in db.execute("SELECT * FROM student_tutors").fetchall()]
        self.assertEqual(actual, expected)
        db.execute("DELETE FROM student_tutors")
        db.commit()
        db.close()
        database.start_database()
        db = database.connect_db()
        count = db.execute("SELECT COUNT(*) AS count FROM student_tutors").fetchone()["count"]
        self.assertEqual(count, 0)
        db.close()

    def test_invalid_input_is_not_a_server_error(self):
        guest = app.test_client()
        for payload in [
            [],
            {"email": []},
            {"email": "x@y.ru", "password": {}},
            {"email": "x@y.ru", "password": "x" * 513},
        ]:
            self.assertEqual(guest.post("/api/auth/login", json=payload).status_code, 400)
        for role in ["admin", "mentor"]:
            answer = guest.post(
                "/api/auth/register",
                json={
                    "firstName": "Имя",
                    "lastName": "Фамилия",
                    "email": "x@y.ru",
                    "password": "safe-password",
                    "role": role,
                    "consent": True,
                },
            )
            self.assertEqual(answer.status_code, 403)
        self.assertEqual(guest.post("/api/auth/register", json={"firstName": []}).status_code, 400)

    def test_production_cookie(self):
        with patch.dict(os.environ, {"FLASK_ENV": "production"}):
            answer = app.test_client().post(
                "/api/auth/login",
                base_url="https://cogito.test",
                json={"email": ACCOUNTS["admin"], "password": "cogito123"},
            )
        self.assertEqual(answer.status_code, 200)
        self.assertIn("Secure", answer.headers["Set-Cookie"])

    def test_simultaneous_requests_return_their_own_record(self):
        def create_lesson(number):
            client, _ = sign_in("tutor")
            topic = f"Параллельный запрос {number}"
            answer = client.post(
                "/api/lessons",
                json={"student": "Тестовый Ученик", "subject": "Математика", "topic": topic},
            )
            self.assertEqual(answer.status_code, 201)
            self.assertEqual(answer.json["item"]["topic"], topic)
            return answer.json["item"]["id"]

        with ThreadPoolExecutor(max_workers=4) as workers:
            ids = list(workers.map(create_lesson, range(8)))
        self.assertEqual(len(set(ids)), 8)

    def test_mentor_cannot_create_for_unassigned_tutor(self):
        admin, _ = sign_in("admin")
        mentor, mentor_answer = sign_in("mentor")
        _, tutor_answer = sign_in("tutor")
        payload = {
            "kind": "mentor_tutor",
            "firstId": mentor_answer.json["user"]["id"],
            "secondId": tutor_answer.json["user"]["id"],
        }
        self.assertEqual(admin.delete("/api/admin/relationships", json=payload).status_code, 200)
        for path in ["/api/lessons", "/api/homework"]:
            self.assertEqual(
                mentor.post(
                    path, json={"student": "Тестовый Ученик", "tutor": "Мария Иванова"}
                ).status_code,
                403,
            )


if __name__ == "__main__":
    try:
        unittest.main(verbosity=2)
    finally:
        test_folder.cleanup()
