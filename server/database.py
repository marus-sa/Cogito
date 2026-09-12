"""Хранение данных Cogito.

Локально проект можно запустить с SQLite. На хостинге передайте DATABASE_URL
от PostgreSQL — остальной код сервера останется таким же.
"""

import json
import os
import sqlite3
from pathlib import Path

from werkzeug.security import generate_password_hash


ROOT = Path(__file__).parent
DATA_FOLDER = ROOT / "data"
DATABASE_FILE = DATA_FOLDER / "cogito.db"


class PostgresDatabase:
    """Маленький переходник: приложение пишет запросы привычно, с ?."""

    def __init__(self, url):
        from psycopg import connect
        from psycopg.rows import dict_row

        self.connection = connect(url, row_factory=dict_row)

    def execute(self, query, params=()):
        return self.connection.execute(query.replace("?", "%s"), params)

    def executemany(self, query, params):
        cursor = self.connection.cursor()
        cursor.executemany(query.replace("?", "%s"), params)
        cursor.close()

    def commit(self):
        self.connection.commit()

    def close(self):
        self.connection.close()


def is_postgres():
    return bool(os.environ.get("DATABASE_URL"))


def connect_db():
    database_url = os.environ.get("DATABASE_URL")
    if database_url:
        return PostgresDatabase(database_url)

    DATA_FOLDER.mkdir(exist_ok=True)
    db = sqlite3.connect(DATABASE_FILE)
    db.row_factory = sqlite3.Row
    return db


def is_production():
    return os.environ.get("FLASK_ENV") == "production"


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
    )


SQLITE_SCHEMA = [
    """CREATE TABLE IF NOT EXISTS users (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        first_name TEXT NOT NULL,
        last_name TEXT NOT NULL,
        email TEXT NOT NULL UNIQUE,
        password_hash TEXT NOT NULL,
        role TEXT NOT NULL,
        account_status TEXT NOT NULL DEFAULT 'active',
        grade TEXT,
        subjects TEXT,
        available_time TEXT,
        child_name TEXT,
        bio TEXT
    )""",
    """CREATE TABLE IF NOT EXISTS sessions (
        token TEXT PRIMARY KEY,
        user_id INTEGER NOT NULL,
        created_at TEXT DEFAULT CURRENT_TIMESTAMP,
        expires_at TEXT NOT NULL,
        FOREIGN KEY (user_id) REFERENCES users(id)
    )""",
    """CREATE TABLE IF NOT EXISTS lessons (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        student TEXT NOT NULL,
        tutor TEXT NOT NULL,
        student_id INTEGER,
        tutor_id INTEGER,
        subject TEXT NOT NULL,
        lesson_date TEXT NOT NULL,
        lesson_time TEXT NOT NULL,
        duration TEXT NOT NULL,
        status TEXT NOT NULL,
        link TEXT,
        topic TEXT,
        materials INTEGER DEFAULT 0
    )""",
    """CREATE TABLE IF NOT EXISTS homework (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        title TEXT NOT NULL,
        subject TEXT NOT NULL,
        student TEXT NOT NULL,
        tutor TEXT NOT NULL,
        student_id INTEGER,
        tutor_id INTEGER,
        issued TEXT NOT NULL,
        deadline TEXT NOT NULL,
        status TEXT NOT NULL,
        attachment TEXT,
        score TEXT,
        description TEXT
    )""",
    """CREATE TABLE IF NOT EXISTS goals (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        title TEXT NOT NULL,
        subject TEXT NOT NULL,
        deadline TEXT NOT NULL,
        tutor TEXT NOT NULL,
        student_id INTEGER,
        tutor_id INTEGER,
        description TEXT,
        tasks TEXT NOT NULL
    )""",
    """CREATE TABLE IF NOT EXISTS conversations (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        title TEXT NOT NULL DEFAULT ''
    )""",
    """CREATE TABLE IF NOT EXISTS conversation_members (
        conversation_id INTEGER NOT NULL,
        user_id INTEGER NOT NULL,
        PRIMARY KEY (conversation_id, user_id)
    )""",
    """CREATE TABLE IF NOT EXISTS messages (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        dialog_id INTEGER NOT NULL,
        sender TEXT NOT NULL,
        sender_id INTEGER,
        text TEXT NOT NULL,
        sent_time TEXT NOT NULL,
        is_read INTEGER DEFAULT 0
    )""",
    """CREATE TABLE IF NOT EXISTS notifications (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER,
        icon TEXT NOT NULL,
        tone TEXT NOT NULL,
        title TEXT NOT NULL,
        text TEXT NOT NULL,
        created_time TEXT NOT NULL,
        is_read INTEGER DEFAULT 0
    )""",
    """CREATE TABLE IF NOT EXISTS review_lessons (
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
    )""",
    """CREATE TABLE IF NOT EXISTS tutor_mentors (
        tutor_id INTEGER NOT NULL,
        mentor_id INTEGER NOT NULL,
        PRIMARY KEY (tutor_id, mentor_id)
    )""",
    """CREATE TABLE IF NOT EXISTS parent_students (
        parent_id INTEGER NOT NULL,
        student_id INTEGER NOT NULL,
        PRIMARY KEY (parent_id, student_id)
    )""",
]


