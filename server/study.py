"""Занятия, домашние задания, цели и отчёты о часах."""

import json
import re
from flask import Blueprint, g, jsonify, request
from common import (
    full_name,
    get_data,
    goal_to_dict,
    http_link_from,
    mentor_can_manage_tutor,
    need_login,
    role_error,
    row_to_dict,
    scoped_item,
    scoped_rows,
    student_by_name,
    tutor_has_student,
    user_by_name,
    video_link_from,
)
from database import connect_db


study = Blueprint("study", __name__)


@study.route("/api/lessons", methods=["GET", "POST"])
@need_login
def lesson_list():
    if request.method == "POST":
        error = role_error("tutor", "mentor", "admin")
        if error:
            return error
    db = connect_db()
    if request.method == "GET":
        rows = scoped_rows(db, "lessons")
        db.close()
        return jsonify({"items": [row_to_dict(row) for row in rows]})
    data = get_data()
    student = student_by_name(db, data.get("student", ""))
    tutor = (
        g.user if g.user["role"] == "tutor" else user_by_name(db, data.get("tutor", ""), "tutor")
    )
    if not student or not tutor:
        db.close()
        return jsonify({"error": "Выберите зарегистрированных ученика и репетитора"}), 400
    if not mentor_can_manage_tutor(db, tutor["id"]):
        db.close()
        return jsonify({"error": "Этот репетитор не закреплён за вами"}), 403
    if not tutor_has_student(db, tutor["id"], student["id"]):
        db.close()
        return jsonify({
            "error": "Сначала администратор должен связать ученика с репетитором в разделе «Участники»"
        }), 403
    lesson_link, link_error = http_link_from(data.get("link"), "ссылку на занятие")
    if link_error:
        db.close()
        return jsonify({"error": link_error}), 400
    # RETURNING отдаёт именно нашу новую запись, а не последнюю запись другого запроса.
    row = db.execute(
        """INSERT INTO lessons
        (student, tutor, student_id, tutor_id, subject, lesson_date, lesson_time, duration, status, link, topic, materials)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, 'Запланировано', ?, ?, 0) RETURNING *""",
        (
            full_name(student),
            full_name(tutor),
            student["id"],
            tutor["id"],
            data.get("subject", ""),
            data.get("date", ""),
            data.get("time", ""),
            data.get("duration", "60 мин"),
            lesson_link or "",
            data.get("topic", ""),
        ),
    ).fetchone()
    db.commit()
    db.close()
    return jsonify({"item": row_to_dict(row)}), 201


@study.patch("/api/lessons/<int:lesson_id>")
@need_login
def lesson_update(lesson_id):
    error = role_error("tutor", "mentor", "admin")
    if error:
        return error
    data = get_data()
    db = connect_db()
    row = scoped_item(db, "lessons", lesson_id)
    if not row:
        db.close()
        return jsonify({"error": "Занятие не найдено или недоступно"}), 404
    status = data.get("status", row["status"])
    if status not in {"Запланировано", "Проведено", "Отменено", "Перенесено"}:
        db.close()
        return jsonify({"error": "Укажите корректный статус занятия"}), 400
    date = data.get("date", row["lesson_date"])
    time = data.get("time", row["lesson_time"])
    if (
        not isinstance(date, str)
        or not date.strip()
        or not isinstance(time, str)
        or not time.strip()
    ):
        db.close()
        return jsonify({"error": "Укажите новую дату и время занятия"}), 400
    db.execute(
        "UPDATE lessons SET status = ?, lesson_date = ?, lesson_time = ? WHERE id = ?",
        (status, date.strip(), time.strip(), lesson_id),
    )
    db.commit()
    row = db.execute("SELECT * FROM lessons WHERE id = ?", (lesson_id,)).fetchone()
    db.close()
    return jsonify({"item": row_to_dict(row)})


