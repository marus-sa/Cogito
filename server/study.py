"""Занятия, домашние задания, цели и отчёты о часах."""

import json
import re
import secrets
from pathlib import Path
from flask import Blueprint, current_app, g, jsonify, request, send_from_directory
from werkzeug.exceptions import HTTPException
import database
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
    user_by_id,
    user_by_name,
    video_link_from,
)
from database import connect_db


study = Blueprint("study", __name__)
MAX_FILE_SIZE = 8 * 1024 * 1024
MAX_WORK_SIZE = 8 * 1024 * 1024
MAX_FILES = 5
FILE_TYPES = {".pdf", ".docx", ".txt", ".jpg", ".jpeg", ".png", ".webp", ".heic", ".heif"}


def homework_item(db, row):
    item = row_to_dict(row)
    files = db.execute(
        "SELECT id, filename, size FROM homework_files WHERE homework_id = ? ORDER BY id",
        (row["id"],),
    ).fetchall()
    item["submissionFiles"] = [
        {"id": file["id"], "name": file["filename"], "size": file["size"],
         "url": f'/api/homework/{row["id"]}/files/{file["id"]}'}
        for file in files
    ]
    return item


@study.get("/api/homework/students")
@need_login
def homework_students():
    error = role_error("tutor", "mentor", "admin")
    if error:
        return error
    where, params = "1 = 1", ()
    if g.user["role"] == "tutor":
        where, params = "links.tutor_id = ?", (g.user["id"],)
    elif g.user["role"] == "mentor":
        where = "links.tutor_id IN (SELECT tutor_id FROM tutor_mentors WHERE mentor_id = ?)"
        params = (g.user["id"],)
    db = connect_db()
    rows = db.execute(f"""SELECT student.id AS student_id, student.first_name, student.last_name,
        student.grade, tutor.id AS tutor_id, tutor.first_name AS tutor_first_name,
        tutor.last_name AS tutor_last_name
        FROM student_tutors AS links
        JOIN users AS student ON student.id = links.student_id
        JOIN users AS tutor ON tutor.id = links.tutor_id
        WHERE {where} AND student.role = 'student' AND tutor.role = 'tutor'
        AND student.account_status = 'active' AND tutor.account_status = 'active'
        AND student.email_verified_at IS NOT NULL AND tutor.email_verified_at IS NOT NULL
        ORDER BY student.first_name, student.last_name, tutor.first_name, student.id""", params).fetchall()
    db.close()
    return jsonify({"items": [
        {"studentId": row["student_id"], "student": full_name(row), "grade": row["grade"],
         "tutorId": row["tutor_id"], "tutor": f'{row["tutor_first_name"]} {row["tutor_last_name"]}'}
        for row in rows
    ]})


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
        items = [homework_item(db, row) for row in rows]
        db.close()
        return jsonify({"items": items})
    data = get_data()
    if "studentId" in data:
        if type(data["studentId"]) is not int or type(data.get("tutorId")) is not int:
            db.close()
            return jsonify({"error": "Выберите ученика из списка"}), 400
        student = user_by_id(db, data["studentId"], "student")
        tutor_id = g.user["id"] if g.user["role"] == "tutor" else data["tutorId"]
        if g.user["role"] == "tutor" and data["tutorId"] != tutor_id:
            db.close()
            return jsonify({"error": "Нельзя назначить задание от другого репетитора"}), 403
        tutor = user_by_id(db, tutor_id, "tutor")
    else:
        student = student_by_name(db, data.get("student", ""))
        tutor = g.user if g.user["role"] == "tutor" else user_by_name(db, data.get("tutor", ""), "tutor")
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
    db = connect_db()
    saved_paths = []
    try:
        row = scoped_item(db, "homework", homework_id)
        if not row:
            return jsonify({"error": "Задание не найдено или недоступно"}), 404
        if row["status"] == "Проверено":
            return jsonify({"error": "Проверенную работу нельзя изменить. Попросите репетитора вернуть её на доработку."}), 409
        request.max_content_length = MAX_WORK_SIZE + 1024 * 1024
        request.max_form_parts = 10
        multipart = request.mimetype == "multipart/form-data"
        data = request.form if multipart else get_data()
        uploads = [file for file in request.files.getlist("files") if file.filename] if multipart else []
        comment = data.get("comment", "")
        if not isinstance(comment, str) or len(comment.strip()) > 2000:
            return jsonify({"error": "Комментарий не должен превышать 2000 символов."}), 400
        submission_link, link_error = http_link_from(data.get("submissionLink"), "ссылку на выполненную работу")
        if link_error:
            return jsonify({"error": link_error}), 400
        existing = db.execute(
            """SELECT COUNT(*) AS count, COALESCE(SUM(size), 0) AS size
            FROM homework_files WHERE homework_id = ?""", (homework_id,),
        ).fetchone()
        if existing["count"] + len(uploads) > MAX_FILES:
            return jsonify({"error": "К одной работе можно прикрепить до 5 файлов. Уберите ненужные файлы."}), 400
        prepared = []
        total_size = existing["size"]
        for upload in uploads:
            name = Path(upload.filename.replace("\\", "/")).name
            name = re.sub(r"[\x00-\x1f\x7f]", "", name).strip()[:180]
            extension = Path(name).suffix.lower()
            if extension not in FILE_TYPES:
                return jsonify({"error": "Прикрепите PDF, DOCX, TXT или фото JPG, PNG, WEBP, HEIC."}), 400
            size = upload.stream.seek(0, 2)
            upload.stream.seek(0)
            if size == 0 or size > MAX_FILE_SIZE:
                return jsonify({"error": "Каждый файл должен быть непустым и не больше 8 МБ."}), 400
            total_size += size
            prepared.append((upload, name, size, secrets.token_hex(16) + extension))
        if total_size > MAX_WORK_SIZE:
            return jsonify({"error": "Общий размер файлов одной работы — не больше 8 МБ. Большую работу можно отправить ссылкой."}), 400
        used = db.execute("SELECT COALESCE(SUM(size), 0) AS size FROM homework_files").fetchone()["size"]
        if used + total_size - existing["size"] > 750 * 1024 * 1024:
            return jsonify({"error": "Хранилище заполнено. Пока отправьте ссылку на работу на облачном диске."}), 507
        if not comment.strip() and not submission_link and not total_size:
            return jsonify({"error": "Добавьте комментарий, ссылку или файл с выполненной работой."}), 400
        folder = database.DATA_FOLDER / "homework-files"
        if prepared:
            folder.mkdir(exist_ok=True)
        for upload, name, size, storage_name in prepared:
            path = folder / storage_name
            saved_paths.append(path)
            upload.save(path)
            db.execute(
                """INSERT INTO homework_files (homework_id, filename, storage_name, size)
                VALUES (?, ?, ?, ?)""", (homework_id, name, storage_name, size),
            )
        db.execute(
            "UPDATE homework SET status = 'Сданы', submission_comment = ?, submission_link = ? WHERE id = ?",
            (comment.strip(), submission_link or "", homework_id),
        )
        row = db.execute("SELECT * FROM homework WHERE id = ?", (homework_id,)).fetchone()
        item = homework_item(db, row)
        db.commit()
        return jsonify({"item": item})
    except HTTPException:
        raise
    except Exception:
        db.rollback()
        for path in saved_paths:
            path.unlink(missing_ok=True)
        current_app.logger.exception("Не удалось сохранить файлы домашней работы")
        return jsonify({"error": "Не удалось сохранить работу. Попробуйте ещё раз или отправьте ссылку на файл."}), 500
    finally:
        db.close()