POSTGRES_SCHEMA = [
    statement.replace("INTEGER PRIMARY KEY AUTOINCREMENT", "SERIAL PRIMARY KEY")
    for statement in SQLITE_SCHEMA
]


INDEXES = [
    "CREATE INDEX IF NOT EXISTS idx_sessions_user_id ON sessions(user_id)",
    "CREATE INDEX IF NOT EXISTS idx_sessions_expires_at ON sessions(expires_at)",
    "CREATE INDEX IF NOT EXISTS idx_homework_student_id ON homework(student_id)",
    "CREATE INDEX IF NOT EXISTS idx_homework_tutor_id ON homework(tutor_id)",
    "CREATE INDEX IF NOT EXISTS idx_lessons_student_id ON lessons(student_id)",
    "CREATE INDEX IF NOT EXISTS idx_lessons_tutor_id ON lessons(tutor_id)",
    "CREATE INDEX IF NOT EXISTS idx_messages_dialog_id ON messages(dialog_id)",
    "CREATE INDEX IF NOT EXISTS idx_notifications_user_id ON notifications(user_id)",
]


UPGRADE_COLUMNS = {
    "users": {"account_status": "TEXT NOT NULL DEFAULT 'active'"},
    "sessions": {"expires_at": "TEXT NOT NULL DEFAULT ''"},
    "lessons": {"student_id": "INTEGER", "tutor_id": "INTEGER"},
    "homework": {"student_id": "INTEGER", "tutor_id": "INTEGER"},
    "goals": {"student_id": "INTEGER", "tutor_id": "INTEGER"},
    "messages": {"sender_id": "INTEGER"},
    "notifications": {"user_id": "INTEGER"},
    "review_lessons": {"tutor_id": "INTEGER"},
}


def upgrade_old_database(db):
    """Добавляет новые поля в старую локальную базу без удаления данных."""
    if is_postgres():
        for table, columns in UPGRADE_COLUMNS.items():
            for column, definition in columns.items():
                db.execute(f"ALTER TABLE {table} ADD COLUMN IF NOT EXISTS {column} {definition}")
        return

    for table, columns in UPGRADE_COLUMNS.items():
        known = {row["name"] for row in db.execute(f"PRAGMA table_info({table})").fetchall()}
        for column, definition in columns.items():
            if column not in known:
                db.execute(f"ALTER TABLE {table} ADD COLUMN {column} {definition}")


def start_database():
    db = connect_db()
    schema = POSTGRES_SCHEMA if is_postgres() else SQLITE_SCHEMA
    for statement in schema:
        db.execute(statement)
    upgrade_old_database(db)
    for statement in INDEXES:
        db.execute(statement)
    if is_production():
        seed_production_admin(db)
    else:
        seed_demo_data(db)
    db.commit()
    db.close()


def get_user_id(db, email):
    row = db.execute("SELECT id FROM users WHERE email = ?", (email,)).fetchone()
    return row["id"] if row else None


