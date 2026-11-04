"""Проверка аккаунтов на временной базе. Реальные пользователи не меняются."""

import os
import io
import unittest
from datetime import datetime, timezone
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
        database.DATA_FOLDER = Path(test_folder.name) / self._testMethodName
        database.DATABASE_FILE = database.DATA_FOLDER / "cogito.db"
        database.start_database()

    def new_homework(self):
        tutor, _ = sign_in("tutor")
        response = tutor.post("/api/homework", json={
            "student": "Тестовый Ученик", "title": "Работа с файлами", "subject": "Математика",
        })
        self.assertEqual(response.status_code, 201)
        return response.json["item"]["id"]

    def test_homework_student_dropdown_and_ids(self):
        admin, _ = sign_in("admin")
        tutor, tutor_answer = sign_in("tutor")
        student, person = new_student()
        student.put("/api/profile", json={"firstName": "Тестовый", "lastName": "Ученик"})
        tutor_id = tutor_answer.json["user"]["id"]
        pairs = tutor.get("/api/homework/students").json["items"]
        self.assertNotIn(person["id"], {pair["studentId"] for pair in pairs})
        link = {"kind": "student_tutor", "firstId": person["id"], "secondId": tutor_id}
        self.assertEqual(admin.post("/api/admin/relationships", json=link).status_code, 201)
        pairs = tutor.get("/api/homework/students").json["items"]
        self.assertIn(person["id"], {pair["studentId"] for pair in pairs})
        self.assertTrue(all(pair["tutorId"] == tutor_id for pair in pairs))
        self.assertTrue(all("email" not in pair for pair in pairs))
        payload = {"studentId": person["id"], "tutorId": tutor_id, "title": "Задание по списку"}
        for role in ["tutor", "mentor", "admin"]:
            client, _ = sign_in(role)
            answer = client.post("/api/homework", json=payload)
            self.assertEqual(answer.status_code, 201)
            self.assertEqual(answer.json["item"]["student_id"], person["id"])
        for role in ["student", "parent"]:
            client, _ = sign_in(role)
            self.assertEqual(client.get("/api/homework/students").status_code, 403)
        self.assertEqual(tutor.post("/api/homework", json={**payload, "tutorId": 9999}).status_code, 403)
        self.assertEqual(tutor.post("/api/homework", json={**payload, "studentId": True}).status_code, 400)
        admin.delete("/api/admin/relationships", json=link)
        self.assertEqual(tutor.post("/api/homework", json=payload).status_code, 403)
        self.assertNotIn(person["id"], {pair["studentId"] for pair in tutor.get("/api/homework/students").json["items"]})

    def test_homework_files_permissions_and_restart(self):
        homework_id = self.new_homework()
        student, _ = sign_in("student")
        submitted = student.patch(f"/api/homework/{homework_id}/submit", data={
            "comment": "Решение во вложениях",
            "files": [(io.BytesIO(b"%PDF-1.4 test work"), "../../Работа.pdf"),
                      (io.BytesIO(b"2 + 2 = 4"), "Ответ.txt")],
        })
        self.assertEqual(submitted.status_code, 200, submitted.json)
        self.assertEqual(submitted.json["item"]["status"], "Сданы")
        files = submitted.json["item"]["submissionFiles"]
        self.assertEqual([file["name"] for file in files], ["Работа.pdf", "Ответ.txt"])
        url = files[0]["url"]
        for role in ACCOUNTS:
            client, _ = sign_in(role)
            with client.get(url) as response:
                self.assertEqual(response.status_code, 200, role)
                self.assertEqual(response.data, b"%PDF-1.4 test work")
                self.assertIn("attachment", response.headers["Content-Disposition"])
                self.assertEqual(response.headers["X-Content-Type-Options"], "nosniff")
                self.assertEqual(response.headers["Cache-Control"], "no-store")
        self.assertEqual(app.test_client().get(url).status_code, 401)
        outsider, _ = new_student()
        self.assertEqual(outsider.get(url).status_code, 404)
        self.assertEqual(outsider.delete(url).status_code, 404)
        self.assertEqual(outsider.patch(f"/api/homework/{homework_id}/submit", data={
            "files": (io.BytesIO(b"another answer"), "answer.txt"),
        }).status_code, 404)
        database.start_database()
        with student.get(url) as response:
            self.assertEqual(response.data, b"%PDF-1.4 test work")
        work = next(item for item in student.get("/api/homework").json["items"] if item["id"] == homework_id)
        self.assertEqual(len(work["submissionFiles"]), 2)
        tutor, _ = sign_in("tutor")
        self.assertEqual(tutor.delete(url).status_code, 403)
        checked = tutor.patch(f"/api/homework/{homework_id}/grade", json={"score": "8 / 10"})
        self.assertEqual(len(checked.json["item"]["submissionFiles"]), 2)
        self.assertEqual(student.delete(url).status_code, 409)
        self.assertEqual(student.patch(f"/api/homework/{homework_id}/submit", json={"comment": "Изменить"}).status_code, 409)
        tutor.patch(f"/api/homework/{homework_id}/grade", json={"decision": "revise"})
        removed = student.delete(url)
        self.assertEqual(removed.status_code, 200)
        self.assertEqual(len(removed.json["item"]["submissionFiles"]), 1)
        self.assertEqual(student.get(url).status_code, 404)

    def test_homework_upload_limits_and_rollback(self):
        homework_id = self.new_homework()
        student, _ = sign_in("student")
        endpoint = f"/api/homework/{homework_id}/submit"
        for files in [
            [(io.BytesIO(b"hello"), "answer.html")],
            [(io.BytesIO(b""), "empty.pdf")],
            [(io.BytesIO(b"valid"), "valid.txt"), (io.BytesIO(b"<script>"), "bad.svg")],
            [(io.BytesIO(b"work"), f"{i}.txt") for i in range(6)],
        ]:
            self.assertEqual(student.patch(endpoint, data={"files": files}).status_code, 400)
        with patch("study.MAX_FILE_SIZE", 8):
            self.assertEqual(student.patch(endpoint, data={
                "files": (io.BytesIO(b"too-large"), "answer.txt"),
            }).status_code, 400)
        with patch("study.MAX_WORK_SIZE", 32):
            response = student.patch(endpoint, data={
                "files": (io.BytesIO(b"x" * (2 * 1024 * 1024)), "large.txt"),
            })
            self.assertEqual(response.status_code, 413)
            self.assertIn("error", response.json)
            response.request.input_stream.close()
            response.close()
        with self.assertLogs(app.logger, level="ERROR"), patch(
            "werkzeug.datastructures.FileStorage.save", side_effect=OSError("Test disk error")
        ):
            response = student.patch(endpoint, data={"files": (io.BytesIO(b"work"), "answer.txt")})
            self.assertEqual(response.status_code, 500)
        db = database.connect_db()
        self.assertEqual(db.execute("SELECT COUNT(*) AS count FROM homework_files").fetchone()["count"], 0)
        self.assertEqual(db.execute("SELECT status FROM homework WHERE id = ?", (homework_id,)).fetchone()["status"], "Новые")
        db.close()
        self.assertEqual(list((database.DATA_FOLDER / "homework-files").glob("*")), [])
        self.assertEqual(student.patch(endpoint, json={"comment": "Ответ без файла"}).status_code, 200)

    def test_chat_uses_moscow_time(self):
        student, _ = sign_in("student")
        tutor, _ = sign_in("tutor")
        with patch("chat.datetime") as clock:
            clock.now.return_value = datetime(2026, 11, 4, 21, 15, tzinfo=timezone.utc)
            message = student.post("/api/messages", json={"dialogId": 1, "text": "Проверка времени"})
        self.assertEqual(message.json["item"]["time"], "00:15")
        self.assertEqual(tutor.get("/api/messages?dialog_id=1").json["items"][-1]["time"], "00:15")
        dialog = next(item for item in tutor.get("/api/conversations").json["items"] if item["id"] == 1)
        self.assertEqual(dialog["time"], "00:15")
        self.assertEqual(tutor.get("/api/notifications").json["items"][0]["time"], "00:15")

    def test_old_chat_time_migration_runs_once(self):
        db = database.connect_db()
        db.execute("UPDATE messages SET sent_time = '23:45' WHERE id = 1")
        db.execute("UPDATE messages SET sent_time = '2026-11-04T21:15:00+00:00' WHERE id = 2")
        db.execute("UPDATE notifications SET created_time = '23:45' WHERE id = 1")
        db.commit()
        db.close()
        with patch.dict(os.environ, {"FLASK_ENV": "production"}):
            database.start_database()
            database.start_database()
        db = database.connect_db()
        self.assertEqual(db.execute("SELECT sent_time FROM messages WHERE id = 1").fetchone()["sent_time"], "02:45")
        self.assertEqual(db.execute("SELECT sent_time FROM messages WHERE id = 2").fetchone()["sent_time"], "2026-11-04T21:15:00+00:00")
        self.assertEqual(db.execute("SELECT created_time FROM notifications WHERE id = 1").fetchone()["created_time"], "02:45")
        db.close()

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
