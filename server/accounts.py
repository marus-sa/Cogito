"""Регистрация, вход, подтверждение почты и профиль."""

import hashlib
import os
import re
import secrets
import smtplib
import ssl
from datetime import datetime, timedelta, timezone
from email.message import EmailMessage
from flask import Blueprint, current_app, g, jsonify, request
from html import escape
from urllib.parse import urlsplit
from werkzeug.security import check_password_hash, generate_password_hash
from common import (
    COOKIE_NAME,
    ROLE_LABELS,
    create_session,
    full_name,
    get_data,
    need_login,
    set_session_cookie,
    text_field,
    user_for_frontend,
)
from database import connect_db, is_production


EMAIL_VERIFICATION_SECONDS = 24 * 60 * 60


EMAIL_RESEND_COOLDOWN_SECONDS = 60


PUBLIC_REGISTER_ROLES = {"student", "parent", "tutor"}


accounts = Blueprint("accounts", __name__)


def email_token_fingerprint(token):
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


def configured_public_app_url():
    """Безопасный базовый URL для ссылки в письме.

    Адрес берётся только из окружения хостинга, а не из заголовка Host
    входящего запроса. Так нельзя разослать ссылку на чужой сайт через
    подменённый заголовок.
    """
    value = os.environ.get("APP_URL", "").strip().rstrip("/")
    if not value:
        return None
    try:
        parsed = urlsplit(value)
    except ValueError:
        return None
    if (
        parsed.scheme not in {"http", "https"}
        or not parsed.netloc
        or parsed.username
        or parsed.password
        or parsed.query
        or parsed.fragment
        or (is_production() and parsed.scheme != "https")
    ):
        return None
    return value


def smtp_configuration():
    """Возвращает SMTP-настройки только при полном безопасном наборе."""
    host = os.environ.get("SMTP_HOST", "").strip()
    username = os.environ.get("SMTP_USERNAME", "").strip()
    password = os.environ.get("SMTP_PASSWORD", "")
    sender = os.environ.get("SMTP_FROM_EMAIL", "").strip()
    if not host or not username or not password or not re.match(r"^\S+@\S+\.\S+$", sender):
        return None
    try:
        port = int(os.environ.get("SMTP_PORT", "587"))
    except ValueError:
        return None
    if not 1 <= port <= 65535:
        return None
    from_name = re.sub(
        r"[\r\n]", " ", os.environ.get("SMTP_FROM_NAME", "Cogito — Light Hearts")
    ).strip()
    return {
        "host": host,
        "port": port,
        "username": username,
        "password": password,
        "sender": sender,
        "from_name": from_name or "Cogito",
        "use_ssl": os.environ.get("SMTP_USE_SSL", "0").strip().lower() in {"1", "true", "yes"},
        "use_tls": os.environ.get("SMTP_USE_TLS", "1").strip().lower() not in {"0", "false", "no"},
    }


def email_verification_url(token):
    base_url = configured_public_app_url()
    if not base_url:
        return None
    # Fragment не отправляется серверу при переходе по ссылке и не попадает
    # в обычные access-логи. Vue прочитает его и отправит POST-запрос.
    return f"{base_url}/verify-email#token={token}"


def create_email_verification_token(db, user_id):
    """Выпускает новую одноразовую ссылку и аннулирует предыдущую."""
    token = secrets.token_urlsafe(32)
    now = datetime.now(timezone.utc)
    db.execute("DELETE FROM email_verification_tokens WHERE user_id = ?", (user_id,))
    db.execute(
        """INSERT INTO email_verification_tokens
        (user_id, token_fingerprint, expires_at, last_sent_at) VALUES (?, ?, ?, ?)""",
        (
            user_id,
            email_token_fingerprint(token),
            (now + timedelta(seconds=EMAIL_VERIFICATION_SECONDS)).isoformat(),
            now.isoformat(),
        ),
    )
    return token


def resend_allowed(row):
    """Ограничивает повторную отправку, не раскрывая существование почты."""
    try:
        last_sent = datetime.fromisoformat(row["last_sent_at"])
        if last_sent.tzinfo is None:
            last_sent = last_sent.replace(tzinfo=timezone.utc)
        return datetime.now(timezone.utc) - last_sent >= timedelta(
            seconds=EMAIL_RESEND_COOLDOWN_SECONDS
        )
    except (TypeError, ValueError):
        return True