@study.route("/api/homework", methods=["GET", "POST"])
@need_login
def homework_list():
    if request.method == "POST":
        error = role_error("tutor", "mentor", "admin")
        if error:
            return error
    db = connect_db()
    if request.method == "GET":
        rows = scoped_rows(db, "homework")
        db.close()
        return jsonify({"items": [row_to_dict(row) for row in rows]})
    data = get_data()
    student = student_by_name(db, data.get("student", ""))
    tutor = (
        g.user if g.user["role"] == "tutor" else user_by_name(db, data.get("tutor", ""), "tutor")
    )
    if not student or not tutor:
        db.close()
        return jsonify({"error": "Выберите зарегистрированных ученика и репетитора"}), 400
    if not mentor_can_manage_tutor(db, tutor["id"]):
        db.close()
        return jsonify({"error": "Этот репетитор не закреплён за вами"}), 403
    if not tutor_has_student(db, tutor["id"], student["id"]):
        db.close()
        return jsonify({
            "error": "Сначала администратор должен связать ученика с репетитором в разделе «Участники»"
        }), 403
    attachment, link_error = http_link_from(data.get("attachment"), "ссылку на материалы")
    if link_error:
        db.close()
        return jsonify({"error": link_error}), 400
    row = db.execute(
        """INSERT INTO homework
        (title, subject, student, tutor, student_id, tutor_id, issued, deadline, status, attachment, score, description)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, 'Новые', ?, NULL, ?) RETURNING *""",
        (
            data.get("title", ""),
            data.get("subject", ""),
            full_name(student),
            full_name(tutor),
            student["id"],
            tutor["id"],
            "Сегодня",
            data.get("deadline", ""),
            attachment or "",
            data.get("description", ""),
        ),
    ).fetchone()
    db.commit()
    db.close()
    return jsonify({"item": row_to_dict(row)}), 201


@study.patch("/api/homework/<int:homework_id>/submit")
@need_login
def submit_homework(homework_id):
    error = role_error("student", "parent")
    if error:
        return error
    data = get_data()
    comment = data.get("comment", "")
    if not isinstance(comment, str) or len(comment.strip()) > 2000:
        return jsonify({"error": "Комментарий не должен превышать 2000 символов."}), 400
    submission_link, link_error = http_link_from(
        data.get("submissionLink"), "ссылку на выполненную работу"
    )
    if link_error:
        return jsonify({"error": link_error}), 400
    db = connect_db()
    row = scoped_item(db, "homework", homework_id)
    if not row:
        db.close()
        return jsonify({"error": "Задание не найдено или недоступно"}), 404
    db.execute(
        """UPDATE homework SET status = 'Сданы', submission_comment = ?, submission_link = ?
        WHERE id = ?""",
        (comment.strip(), submission_link or "", homework_id),
    )
    db.commit()
    row = db.execute("SELECT * FROM homework WHERE id = ?", (homework_id,)).fetchone()
    db.close()
    return jsonify({"item": row_to_dict(row)})


@study.patch("/api/homework/<int:homework_id>/grade")
@need_login
def grade_homework(homework_id):
    error = role_error("tutor", "mentor", "admin")
    if error:
        return error
    data = get_data()
    decision = data.get("decision", "accept")
    if decision not in {"accept", "revise"}:
        return jsonify({"error": "Выберите корректное решение по работе."}), 400
    review_comment = data.get("comment", "")
    if not isinstance(review_comment, str) or len(review_comment.strip()) > 2000:
        return jsonify({"error": "Комментарий не должен превышать 2000 символов."}), 400
    score = data.get("score", "")
    if decision == "accept":
        if isinstance(score, (int, float)):
            score = str(score)
        if not isinstance(score, str) or not re.fullmatch(
            r"\d+(?:[.,]\d+)?\s*/\s*\d+(?:[.,]\d+)?", score.strip()
        ):
            return jsonify({"error": "Укажите балл в формате «8 / 10»."}), 400
        saved_score = score.strip()
        status = "Проверено"
    else:
        saved_score = None
        status = "В работе"
    db = connect_db()
    row = scoped_item(db, "homework", homework_id)
    if not row:
        db.close()
        return jsonify({"error": "Задание не найдено или недоступно"}), 404
    db.execute(
        """UPDATE homework SET status = ?, score = ?, review_comment = ? WHERE id = ?""",
        (status, saved_score, review_comment.strip(), homework_id),
    )
    db.commit()
    row = db.execute("SELECT * FROM homework WHERE id = ?", (homework_id,)).fetchone()
    db.close()
    return jsonify({"item": row_to_dict(row)})


