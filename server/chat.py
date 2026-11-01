"""Контакты, диалоги, сообщения и уведомления."""

from datetime import datetime
from flask import Blueprint, g, jsonify, request
from common import ROLE_COLORS, ROLE_LABELS, full_name, get_data, initials, need_login, row_to_dict
from database import connect_db


chat = Blueprint("chat", __name__)


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


@chat.get("/api/chat/contacts")
@need_login
def chat_contacts():
    db = connect_db()
    rows = chat_contact_rows(db)
    db.close()
    return jsonify({"items": [chat_user(row) for row in rows]})


@chat.route("/api/conversations", methods=["GET", "POST"])
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
        conversation = db.execute(
            "SELECT * FROM conversations WHERE id = ?", (existing["conversation_id"],)
        ).fetchone()
        item = conversation_to_dict(db, conversation, g.user["id"])
        db.close()
        return jsonify({"item": item, "created": False})

    recipient = db.execute("SELECT * FROM users WHERE id = ?", (recipient_id,)).fetchone()
    conversation = db.execute(
        "INSERT INTO conversations (title) VALUES (?) RETURNING *", (full_name(recipient),)
    ).fetchone()
    db.executemany(
        "INSERT INTO conversation_members (conversation_id, user_id) VALUES (?, ?)",
        [(conversation["id"], g.user["id"]), (conversation["id"], recipient_id)],
    )
    db.commit()
    item = conversation_to_dict(db, conversation, g.user["id"])
    db.close()
    return jsonify({"item": item, "created": True}), 201


@chat.route("/api/messages", methods=["GET", "POST"])
@need_login
def messages():
    db = connect_db()
    dialog_id = (
        request.args.get("dialog_id", type=int)
        if request.method == "GET"
        else get_data().get("dialogId")
    )
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
        rows = db.execute(
            "SELECT * FROM messages WHERE dialog_id = ? ORDER BY id", (dialog_id,)
        ).fetchall()
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
    row = db.execute(
        "INSERT INTO messages (dialog_id, sender, sender_id, text, sent_time, is_read) VALUES (?, 'me', ?, ?, ?, 0) RETURNING *",
        (dialog_id, g.user["id"], text, now),
    ).fetchone()
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
    db.close()
    item = row_to_dict(row)
    item["sender"] = "me"
    return jsonify({"item": item}), 201


@chat.route("/api/notifications", methods=["GET", "PATCH"])
@need_login
def notifications():
    db = connect_db()
    if request.method == "GET":
        rows = db.execute(
            "SELECT * FROM notifications WHERE user_id = ? ORDER BY id DESC", (g.user["id"],)
        ).fetchall()
        db.close()
        return jsonify({"items": [row_to_dict(row) for row in rows]})
    data = get_data()
    if data.get("all"):
        db.execute("UPDATE notifications SET is_read = 1 WHERE user_id = ?", (g.user["id"],))
    elif data.get("id"):
        db.execute(
            "UPDATE notifications SET is_read = 1 WHERE id = ? AND user_id = ?",
            (data["id"], g.user["id"]),
        )
    db.commit()
    db.close()
    return jsonify({"ok": True})
