"""Настройка администратора, восстановление доступа и участники."""

import hashlib
import hmac
import os
import re
import secrets
from datetime import datetime, timedelta, timezone
from flask import Blueprint, current_app, g, jsonify, request
from werkzeug.security import generate_password_hash
from common import (
    ROLE_LABELS,
    create_session,
    get_data,
    need_login,
    role_error,
    row_to_dict,
    set_session_cookie,
    user_for_frontend,
)
from database import connect_db, is_production


ADMIN_RESET_TOKEN_ENV = "ADMIN_RESET_TOKEN"


ADMIN_RESET_AUTH_COOKIE = "cogito_admin_reset"


ADMIN_RESET_AUTH_COOKIE_PATH = "/api/auth/admin-password-reset"


ADMIN_RESET_AUTH_SECONDS = 15 * 60


admin = Blueprint("admin", __name__)


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


def local_admin_setup_allowed():
    """Первого администратора локально создаёт только владелец компьютера.

    На опубликованном сайте этот маршрут недоступен: там первого администратора
    создают переменные ADMIN_EMAIL и ADMIN_BOOTSTRAP_PASSWORD. Локально доступ
    закрывается сразу после создания первого админа.
    """
    return not is_production() and request.remote_addr in {"127.0.0.1", "::1"}


@admin.route("/api/setup/local-admin", methods=["GET", "POST"])
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


@admin.post("/api/auth/admin-password-reset/authorize")
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
        current_app.logger.exception("Не удалось подтвердить код восстановления администратора")
        return admin_reset_error()
    finally:
        db.close()
    return set_reset_authorization_cookie(jsonify({"authorized": True}), authorization)


@admin.route("/api/auth/admin-password-reset", methods=["GET", "POST"])
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
        current_app.logger.exception("Не удалось выполнить сброс доступа администратора")
        return admin_reset_error()
    finally:
        db.close()
    return clear_reset_authorization_cookie(jsonify({"ok": True}))


@admin.get("/api/admin/users")
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


@admin.get("/api/admin/dashboard")
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


@admin.patch("/api/admin/users/<int:user_id>")
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


@admin.route("/api/admin/relationships", methods=["GET", "POST", "DELETE"])
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
