"""Тестовые участники и занятия. Используются только при COGITO_DEMO_DATA=1."""


from datetime import datetime, timezone
from werkzeug.security import generate_password_hash


def make_demo_user(first_name, last_name, email, role, grade="", subjects="", time=""):
    """Учётная запись только для локального демо-режима."""
    return (
        first_name,
        last_name,
        email,
        generate_password_hash("cogito123"),
        role,
        "active",
        grade,
        subjects,
        time,
        "",
        "",
        datetime.now(timezone.utc).isoformat(),
        "",
        "{}",
    )


def get_user_id(db, email):
    row = db.execute("SELECT id FROM users WHERE email = ?", (email,)).fetchone()
    return row["id"] if row else None


def seed_demo_data(db):
    has_users = db.execute("SELECT id FROM users LIMIT 1").fetchone()
    if has_users:
        return

    demo_users = [
        make_demo_user(
            "Тестовый",
            "Ученик",
            "student.demo@cogito.test",
            "student",
            "7",
            "Математика",
            "Пн, Ср · после 17:00",
        ),
        make_demo_user(
            "Мария",
            "Иванова",
            "maria@cogito.ru",
            "tutor",
            "11",
            "Математика, информатика",
            "Пн, Ср · после 16:00",
        ),
        make_demo_user(
            "Елена", "Смирнова", "elena@cogito.ru", "parent", "", "Математика", "Вечером"
        ),
        make_demo_user(
            "Алексей", "Петров", "alexey@cogito.ru", "mentor", "", "Координация", "Будни"
        ),
        make_demo_user(
            "Софья", "Орлова", "sofia@cogito.ru", "admin", "", "Управление проектом", "Будни"
        ),
    ]
    db.executemany(
        """INSERT INTO users
        (first_name, last_name, email, password_hash, role, account_status, grade, subjects, available_time, child_name, bio,
         email_verified_at, avatar_color, notification_preferences)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
        demo_users,
    )

    student_id = get_user_id(db, "student.demo@cogito.test")
    tutor_id = get_user_id(db, "maria@cogito.ru")
    parent_id = get_user_id(db, "elena@cogito.ru")
    mentor_id = get_user_id(db, "alexey@cogito.ru")

    db.execute(
        "INSERT INTO student_tutors (student_id, tutor_id) VALUES (?, ?)", (student_id, tutor_id)
    )

    db.executemany(
        """INSERT INTO lessons
        (student, tutor, student_id, tutor_id, subject, lesson_date, lesson_time, duration, status, link, topic, materials)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
        [
            (
                "Тестовый Ученик",
                "Мария Иванова",
                student_id,
                tutor_id,
                "Математика",
                "Сегодня, 18:00",
                "18:00–19:00",
                "60 мин",
                "Запланировано",
                "https://telemost.yandex.ru",
                "Линейные уравнения",
                1,
            ),
            (
                "Тестовый Ученик",
                "Мария Иванова",
                student_id,
                tutor_id,
                "Математика",
                "28 июля",
                "18:00–19:00",
                "60 мин",
                "Проведено",
                "",
                "Диагностическая работа",
                1,
            ),
        ],
    )
    db.executemany(
        """INSERT INTO homework
        (title, subject, student, tutor, student_id, tutor_id, issued, deadline, status, attachment, score, description)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
        [
            (
                "Линейные уравнения: тренировка",
                "Математика",
                "Тестовый Ученик",
                "Мария Иванова",
                student_id,
                tutor_id,
                "29 июля",
                "3 августа",
                "В работе",
                "Карточка с заданиями.pdf",
                None,
                "Решите задания 1–12. Покажите ход решения в тетради.",
            ),
            (
                "Диагностическая работа",
                "Математика",
                "Тестовый Ученик",
                "Мария Иванова",
                student_id,
                tutor_id,
                "22 июля",
                "28 июля",
                "Проверено",
                "Диагностика.pdf",
                "8 / 10",
                "Повторить действия с дробями перед следующим занятием.",
            ),
        ],
    )
    db.execute("INSERT INTO conversations (title) VALUES (?)", ("Тестовый ученик и Мария",))
    conversation = db.execute("SELECT id FROM conversations ORDER BY id DESC LIMIT 1").fetchone()
    dialog_id = conversation["id"]
    db.executemany(
        "INSERT INTO conversation_members (conversation_id, user_id) VALUES (?, ?)",
        [(dialog_id, student_id), (dialog_id, tutor_id)],
    )
    db.executemany(
        """INSERT INTO messages (dialog_id, sender, sender_id, text, sent_time, is_read)
        VALUES (?, ?, ?, ?, ?, ?)""",
        [
            (
                dialog_id,
                "them",
                tutor_id,
                "Добрый день! Посмотрела твою работу — есть несколько мест, которые разберём на занятии.",
                "12:34",
                1,
            ),
            (
                dialog_id,
                "me",
                student_id,
                "Спасибо! Я попробую ещё раз решить задачи 7 и 8.",
                "12:37",
                1,
            ),
            (
                dialog_id,
                "them",
                tutor_id,
                "Отлично, разберём на занятии! Можешь прислать фото, если что-то не получается.",
                "12:40",
                1,
            ),
        ],
    )
    db.executemany(
        """INSERT INTO notifications (user_id, icon, tone, title, text, created_time, is_read)
        VALUES (?, ?, ?, ?, ?, ?, ?)""",
        [
            (
                student_id,
                "CheckCircle2",
                "success",
                "Работа проверена",
                "Мария Иванова проверила «Диагностическую работу».",
                "20 минут назад",
                0,
            ),
            (
                student_id,
                "CalendarClock",
                "primary",
                "Занятие завтра",
                "Математика начнётся завтра в 18:00.",
                "2 часа назад",
                0,
            ),
            (
                student_id,
                "MessageCircle",
                "warning",
                "Новое сообщение",
                "Мария Иванова написала вам в чате.",
                "Сегодня, 12:40",
                1,
            ),
        ],
    )
    db.execute(
        "INSERT INTO tutor_mentors (tutor_id, mentor_id) VALUES (?, ?)", (tutor_id, mentor_id)
    )
    db.execute(
        "INSERT INTO parent_students (parent_id, student_id) VALUES (?, ?)", (parent_id, student_id)
    )
    db.execute(
        """INSERT INTO review_lessons
        (tutor, tutor_id, tutor_initials, student, lesson_date, duration, video, shots, status, topic)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
        (
            "Мария Иванова",
            tutor_id,
            "МИ",
            "Тестовый Ученик",
            "30 июля, 18:00",
            "60 мин",
            1,
            1,
            "Ожидает проверки",
            "Дроби и проценты",
        ),
    )