def send_verification_email(user, token):
    """Отправляет письмо, не позволяя ошибке SMTP сорвать регистрацию."""
    settings = smtp_configuration()
    verification_url = email_verification_url(token)
    if not settings or not verification_url:
        return "not_configured"

    role_label = ROLE_LABELS.get(user["role"], "участник")
    recipient_name = user["first_name"].strip() or "друг"
    account_copy = (
        "После подтверждения команда Light Hearts проверит вашу заявку репетитора."
        if user["role"] == "tutor"
        else "После подтверждения вы сможете войти в личный кабинет."
    )
    text = (
        f"Здравствуйте, {recipient_name}!\n\n"
        f"Вы зарегистрировались в Cogito как {role_label.lower()}.\n"
        f"{account_copy}\n\n"
        f"Подтвердите электронную почту по ссылке:\n{verification_url}\n\n"
        "Ссылка действует 24 часа. Если это были не вы, просто проигнорируйте письмо."
    )
    html = (
        '<div style="font-family:Arial,sans-serif;color:#312b3d;line-height:1.55">'
        f'<h2 style="color:#6950a5">Здравствуйте, {escape(recipient_name)}!</h2>'
        f"<p>Вы зарегистрировались в <b>Cogito</b> как {escape(role_label.lower())}.</p>"
        f"<p>{escape(account_copy)}</p>"
        f'<p><a href="{escape(verification_url, quote=True)}" '
        'style="display:inline-block;padding:12px 18px;border-radius:9px;color:#fff;'
        'background:#6950a5;text-decoration:none;font-weight:bold">Подтвердить почту</a></p>'
        '<p style="font-size:13px;color:#716878">Ссылка действует 24 часа. Если вы не регистрировались, '
        "просто проигнорируйте это письмо.</p></div>"
    )
    message = EmailMessage()
    message["Subject"] = "Подтвердите регистрацию в Cogito"
    message["From"] = f'{settings["from_name"]} <{settings["sender"]}>'
    message["To"] = user["email"]
    message.set_content(text)
    message.add_alternative(html, subtype="html")

    try:
        if settings["use_ssl"]:
            smtp_client = smtplib.SMTP_SSL(
                settings["host"], settings["port"], timeout=10, context=ssl.create_default_context()
            )
        else:
            smtp_client = smtplib.SMTP(settings["host"], settings["port"], timeout=10)
        with smtp_client as smtp:
            smtp.ehlo()
            if not settings["use_ssl"] and settings["use_tls"]:
                smtp.starttls(context=ssl.create_default_context())
                smtp.ehlo()
            smtp.login(settings["username"], settings["password"])
            smtp.send_message(message)
    except (OSError, smtplib.SMTPException, ValueError):
        # Лог помогает владельцу настроить хостинг, но никогда не содержит
        # SMTP-пароль и не отправляется регистрирующемуся пользователю.
        current_app.logger.exception("Не удалось отправить письмо подтверждения регистрации")
        return "failed"
    return "sent"


@accounts.post("/api/auth/login")
def login():
    data = get_data()
    email = text_field(data, "email").lower()
    password = data.get("password", "")
    if not email or not isinstance(password, str) or not 1 <= len(password) <= 512:
        return jsonify({"error": "Введите почту и пароль"}), 400
    db = connect_db()
    user = db.execute("SELECT * FROM users WHERE email = ?", (email,)).fetchone()
    db.close()
    if not user or not check_password_hash(user["password_hash"], password):
        return jsonify({"error": "Неверная почта или пароль"}), 400
    # Роль берём из базы, а не из выбранной кнопки на устройстве.
    if not user["email_verified_at"]:
        return (
            jsonify(
                {
                    "error": "Сначала подтвердите почту по ссылке из письма.",
                    "code": "email_not_verified",
                }
            ),
            403,
        )
    if user["account_status"] == "pending":
        return jsonify({"error": "Заявка ещё ожидает подтверждения администратора"}), 403
    if user["account_status"] != "active":
        return jsonify({"error": "Этот аккаунт сейчас недоступен"}), 403

    remember = data.get("remember", True) is True
    days = 30 if remember else 1
    response = jsonify({"user": user_for_frontend(user)})
    return set_session_cookie(response, create_session(user["id"], days), days, remember)


