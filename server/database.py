"""Таблицы и подключение к SQLite. База находится в server/data/cogito.db."""

from demo import seed_demo_data
import os
import sqlite3
from datetime import datetime, timedelta, timezone
from pathlib import Path

from werkzeug.security import generate_password_hash

ROOT = Path(__file__).parent
DATA_FOLDER = ROOT / "data"
DATABASE_FILE = DATA_FOLDER / "cogito.db"


def connect_db():
    if os.environ.get("DATABASE_URL"):
        raise RuntimeError("Cogito использует только SQLite. Удалите DATABASE_URL из настроек запуска.")
    DATA_FOLDER.mkdir(exist_ok=True)
    db = sqlite3.connect(DATABASE_FILE)
    db.row_factory = sqlite3.Row
    return db


def is_production():
    return os.environ.get("FLASK_ENV") == "production"


SCHEMA = [
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
        bio TEXT,
        email_verified_at TEXT,
        avatar_color TEXT,
        notification_preferences TEXT NOT NULL DEFAULT '{}'
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
        description TEXT,
        submission_comment TEXT,
        submission_link TEXT,
        review_comment TEXT
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
        video_link TEXT,
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
    """CREATE TABLE IF NOT EXISTS student_tutors (
        student_id INTEGER NOT NULL,
        tutor_id INTEGER NOT NULL,
        PRIMARY KEY (student_id, tutor_id)
    )""",
    """CREATE TABLE IF NOT EXISTS homework_files (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        homework_id INTEGER NOT NULL,
        filename TEXT NOT NULL,
        storage_name TEXT NOT NULL UNIQUE,
        size INTEGER NOT NULL
    )""",
    """CREATE TABLE IF NOT EXISTS admin_password_reset_tokens (
        token_fingerprint TEXT PRIMARY KEY,
        admin_user_id INTEGER NOT NULL,
        used_at TEXT NOT NULL,
        FOREIGN KEY (admin_user_id) REFERENCES users(id)
    )""",
    """CREATE TABLE IF NOT EXISTS admin_password_reset_authorizations (
        token_fingerprint TEXT PRIMARY KEY,
        expires_at TEXT NOT NULL
    )""",
    """CREATE TABLE IF NOT EXISTS email_verification_tokens (
        user_id INTEGER PRIMARY KEY,
        token_fingerprint TEXT NOT NULL,
        expires_at TEXT NOT NULL,
        last_sent_at TEXT NOT NULL,
        FOREIGN KEY (user_id) REFERENCES users(id)
    )""",
    """CREATE TABLE IF NOT EXISTS app_migrations (
        migration_key TEXT PRIMARY KEY,
        applied_at TEXT NOT NULL
    )""",
]


INDEXES = [
    "CREATE INDEX IF NOT EXISTS idx_sessions_user_id ON sessions(user_id)",
    "CREATE INDEX IF NOT EXISTS idx_sessions_expires_at ON sessions(expires_at)",
    "CREATE INDEX IF NOT EXISTS idx_conversation_members_user_id ON conversation_members(user_id)",
    "CREATE INDEX IF NOT EXISTS idx_homework_student_id ON homework(student_id)",
    "CREATE INDEX IF NOT EXISTS idx_homework_tutor_id ON homework(tutor_id)",
    "CREATE INDEX IF NOT EXISTS idx_lessons_student_id ON lessons(student_id)",
    "CREATE INDEX IF NOT EXISTS idx_lessons_tutor_id ON lessons(tutor_id)",
    "CREATE INDEX IF NOT EXISTS idx_messages_dialog_id ON messages(dialog_id)",
    "CREATE INDEX IF NOT EXISTS idx_notifications_user_id ON notifications(user_id)",
    "CREATE INDEX IF NOT EXISTS idx_student_tutors_tutor_id ON student_tutors(tutor_id)",
    "CREATE INDEX IF NOT EXISTS idx_homework_files_homework_id ON homework_files(homework_id)",
    "CREATE INDEX IF NOT EXISTS idx_admin_reset_authorizations_expires_at ON admin_password_reset_authorizations(expires_at)",
    "CREATE INDEX IF NOT EXISTS idx_email_verification_tokens_expires_at ON email_verification_tokens(expires_at)",
]


UPGRADE_COLUMNS = {
    "users": {
        "account_status": "TEXT NOT NULL DEFAULT 'active'",
        "email_verified_at": "TEXT",
        "avatar_color": "TEXT",
        "notification_preferences": "TEXT NOT NULL DEFAULT '{}'",
    },
    "sessions": {"expires_at": "TEXT NOT NULL DEFAULT ''"},
    "lessons": {"student_id": "INTEGER", "tutor_id": "INTEGER"},
    "homework": {
        "student_id": "INTEGER",
        "tutor_id": "INTEGER",
        "submission_comment": "TEXT",
        "submission_link": "TEXT",
        "review_comment": "TEXT",
    },
    "messages": {"sender_id": "INTEGER"},
    "notifications": {"user_id": "INTEGER"},
    "review_lessons": {"tutor_id": "INTEGER", "video_link": "TEXT"},
}


