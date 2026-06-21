#!/usr/bin/env python3
"""
Grammar App — Flask Backend
Duolingo-like language learning app with SQLite, gamification, and spaced repetition.
"""

import json
import time
from pathlib import Path
from flask import Flask, jsonify, request, send_from_directory, session, g

from database import (
    init_db, seed_default_data, get_db, get_user, get_user_by_username,
    create_user, update_user_xp, use_heart, recharge_hearts,
    update_streak, record_exercise_result, get_lesson_exercises,
    get_user_stats, get_review_vocab, update_vocab_mastery,
    get_leaderboard, add_vocabulary
)

app = Flask(__name__, static_folder="../frontend", static_url_path="")
app.secret_key = "alex-voice-grammar-app-secret-2026"

FRONTEND_DIR = Path(__file__).parent.parent / "frontend"


# ── Middleware ───────────────────────────────────────────
@app.before_request
def before_request():
    g.start_time = time.time()


@app.after_request
def after_request(response):
    response.headers["Access-Control-Allow-Origin"] = "*"
    response.headers["Access-Control-Allow-Methods"] = "GET, POST, OPTIONS"
    response.headers["Access-Control-Allow-Headers"] = "Content-Type"
    return response


# ── Static Files ────────────────────────────────────────
@app.route("/")
def index():
    return send_from_directory(str(FRONTEND_DIR), "index.html")


@app.route("/<path:filename>")
def serve_static(filename):
    return send_from_directory(str(FRONTEND_DIR), filename)


# ── Auth Routes ─────────────────────────────────────────
@app.route("/api/auth/register", methods=["POST"])
def register():
    data = request.json or {}
    username = data.get("username", "").strip()
    display_name = data.get("display_name", username)
    native_lang = data.get("native_lang", "es")
    target_lang = data.get("target_lang", "ja")
    
    if not username or len(username) < 2:
        return jsonify({"error": "Username must be at least 2 characters"}), 400
    
    user_id = create_user(username, display_name, native_lang, target_lang)
    if not user_id:
        return jsonify({"error": "Username already exists"}), 409
    
    session["user_id"] = user_id
    return jsonify({"ok": True, "user_id": user_id, "username": username})


@app.route("/api/auth/login", methods=["POST"])
def login():
    data = request.json or {}
    username = data.get("username", "").strip()
    
    if not username:
        return jsonify({"error": "Username required"}), 400
    
    user = get_user_by_username(username)
    if not user:
        return jsonify({"error": "User not found. Register first."}), 404
    
    session["user_id"] = user["id"]
    return jsonify({"ok": True, "user": user})


@app.route("/api/auth/me")
def auth_me():
    user_id = session.get("user_id")
    if not user_id:
        return jsonify({"error": "Not logged in"}), 401
    user = get_user(user_id)
    if not user:
        return jsonify({"error": "User not found"}), 404
    return jsonify({"user": user})


@app.route("/api/auth/logout", methods=["POST"])
def logout():
    session.clear()
    return jsonify({"ok": True})


# ── Content Routes ──────────────────────────────────────
@app.route("/api/units")
def list_units():
    conn = get_db()
    units = conn.execute("SELECT * FROM units ORDER BY sort_order").fetchall()
    conn.close()
    return jsonify({"units": [dict(u) for u in units]})


@app.route("/api/units/<int:unit_id>/lessons")
def list_lessons(unit_id):
    conn = get_db()
    lessons = conn.execute(
        "SELECT * FROM lessons WHERE unit_id = ? ORDER BY sort_order", (unit_id,)
    ).fetchall()
    conn.close()
    return jsonify({"lessons": [dict(l) for l in lessons]})


@app.route("/api/lessons/<int:lesson_id>")
def get_lesson(lesson_id):
    conn = get_db()
    lesson = conn.execute("SELECT * FROM lessons WHERE id = ?", (lesson_id,)).fetchone()
    exercises = get_lesson_exercises(lesson_id)
    conn.close()
    if not lesson:
        return jsonify({"error": "Lesson not found"}), 404
    
    # Remove correct_answer from response (don't leak answers!)
    safe_exercises = []
    for e in exercises:
        safe = {k: v for k, v in e.items() if k != "correct_answer"}
        safe_exercises.append(safe)
    
    return jsonify({"lesson": dict(lesson), "exercises": safe_exercises})