def seed_production_admin(db):
    """Создаёт первого администратора только в новой боевой базе.

    Пароль приходит из переменной окружения Render и никогда не попадает
    в репозиторий или в базу в открытом виде.
    """
    has_users = db.execute("SELECT id FROM users LIMIT 1").fetchone()
    if has_users:
        return

    email = os.environ.get("ADMIN_EMAIL", "").strip().lower()
    password = os.environ.get("ADMIN_BOOTSTRAP_PASSWORD", "")
    if not email or not password:
        raise RuntimeError(
            "Для первого запуска в production задайте ADMIN_EMAIL и ADMIN_BOOTSTRAP_PASSWORD."
        )
    if len(password) < 12:
        raise RuntimeError("ADMIN_BOOTSTRAP_PASSWORD должен содержать не менее 12 символов.")

    db.execute(
        """INSERT INTO users
        (first_name, last_name, email, password_hash, role, account_status, grade, subjects, available_time, child_name, bio)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
        (
            "Администратор",
            "Cogito",
            email,
            generate_password_hash(password),
            "admin",
            "active",
            "",
            "Управление проектом",
            "",
            "",
            "",
        ),
    )


def seed_demo_data(db):
    has_users = db.execute("SELECT id FROM users LIMIT 1").fetchone()
    if has_users:
        return

    demo_users = [
        make_demo_user("Анна", "Смирнова", "anna@cogito.ru", "student", "7", "Математика", "Пн, Ср · после 17:00"),
        make_demo_user("Мария", "Иванова", "maria@cogito.ru", "tutor", "11", "Математика, информатика", "Пн, Ср · после 16:00"),
        make_demo_user("Елена", "Смирнова", "elena@cogito.ru", "parent", "", "Математика", "Вечером"),
        make_demo_user("Алексей", "Петров", "alexey@cogito.ru", "mentor", "", "Координация", "Будни"),
        make_demo_user("Софья", "Орлова", "sofia@cogito.ru", "admin", "", "Управление проектом", "Будни"),
    ]
    db.executemany(
        """INSERT INTO users
        (first_name, last_name, email, password_hash, role, account_status, grade, subjects, available_time, child_name, bio)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
        demo_users,
    )

    student_id = get_user_id(db, "anna@cogito.ru")
    tutor_id = get_user_id(db, "maria@cogito.ru")
    parent_id = get_user_id(db, "elena@cogito.ru")
    mentor_id = get_user_id(db, "alexey@cogito.ru")

    db.executemany(
        """INSERT INTO lessons
        (student, tutor, student_id, tutor_id, subject, lesson_date, lesson_time, duration, status, link, topic, materials)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
        [
            ("Анна Смирнова", "Мария Иванова", student_id, tutor_id, "Математика", "Сегодня, 18:00", "18:00–19:00", "60 мин", "Запланировано", "https://telemost.yandex.ru", "Линейные уравнения", 1),
            ("Анна Смирнова", "Мария Иванова", student_id, tutor_id, "Математика", "28 июля", "18:00–19:00", "60 мин", "Проведено", "", "Диагностическая работа", 1),
        ],
    )
    db.executemany(
        """INSERT INTO homework
        (title, subject, student, tutor, student_id, tutor_id, issued, deadline, status, attachment, score, description)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
        [
            ("Линейные уравнения: тренировка", "Математика", "Анна Смирнова", "Мария Иванова", student_id, tutor_id, "29 июля", "3 августа", "В работе", "Карточка с заданиями.pdf", None, "Решите задания 1–12. Покажите ход решения в тетради."),
            ("Диагностическая работа", "Математика", "Анна Смирнова", "Мария Иванова", student_id, tutor_id, "22 июля", "28 июля", "Проверено", "Диагностика.pdf", "8 / 10", "Повторить действия с дробями перед следующим занятием."),
        ],
    )
    tasks = [
        {"id": 1, "label": "Повторить дроби", "done": True},
        {"id": 2, "label": "Решить диагностическую работу", "done": True},
        {"id": 3, "label": "Изучить линейные уравнения", "done": False},
        {"id": 4, "label": "Выполнить итоговый тест", "done": False},
    ]
    db.execute(
        """INSERT INTO goals (title, subject, deadline, tutor, student_id, tutor_id, description, tasks)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
        ("Повысить оценку по математике с 3 до 4", "Математика", "25 августа", "Мария Иванова", student_id, tutor_id, "Уверенно решать базовые задания и выйти на твёрдую четвёрку к концу четверти.", json.dumps(tasks, ensure_ascii=False)),
    )

    db.execute("INSERT INTO conversations (title) VALUES (?)", ("Анна и Мария",))
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
            (dialog_id, "them", tutor_id, "Анна, добрый день! Посмотрела твою работу — есть несколько мест, которые разберём на занятии.", "12:34", 1),
            (dialog_id, "me", student_id, "Спасибо! Я попробую ещё раз решить задачи 7 и 8.", "12:37", 1),
            (dialog_id, "them", tutor_id, "Отлично, разберём на занятии! Можешь прислать фото, если что-то не получается.", "12:40", 1),
        ],
    )
    db.executemany(
        """INSERT INTO notifications (user_id, icon, tone, title, text, created_time, is_read)
        VALUES (?, ?, ?, ?, ?, ?, ?)""",
        [
            (student_id, "CheckCircle2", "success", "Работа проверена", "Мария Иванова проверила «Диагностическую работу».", "20 минут назад", 0),
            (student_id, "CalendarClock", "primary", "Занятие завтра", "Математика начнётся завтра в 18:00.", "2 часа назад", 0),
            (student_id, "MessageCircle", "warning", "Новое сообщение", "Мария Иванова написала вам в чате.", "Сегодня, 12:40", 1),
        ],
    )
    db.execute("INSERT INTO tutor_mentors (tutor_id, mentor_id) VALUES (?, ?)", (tutor_id, mentor_id))
    db.execute("INSERT INTO parent_students (parent_id, student_id) VALUES (?, ?)", (parent_id, student_id))
    db.execute(
        """INSERT INTO review_lessons
        (tutor, tutor_id, tutor_initials, student, lesson_date, duration, video, shots, status, topic)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
        ("Мария Иванова", tutor_id, "МИ", "Анна Смирнова", "30 июля, 18:00", "60 мин", 1, 1, "Ожидает проверки", "Дроби и проценты"),
    )