def upgrade_old_database(db):
    """Добавляет новые поля в старую локальную базу без удаления данных."""
    for table, columns in UPGRADE_COLUMNS.items():
        known = {row["name"] for row in db.execute(f"PRAGMA table_info({table})").fetchall()}
        for column, definition in columns.items():
            if column not in known:
                db.execute(f"ALTER TABLE {table} ADD COLUMN {column} {definition}")


def mark_existing_users_as_verified(db):
    """Не закрывает доступ тем, кто зарегистрировался до email-подтверждения.

    Маркер миграции критичен: без него каждый последующий рестарт подтвердил
    бы почту только что зарегистрированного человека без перехода по ссылке.
    """
    migration_key = "email-verification-existing-users-v1"
    applied = db.execute(
        "SELECT 1 FROM app_migrations WHERE migration_key = ?", (migration_key,)
    ).fetchone()
    if applied:
        return
    now = datetime.now(timezone.utc).isoformat()
    db.execute("UPDATE users SET email_verified_at = ? WHERE email_verified_at IS NULL", (now,))
    db.execute(
        "INSERT INTO app_migrations (migration_key, applied_at) VALUES (?, ?)",
        (migration_key, now),
    )


def add_existing_student_tutor_links(db):
    """Один раз сохраняет прежние назначения из занятий и заданий."""
    migration_key = "student-tutors-v1"
    if db.execute(
        "SELECT 1 FROM app_migrations WHERE migration_key = ?", (migration_key,)
    ).fetchone():
        return
    db.execute(
        """INSERT INTO student_tutors (student_id, tutor_id)
        SELECT records.student_id, records.tutor_id FROM (
            SELECT student_id, tutor_id FROM lessons
            UNION SELECT student_id, tutor_id FROM homework
        ) AS records
        JOIN users AS student ON student.id = records.student_id
        JOIN users AS tutor ON tutor.id = records.tutor_id
        WHERE student.role = 'student' AND tutor.role = 'tutor'
        ON CONFLICT DO NOTHING"""
    )
    db.execute(
        "INSERT INTO app_migrations (migration_key, applied_at) VALUES (?, ?)",
        (migration_key, datetime.now(timezone.utc).isoformat()),
    )


def fix_old_message_times(db):
    """Старый сервер записывал только часы и минуты по UTC. Сдвигаем их один раз."""
    migration_key = "message-times-msk-v1"
    if not is_production() or db.execute(
        "SELECT 1 FROM app_migrations WHERE migration_key = ?", (migration_key,)
    ).fetchone():
        return
    for table, column in [("messages", "sent_time"), ("notifications", "created_time")]:
        for row in db.execute(f"SELECT id, {column} FROM {table}").fetchall():
            try:
                old = datetime.strptime(row[column], "%H:%M")
            except (TypeError, ValueError):
                continue
            updated = (old + timedelta(hours=3)).strftime("%H:%M")
            db.execute(f"UPDATE {table} SET {column} = ? WHERE id = ?", (updated, row["id"]))
    db.execute(
        "INSERT INTO app_migrations (migration_key, applied_at) VALUES (?, ?)",
        (migration_key, datetime.now(timezone.utc).isoformat()),
    )


def start_database():
    db = connect_db()
    for statement in SCHEMA:
        db.execute(statement)
    upgrade_old_database(db)
    mark_existing_users_as_verified(db)
    add_existing_student_tutor_links(db)
    fix_old_message_times(db)
    for statement in INDEXES:
        db.execute(statement)
    has_bootstrap_admin = bool(
        os.environ.get("ADMIN_EMAIL") or os.environ.get("ADMIN_BOOTSTRAP_PASSWORD")
    )
    if is_production() or has_bootstrap_admin:
        seed_production_admin(db)
    elif os.environ.get("COGITO_DEMO_DATA") == "1":
        seed_demo_data(db)
    db.commit()
    db.close()


def seed_production_admin(db):
    """Создаёт первого администратора только в новой боевой базе.

    Пароль приходит из настроек хостинга и никогда не попадает
    в репозиторий или в базу в открытом виде.
    """
    has_admin = db.execute("SELECT id FROM users WHERE role = 'admin' LIMIT 1").fetchone()
    if has_admin:
        return

    email = os.environ.get("ADMIN_EMAIL", "").strip().lower()
    password = os.environ.get("ADMIN_BOOTSTRAP_PASSWORD", "")
    if not email or not password:
        raise RuntimeError(
            "Для первого запуска в production задайте ADMIN_EMAIL и ADMIN_BOOTSTRAP_PASSWORD."
        )
    if len(password) < 12:
        raise RuntimeError("ADMIN_BOOTSTRAP_PASSWORD должен содержать не менее 12 символов.")
    if db.execute("SELECT id FROM users WHERE lower(email) = ?", (email,)).fetchone():
        raise RuntimeError(
            "ADMIN_EMAIL занят обычным аккаунтом. Укажите другой адрес для первого администратора."
        )

    db.execute(
        """INSERT INTO users
        (first_name, last_name, email, password_hash, role, account_status, grade, subjects, available_time, child_name, bio,
         email_verified_at, avatar_color, notification_preferences)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
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
            datetime.now(timezone.utc).isoformat(),
            "",
            "{}",
        ),
    )