@study.route("/api/goals", methods=["GET", "POST"])
@need_login
def goals():
    if request.method == "POST":
        error = role_error("student")
        if error:
            return error
    db = connect_db()
    if request.method == "GET":
        rows = scoped_rows(db, "goals")
        db.close()
        return jsonify({"items": [goal_to_dict(row) for row in rows]})
    data = get_data()
    row = db.execute(
        """INSERT INTO goals (title, subject, deadline, tutor, student_id, tutor_id, description, tasks)
        VALUES (?, ?, ?, ?, ?, NULL, ?, ?) RETURNING *""",
        (
            data.get("title", ""),
            data.get("subject", ""),
            data.get("deadline", ""),
            "Не назначен",
            g.user["id"],
            data.get("description", ""),
            json.dumps(data.get("tasks", []), ensure_ascii=False),
        ),
    ).fetchone()
    db.commit()
    db.close()
    return jsonify({"item": goal_to_dict(row)}), 201


@study.patch("/api/goals/<int:goal_id>/tasks/<int:task_id>")
@need_login
def toggle_goal_task(goal_id, task_id):
    error = role_error("student", "tutor", "mentor", "admin")
    if error:
        return error
    db = connect_db()
    row = scoped_item(db, "goals", goal_id)
    if not row:
        db.close()
        return jsonify({"error": "Цель не найдена"}), 404
    tasks = json.loads(row["tasks"])
    for task in tasks:
        if task["id"] == task_id:
            task["done"] = not task["done"]
    db.execute(
        "UPDATE goals SET tasks = ? WHERE id = ?", (json.dumps(tasks, ensure_ascii=False), goal_id)
    )
    db.commit()
    updated = db.execute("SELECT * FROM goals WHERE id = ?", (goal_id,)).fetchone()
    db.close()
    return jsonify({"item": goal_to_dict(updated)})


@study.route("/api/review-lessons", methods=["GET", "POST"])
@need_login
def review_lessons():
    if request.method == "POST":
        error = role_error("tutor")
        if error:
            return error
        data = get_data()
        video_link, error = video_link_from(data.get("videoLink"))
        if error:
            return jsonify({"error": error}), 400
    db = connect_db()
    if request.method == "GET":
        if g.user["role"] == "admin":
            rows = db.execute("SELECT * FROM review_lessons ORDER BY id DESC").fetchall()
        elif g.user["role"] == "tutor":
            rows = db.execute(
                "SELECT * FROM review_lessons WHERE tutor_id = ? ORDER BY id DESC", (g.user["id"],)
            ).fetchall()
        elif g.user["role"] == "mentor":
            rows = db.execute(
                """SELECT * FROM review_lessons WHERE tutor_id IN
                (SELECT tutor_id FROM tutor_mentors WHERE mentor_id = ?) ORDER BY id DESC""",
                (g.user["id"],),
            ).fetchall()
        else:
            rows = []
        db.close()
        return jsonify({"items": [row_to_dict(row) for row in rows]})
    row = db.execute(
        """INSERT INTO review_lessons
        (tutor, tutor_id, tutor_initials, student, lesson_date, duration, video, video_link, shots, status, topic)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, 'Ожидает проверки', ?) RETURNING *""",
        (
            full_name(g.user),
            g.user["id"],
            "".join([g.user["first_name"][0], g.user["last_name"][0]]),
            data.get("student", ""),
            data.get("date", ""),
            data.get("duration", "60 мин"),
            int(bool(data.get("video")) or bool(video_link)),
            video_link,
            int(bool(data.get("shots"))),
            data.get("topic", ""),
        ),
    ).fetchone()
    db.commit()
    db.close()
    return jsonify({"item": row_to_dict(row)}), 201


@study.patch("/api/review-lessons/<int:lesson_id>")
@need_login
def review_lesson_update(lesson_id):
    error = role_error("mentor", "admin")
    if error:
        return error
    data = get_data()
    db = connect_db()
    if g.user["role"] == "mentor":
        row = db.execute(
            """SELECT * FROM review_lessons WHERE id = ? AND tutor_id IN
            (SELECT tutor_id FROM tutor_mentors WHERE mentor_id = ?)""",
            (lesson_id, g.user["id"]),
        ).fetchone()
    else:
        row = db.execute("SELECT * FROM review_lessons WHERE id = ?", (lesson_id,)).fetchone()
    if not row:
        db.close()
        return jsonify({"error": "Отчёт не найден или недоступен"}), 404
    db.execute(
        "UPDATE review_lessons SET status = ? WHERE id = ?",
        (data.get("status", "Проверено"), lesson_id),
    )
    db.commit()
    row = db.execute("SELECT * FROM review_lessons WHERE id = ?", (lesson_id,)).fetchone()
    db.close()
    return jsonify({"item": row_to_dict(row)})