@accounts.post("/api/auth/register")
def register():
    data = get_data()
    for key in [
        "firstName",
        "lastName",
        "email",
        "role",
        "grade",
        "subjects",
        "subject",
        "time",
        "child",
        "about",
    ]:
        data[key] = text_field(data, key, 2000 if key == "about" else 300)
    data["email"] = data["email"].lower()
    required = ["firstName", "lastName", "email", "password", "role"]
    if any(not isinstance(data.get(field), str) or not data[field].strip() for field in required):
        return jsonify({"error": "Заполните обязательные поля"}), 400
    if not 6 <= len(data["password"]) <= 512:
        return jsonify({"error": "Пароль должен содержать от 6 до 512 символов"}), 400
    if not re.match(r"^\S+@\S+\.\S+$", data["email"]):
        return jsonify({"error": "Проверьте формат электронной почты"}), 400
    if data["role"] not in PUBLIC_REGISTER_ROLES:
        return (
            jsonify({"error": "Служебную роль назначает администратор после подтверждения почты"}),
            403,
        )
    if data.get("consent") is not True:
        return jsonify({"error": "Нужно согласие на обработку персональных данных"}), 400

    account_status = "pending" if data["role"] == "tutor" else "active"
    db = connect_db()
    try:
        db.execute(
            """INSERT INTO users
            (first_name, last_name, email, password_hash, role, account_status, grade, subjects, available_time, child_name, bio,
             email_verified_at, avatar_color)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, NULL, '')""",
            (
                data["firstName"].strip(),
                data["lastName"].strip(),
                data["email"].strip().lower(),
                generate_password_hash(data["password"]),
                data["role"],
                account_status,
                data.get("grade", ""),
                data["subjects"] or data["subject"],
                data.get("time", ""),
                data.get("child", ""),
                data.get("about", ""),
            ),
        )
        user = db.execute(
            "SELECT * FROM users WHERE email = ?", (data["email"].strip().lower(),)
        ).fetchone()
        verification_token = create_email_verification_token(db, user["id"])
        db.commit()
    except Exception:
        db.rollback()
        db.close()
        return jsonify({"error": "Эта электронная почта уже зарегистрирована"}), 400
    db.close()
    email_status = send_verification_email(user, verification_token)
    return (
        jsonify(
            {
                "user": user_for_frontend(user),
                "needsApproval": account_status == "pending",
                "verificationRequired": True,
                "emailStatus": email_status,
            }
        ),
        201,
    )


@accounts.post("/api/auth/resend-email-verification")
def resend_email_verification():
    """Отправляет свежую ссылку, не раскрывая зарегистрированные адреса."""
    email = get_data().get("email", "")
    delivery_available = bool(smtp_configuration() and configured_public_app_url())
    answer = {
        "ok": True,
        "deliveryAvailable": delivery_available,
        "message": "Если этому адресу нужно подтверждение, письмо отправлено.",
    }
    if not isinstance(email, str) or not re.match(r"^\S+@\S+\.\S+$", email.strip()):
        return jsonify(answer), 202

    db = connect_db()
    try:
        user = db.execute(
            "SELECT * FROM users WHERE email = ?", (email.strip().lower(),)
        ).fetchone()
        if not user or user["email_verified_at"]:
            return jsonify(answer), 202
        existing = db.execute(
            "SELECT * FROM email_verification_tokens WHERE user_id = ?", (user["id"],)
        ).fetchone()
        if existing and not resend_allowed(existing):
            return jsonify(answer), 202
        verification_token = create_email_verification_token(db, user["id"])
        db.commit()
    except Exception:
        db.rollback()
        current_app.logger.exception("Не удалось подготовить повторную ссылку подтверждения")
        return jsonify(answer), 202
    finally:
        db.close()

    send_verification_email(user, verification_token)
    return jsonify(answer), 202