@study.route("/api/homework/<int:homework_id>/files/<int:file_id>", methods=["GET", "DELETE"])
@need_login
def homework_file(homework_id, file_id):
    db = connect_db()
    try:
        work = scoped_item(db, "homework", homework_id)
        file = db.execute(
            "SELECT * FROM homework_files WHERE id = ? AND homework_id = ?",
            (file_id, homework_id),
        ).fetchone()
        if not work or not file:
            return jsonify({"error": "Файл не найден или недоступен"}), 404
        folder = database.DATA_FOLDER / "homework-files"
        if request.method == "DELETE":
            error = role_error("student", "parent")
            if error:
                return error
            if work["status"] == "Проверено":
                return jsonify({"error": "Файлы проверенной работы нельзя удалить."}), 409
            # Имя в хранилище создаёт сервер, а не пользователь.
            if not re.fullmatch(r"[0-9a-f]{32}\.[a-z]+", file["storage_name"]):
                return jsonify({"error": "Не удалось удалить файл."}), 500
            (folder / file["storage_name"]).unlink(missing_ok=True)
            db.execute("DELETE FROM homework_files WHERE id = ?", (file_id,))
            db.commit()
            return jsonify({"item": homework_item(db, work)})
        return send_from_directory(folder, file["storage_name"], as_attachment=True,
                                   download_name=file["filename"], mimetype="application/octet-stream")
    finally:
        db.close()


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
    item = homework_item(db, row)
    db.close()
    return jsonify({"item": item})


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