# ── Exercise Submission ─────────────────────────────────
@app.route("/api/exercises/submit", methods=["POST"])
def submit_exercise():
    user_id = session.get("user_id")
    if not user_id:
        return jsonify({"error": "Not logged in"}), 401
    
    data = request.json or {}
    exercise_id = data.get("exercise_id")
    user_answer = data.get("answer", "").strip()
    time_spent_ms = data.get("time_spent_ms", 0)
    
    if not exercise_id:
        return jsonify({"error": "exercise_id required"}), 400
    
    # Get correct answer
    conn = get_db()
    exercise = conn.execute("SELECT * FROM exercises WHERE id = ?", (exercise_id,)).fetchone()
    conn.close()
    
    if not exercise:
        return jsonify({"error": "Exercise not found"}), 404
    
    # Check answer (case-insensitive for Latin, exact for CJK)
    correct_answer = exercise["correct_answer"].strip()
    is_correct = user_answer.strip() == correct_answer or user_answer.lower() == correct_answer.lower()
    
    # Record result
    record_exercise_result(user_id, exercise_id, is_correct, time_spent_ms)
    
    # Update streak
    streak = update_streak(user_id)
    
    # Check hearts
    if not is_correct:
        heart_used = use_heart(user_id)
        if not heart_used:
            return jsonify({
                "correct": False,
                "correct_answer": correct_answer,
                "explanation": exercise["explanation"],
                "no_hearts": True,
                "streak": streak
            })
    
    # Get updated user
    user = get_user(user_id)
    
    return jsonify({
        "correct": is_correct,
        "correct_answer": correct_answer,
        "explanation": exercise["explanation"],
        "streak": streak,
        "xp": user["xp"] if is_correct else 0,
        "hearts": user["hearts"]
    })


# ── Progress Routes ─────────────────────────────────────
@app.route("/api/progress/stats")
def progress_stats():
    user_id = session.get("user_id")
    if not user_id:
        return jsonify({"error": "Not logged in"}), 401
    
    stats = get_user_stats(user_id)
    return jsonify(stats)


@app.route("/api/progress/complete-lesson", methods=["POST"])
def complete_lesson():
    user_id = session.get("user_id")
    if not user_id:
        return jsonify({"error": "Not logged in"}), 401
    
    data = request.json or {}
    lesson_id = data.get("lesson_id")
    score = data.get("score", 0)
    hearts_lost = data.get("hearts_lost", 0)
    
    conn = get_db()
    conn.execute("""
        INSERT INTO lesson_progress (user_id, lesson_id, completed, score, hearts_lost, completed_at)
        VALUES (?, ?, 1, ?, ?, datetime('now'))
        ON CONFLICT(user_id, lesson_id) DO UPDATE SET
            completed = 1,
            score = MAX(score, excluded.score),
            hearts_lost = excluded.hearts_lost,
            completed_at = datetime('now')
    """, (user_id, lesson_id, score, hearts_lost))
    conn.commit()
    conn.close()
    
    # XP reward for lesson completion
    conn2 = get_db()
    lesson_row = conn2.execute("SELECT xp_reward FROM lessons WHERE id = ?", (lesson_id,)).fetchone()
    conn2.close()
    if lesson_row:
        update_user_xp(user_id, lesson_row["xp_reward"])
    
    return jsonify({"ok": True})


# ── Vocabulary (SRS) ───────────────────────────────────
@app.route("/api/vocab/review")
def vocab_review():
    user_id = session.get("user_id")
    if not user_id:
        return jsonify({"error": "Not logged in"}), 401
    
    vocab = get_review_vocab(user_id)
    return jsonify({"vocab": vocab})


@app.route("/api/vocab/add", methods=["POST"])
def vocab_add():
    user_id = session.get("user_id")
    if not user_id:
        return jsonify({"error": "Not logged in"}), 401
    
    data = request.json or {}
    add_vocabulary(
        user_id,
        data["word"], data["translation"],
        data.get("source_lang", "en"),
        data.get("target_lang", "ja")
    )
    return jsonify({"ok": True})


@app.route("/api/vocab/update", methods=["POST"])
def vocab_update():
    user_id = session.get("user_id")
    if not user_id:
        return jsonify({"error": "Not logged in"}), 401
    
    data = request.json or {}
    update_vocab_mastery(data["vocab_id"], data["correct"])
    return jsonify({"ok": True})


# ── Leaderboard ─────────────────────────────────────────
@app.route("/api/leaderboard")
def leaderboard():
    board = get_leaderboard()
    return jsonify({"leaderboard": board})


# ── Hearts ──────────────────────────────────────────────
@app.route("/api/hearts/recharge", methods=["POST"])
def hearts_recharge():
    user_id = session.get("user_id")
    if not user_id:
        return jsonify({"error": "Not logged in"}), 401
    
    recharge_hearts(user_id)
    user = get_user(user_id)
    return jsonify({"hearts": user["hearts"]})


# ── Main ────────────────────────────────────────────────
if __name__ == "__main__":
    import sys
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')
    
    print("=" * 50)
    print("  📝 Alex Voice — Grammar App")
    print("=" * 50)
    
    init_db()
    seed_default_data()
    
    port = int(__import__("os").environ.get("GRAMMAR_PORT", "3004"))
    print(f"  Web UI:  http://localhost:{port}")
    print(f"  DB:      grammar.db")
    print(f"  Mode:    SQLite (local)")
    print("=" * 50)
    
    app.run(host="0.0.0.0", port=port, debug=False)