@accounts.post("/api/auth/verify-email")
def verify_email():
    token = get_data().get("token")
    if not isinstance(token, str) or len(token) < 32:
        return jsonify({"error": "Эта ссылка недействительна или уже устарела."}), 400

    fingerprint = email_token_fingerprint(token)
    now = datetime.now(timezone.utc).isoformat()
    db = connect_db()
    try:
        row = db.execute(
            """DELETE FROM email_verification_tokens
            WHERE token_fingerprint = ? AND expires_at > ? RETURNING user_id""",
            (fingerprint, now),
        ).fetchone()
        if not row:
            return jsonify({"error": "Эта ссылка недействительна или уже устарела."}), 400
        db.execute("UPDATE users SET email_verified_at = ? WHERE id = ?", (now, row["user_id"]))
        user = db.execute("SELECT * FROM users WHERE id = ?", (row["user_id"],)).fetchone()
        db.commit()
    except Exception:
        db.rollback()
        current_app.logger.exception("Не удалось подтвердить почту пользователя")
        return (
            jsonify(
                {
                    "error": "Не удалось подтвердить почту. Запросите новое письмо и попробуйте снова."
                }
            ),
            500,
        )
    finally:
        db.close()

    result = {
        "verified": True,
        "needsApproval": user["account_status"] == "pending",
        "user": user_for_frontend(user),
    }
    response = jsonify(result)
    if user["account_status"] == "active":
        return set_session_cookie(response, create_session(user["id"]))
    return response


@accounts.get("/api/auth/me")
@need_login
def current_user():
    return jsonify({"user": user_for_frontend(g.user)})


@accounts.post("/api/auth/logout")
def logout():
    # Даже просроченную cookie можно удалить, не требуя повторного входа.
    token = request.headers.get("Authorization", "").replace("Bearer ", "") or request.cookies.get(
        COOKIE_NAME, ""
    )
    db = connect_db()
    db.execute("DELETE FROM sessions WHERE token = ?", (token,))
    db.commit()
    db.close()
    response = jsonify({"ok": True})
    response.delete_cookie(COOKIE_NAME, path="/")
    return response


@accounts.route("/api/profile", methods=["GET", "PUT"])
@need_login
def profile():
    if request.method == "GET":
        return jsonify({"user": user_for_frontend(g.user)})
    data = get_data()
    requested_email = data.get("email", g.user["email"])
    if not isinstance(requested_email, str) or requested_email.strip().lower() != g.user["email"]:
        return (
            jsonify(
                {"error": "Смену почты пока выполняет координатор после проверки нового адреса."}
            ),
            400,
        )

    def profile_text(key, fallback, limit=500):
        value = data.get(key, fallback)
        if not isinstance(value, str):
            raise ValueError(key)
        return value.strip()[:limit]

    try:
        first_name = profile_text("firstName", g.user["first_name"], 80)
        last_name = profile_text("lastName", g.user["last_name"], 100)
        grade = profile_text("grade", g.user["grade"] or "", 30)
        subjects = profile_text("subjects", g.user["subjects"] or "", 300)
        available_time = profile_text("time", g.user["available_time"] or "", 300)
        child_name = profile_text("childName", g.user["child_name"] or "", 200)
        bio = profile_text("bio", g.user["bio"] or "", 2000)
    except ValueError:
        return jsonify({"error": "Проверьте формат данных профиля."}), 400
    if not first_name or not last_name:
        return jsonify({"error": "Укажите имя и фамилию."}), 400

    avatar_color = data.get("avatarColor", g.user["avatar_color"] or "")
    if not isinstance(avatar_color, str) or (
        avatar_color and not re.fullmatch(r"#[0-9a-fA-F]{6}", avatar_color)
    ):
        return jsonify({"error": "Выберите цвет из предложенной палитры."}), 400
    db = connect_db()
    try:
        db.execute(
            """UPDATE users SET first_name = ?, last_name = ?, grade = ?, subjects = ?,
            available_time = ?, child_name = ?, bio = ?, avatar_color = ? WHERE id = ?""",
            (
                first_name,
                last_name,
                grade,
                subjects,
                available_time,
                child_name,
                bio,
                avatar_color,
                g.user["id"],
            ),
        )
        db.commit()
        user = db.execute("SELECT * FROM users WHERE id = ?", (g.user["id"],)).fetchone()
    except Exception:
        db.rollback()
        current_app.logger.exception("Не удалось обновить профиль")
        return jsonify({"error": "Не удалось сохранить профиль. Попробуйте ещё раз."}), 500
    finally:
        db.close()
    return jsonify({"user": user_for_frontend(user)})
