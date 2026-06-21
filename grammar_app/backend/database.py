#!/usr/bin/env python3
"""
Grammar App — Database Module
SQLite database with schema for a Duolingo-like language learning app.
"""

import sqlite3
import json
from pathlib import Path
from datetime import datetime, timedelta

DB_PATH = Path(__file__).parent.parent / "data" / "grammar.db"


def get_db():
    """Get database connection with WAL mode."""
    conn = sqlite3.connect(str(DB_PATH))
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA foreign_keys=ON")
    return conn


def init_db():
    """Initialize database schema."""
    conn = get_db()
    conn.executescript("""
        -- Users table
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE NOT NULL,
            display_name TEXT NOT NULL,
            native_lang TEXT DEFAULT 'es',
            target_lang TEXT DEFAULT 'ja',
            xp INTEGER DEFAULT 0,
            level INTEGER DEFAULT 1,
            hearts INTEGER DEFAULT 5,
            streak_days INTEGER DEFAULT 0,
            last_practice_date TEXT,
            created_at TEXT DEFAULT (datetime('now')),
            updated_at TEXT DEFAULT (datetime('now'))
        );

        -- Units (skill tree structure)
        CREATE TABLE IF NOT EXISTS units (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            description TEXT,
            icon TEXT DEFAULT '📚',
            color TEXT DEFAULT '#6366f1',
            sort_order INTEGER DEFAULT 0,
            required_level INTEGER DEFAULT 0,
            created_at TEXT DEFAULT (datetime('now'))
        );

        -- Lessons within units
        CREATE TABLE IF NOT EXISTS lessons (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            unit_id INTEGER REFERENCES units(id),
            name TEXT NOT NULL,
            description TEXT,
            sort_order INTEGER DEFAULT 0,
            xp_reward INTEGER DEFAULT 10,
            is_boss_lesson BOOLEAN DEFAULT 0,
            created_at TEXT DEFAULT (datetime('now'))
        );

        -- Exercises (individual questions)
        CREATE TABLE IF NOT EXISTS exercises (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            lesson_id INTEGER REFERENCES lessons(id),
            exercise_type TEXT NOT NULL,  -- fill_blank, translate, match, listen_type, word_bank, multiple_choice
            question TEXT NOT NULL,
            correct_answer TEXT NOT NULL,
            options TEXT,  -- JSON array for multiple choice/matching
            hint TEXT,
            explanation TEXT,
            audio_text TEXT,  -- text to generate TTS for listening exercises
            sort_order INTEGER DEFAULT 0,
            difficulty INTEGER DEFAULT 1,  -- 1-5
            created_at TEXT DEFAULT (datetime('now'))
        );

        -- User exercise progress
        CREATE TABLE IF NOT EXISTS user_progress (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER REFERENCES users(id),
            exercise_id INTEGER REFERENCES exercises(id),
            is_correct BOOLEAN NOT NULL,
            time_spent_ms INTEGER,
            attempts INTEGER DEFAULT 1,
            practiced_at TEXT DEFAULT (datetime('now'))
        );

        -- Lesson completion tracking
        CREATE TABLE IF NOT EXISTS lesson_progress (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER REFERENCES users(id),
            lesson_id INTEGER REFERENCES lessons(id),
            completed BOOLEAN DEFAULT 0,
            score INTEGER DEFAULT 0,  -- percentage
            hearts_lost INTEGER DEFAULT 0,
            completed_at TEXT,
            created_at TEXT DEFAULT (datetime('now')),
            UNIQUE(user_id, lesson_id)
        );

        -- Streak tracking
        CREATE TABLE IF NOT EXISTS streak_log (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER REFERENCES users(id),
            practice_date TEXT NOT NULL,
            exercises_done INTEGER DEFAULT 0,
            UNIQUE(user_id, practice_date)
        );

        -- Vocabulary tracker
        CREATE TABLE IF NOT EXISTS vocabulary (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER REFERENCES users(id),
            word TEXT NOT NULL,
            translation TEXT NOT NULL,
            source_lang TEXT NOT NULL,
            target_lang TEXT NOT NULL,
            mastery_level INTEGER DEFAULT 0,  -- 0-5 (SRS levels)
            next_review_date TEXT,
            last_reviewed TEXT,
            times_correct INTEGER DEFAULT 0,
            times_wrong INTEGER DEFAULT 0,
            created_at TEXT DEFAULT (datetime('now'))
        );

        -- Indexes for performance
        CREATE INDEX IF NOT EXISTS idx_exercises_lesson ON exercises(lesson_id);
        CREATE INDEX IF NOT EXISTS idx_user_progress_user ON user_progress(user_id);
        CREATE INDEX IF NOT EXISTS idx_user_progress_exercise ON user_progress(exercise_id);
        CREATE INDEX IF NOT EXISTS idx_lesson_progress_user ON lesson_progress(user_id);
        CREATE INDEX IF NOT EXISTS idx_vocabulary_user ON vocabulary(user_id);
        CREATE INDEX IF NOT EXISTS idx_streak_log_user ON streak_log(user_id);
    """)
    conn.commit()
    conn.close()
    print(f"[GrammarDB] Database initialized at {DB_PATH}")


def seed_default_data():
    """Seed database with default units and lessons."""
    conn = get_db()
    
    # Check if already seeded
    count = conn.execute("SELECT COUNT(*) FROM units").fetchone()[0]
    if count > 0:
        conn.close()
        return
    
    # Create default units for Japanese learning
    units = [
        ("Hiragana", "Learn the basic Japanese syllabary", "あ", "#6366f1", 1, 0),
        ("Katakana", "Foreign words and emphasis", "ア", "#8b5cf6", 2, 0),
        ("Greetings", "Basic greetings and politeness", "👋", "#06b6d4", 3, 1),
        ("Self Introduction", "Introduce yourself", "🙋", "#10b981", 4, 2),
        ("Numbers", "Counting and math", "🔢", "#f59e0b", 5, 3),
        ("Food & Drink", "Ordering at restaurants", "🍜", "#ef4444", 6, 4),
        ("Daily Routine", "Talk about your day", "📅", "#3b82f6", 7, 5),
        ("Verbs Basic", "Common action verbs", "🏃", "#ec4899", 8, 6),
    ]
    
    for name, desc, icon, color, order, req_level in units:
        conn.execute(
            "INSERT INTO units (name, description, icon, color, sort_order, required_level) VALUES (?, ?, ?, ?, ?, ?)",
            (name, desc, icon, color, order, req_level)
        )
    
    # Create lessons for Unit 1 (Greetings)
    greeting_lessons = [
        (3, "Hello", "Learn こんにちは and おはよう", 1, 10, 0),
        (3, "Thank You", "Learn ありがとう and どうも", 2, 10, 0),
        (3, "Goodbye", "Learn さようなら and じゃあね", 3, 10, 0),
        (3, "Sorry", "Learn すみません and ごめんなさい", 4, 15, 1),  # boss lesson
    ]
    
    for unit_id, name, desc, order, xp, is_boss in greeting_lessons:
        conn.execute(
            "INSERT INTO lessons (unit_id, name, description, sort_order, xp_reward, is_boss_lesson) VALUES (?, ?, ?, ?, ?, ?)",
            (unit_id, name, desc, order, xp, is_boss)
        )
    
    # Create exercises for Lesson 1 (Hello)
    exercises = [
        (1, "multiple_choice", "How do you say 'Good morning' in Japanese?", "おはようございます", 
         json.dumps(["こんにちは", "おはようございます", "ありがとう", "さようなら"]),
         "Used before 10 AM", "おはようございます (ohayou gozaimasu) is the polite form of good morning.", "おはようございます", 1, 1),
        (1, "fill_blank", "Complete: こ___ちは", "んにち",
         None, "This is the most common greeting", "こんにちは (konnichiwa) means hello/good afternoon", None, 2, 1),
        (1, "translate", "Translate to Japanese: 'How are you?'", "お元気ですか",
         None, "Polite form asking about wellbeing", "元気 (genki) = healthy/well, ですか = is it?", None, 3, 1),
        (1, "word_bank", "Arrange: are you? good how", "お元気ですか",
         json.dumps(["ですか", "お元気", "が", "すき"]),
         "Put the words in correct order", "Word order: Topic + ですか", None, 4, 2),
    ]
    
    for lesson_id, etype, question, answer, options, hint, explanation, audio, order, diff in exercises:
        conn.execute(
            "INSERT INTO exercises (lesson_id, exercise_type, question, correct_answer, options, hint, explanation, audio_text, sort_order, difficulty) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (lesson_id, etype, question, answer, options, hint, explanation, audio, order, diff)
        )
    
    conn.commit()
    conn.close()
    print("[GrammarDB] Default data seeded")


# ── User Operations ─────────────────────────────────────
def create_user(username, display_name, native_lang='es', target_lang='ja'):
    conn = get_db()
    try:
        conn.execute(
            "INSERT INTO users (username, display_name, native_lang, target_lang) VALUES (?, ?, ?, ?)",
            (username, display_name, native_lang, target_lang)
        )
        conn.commit()
        user_id = conn.execute("SELECT last_insert_rowid()").fetchone()[0]
        return user_id
    except sqlite3.IntegrityError:
        return None
    finally:
        conn.close()


def get_user(user_id):
    conn = get_db()
    user = conn.execute("SELECT * FROM users WHERE id = ?", (user_id,)).fetchone()
    conn.close()
    return dict(user) if user else None


def get_user_by_username(username):
    conn = get_db()
    user = conn.execute("SELECT * FROM users WHERE username = ?", (username,)).fetchone()
    conn.close()
    return dict(user) if user else None


def update_user_xp(user_id, xp_gain):
    conn = get_db()
    conn.execute("UPDATE users SET xp = xp + ?, level = ((xp + ?) / 100) + 1, updated_at = datetime('now') WHERE id = ?", (xp_gain, xp_gain, user_id))
    conn.commit()
    conn.close()


def use_heart(user_id):
    """Use one heart. Returns False if no hearts left."""
    conn = get_db()
    user = conn.execute("SELECT hearts FROM users WHERE id = ?", (user_id,)).fetchone()
    if not user or user['hearts'] <= 0:
        conn.close()
        return False
    conn.execute("UPDATE users SET hearts = hearts - 1 WHERE id = ?", (user_id,))
    conn.commit()
    conn.close()
    return True


def recharge_hearts(user_id, amount=5):
    conn = get_db()
    conn.execute("UPDATE users SET hearts = MIN(hearts + ?, 5) WHERE id = ?", (amount, user_id))
    conn.commit()
    conn.close()


# ── Streak Operations ───────────────────────────────────
def update_streak(user_id):
    """Update streak. Returns current streak count."""
    conn = get_db()
    today = datetime.now().strftime('%Y-%m-%d')
    yesterday = (datetime.now() - timedelta(days=1)).strftime('%Y-%m-%d')
    
    # Check if already practiced today
    existing = conn.execute("SELECT id FROM streak_log WHERE user_id = ? AND practice_date = ?", (user_id, today)).fetchone()
    if existing:
        conn.close()
        user = get_user(user_id)
        return user['streak_days'] if user else 0
    
    # Check yesterday's streak
    yesterday_log = conn.execute("SELECT id FROM streak_log WHERE user_id = ? AND practice_date = ?", (user_id, yesterday)).fetchone()
    
    if yesterday_log:
        # Continue streak
        conn.execute("UPDATE users SET streak_days = streak_days + 1, last_practice_date = ? WHERE id = ?", (today, user_id))
    else:
        # Streak broken, restart
        conn.execute("UPDATE users SET streak_days = 1, last_practice_date = ? WHERE id = ?", (today, user_id))
    
    conn.execute("INSERT INTO streak_log (user_id, practice_date, exercises_done) VALUES (?, ?, 1)", (user_id, today))
    conn.commit()
    
    user = get_user(user_id)
    conn.close()
    return user['streak_days'] if user else 0


# ── Progress Operations ─────────────────────────────────
def record_exercise_result(user_id, exercise_id, is_correct, time_spent_ms=0):
    conn = get_db()
    conn.execute(
        "INSERT INTO user_progress (user_id, exercise_id, is_correct, time_spent_ms) VALUES (?, ?, ?, ?)",
        (user_id, exercise_id, is_correct, time_spent_ms)
    )
    
    if is_correct:
        # Award 10 XP per correct exercise
        conn.execute("UPDATE users SET xp = xp + 10, level = ((xp + 10) / 100) + 1, updated_at = datetime('now') WHERE id = ?", (user_id,))
    
    conn.commit()
    conn.close()


def get_lesson_exercises(lesson_id):
    conn = get_db()
    exercises = conn.execute("SELECT * FROM exercises WHERE lesson_id = ? ORDER BY sort_order", (lesson_id,)).fetchall()
    conn.close()
    return [dict(e) for e in exercises]


def get_user_stats(user_id):
    conn = get_db()
    stats = {}
    
    user = conn.execute("SELECT * FROM users WHERE id = ?", (user_id,)).fetchone()
    if user:
        stats['user'] = dict(user)
    
    # Total exercises completed
    total = conn.execute("SELECT COUNT(*) FROM user_progress WHERE user_id = ?", (user_id,)).fetchone()[0]
    correct = conn.execute("SELECT COUNT(*) FROM user_progress WHERE user_id = ? AND is_correct = 1", (user_id,)).fetchone()[0]
    stats['total_exercises'] = total
    stats['correct_exercises'] = correct
    stats['accuracy'] = round(correct / total * 100, 1) if total > 0 else 0
    
    # Lessons completed
    stats['lessons_completed'] = conn.execute(
        "SELECT COUNT(*) FROM lesson_progress WHERE user_id = ? AND completed = 1", (user_id,)
    ).fetchone()[0]
    
    # Vocabulary count
    stats['vocabulary_count'] = conn.execute(
        "SELECT COUNT(*) FROM vocabulary WHERE user_id = ?", (user_id,)
    ).fetchone()[0]
    
    # Weekly activity
    week_ago = (datetime.now() - timedelta(days=7)).strftime('%Y-%m-%d')
    stats['weekly_practice'] = conn.execute(
        "SELECT SUM(exercises_done) FROM streak_log WHERE user_id = ? AND practice_date >= ?",
        (user_id, week_ago)
    ).fetchone()[0] or 0
    
    conn.close()
    return stats


# ── Vocabulary Operations (SRS) ────────────────────────
def add_vocabulary(user_id, word, translation, source_lang, target_lang):
    conn = get_db()
    conn.execute(
        "INSERT INTO vocabulary (user_id, word, translation, source_lang, target_lang, next_review_date) VALUES (?, ?, ?, ?, ?, date('now'))",
        (user_id, word, translation, source_lang, target_lang)
    )
    conn.commit()
    conn.close()


def get_review_vocab(user_id, limit=10):
    """Get vocabulary due for review (SRS)."""
    conn = get_db()
    today = datetime.now().strftime('%Y-%m-%d')
    vocab = conn.execute(
        "SELECT * FROM vocabulary WHERE user_id = ? AND next_review_date <= ? ORDER BY next_review_date LIMIT ?",
        (user_id, today, limit)
    ).fetchall()
    conn.close()
    return [dict(v) for v in vocab]


def update_vocab_mastery(vocab_id, correct):
    """Update SRS mastery level."""
    conn = get_db()
    if correct:
        conn.execute("""
            UPDATE vocabulary SET 
                mastery_level = MIN(mastery_level + 1, 5),
                times_correct = times_correct + 1,
                next_review_date = date('now', '+' || (mastery_level * 2) || ' days'),
                last_reviewed = datetime('now')
            WHERE id = ?
        """, (vocab_id,))
    else:
        conn.execute("""
            UPDATE vocabulary SET 
                mastery_level = MAX(mastery_level - 1, 0),
                times_wrong = times_wrong + 1,
                next_review_date = date('now', '+1 day'),
                last_reviewed = datetime('now')
            WHERE id = ?
        """, (vocab_id,))
    conn.commit()
    conn.close()


# ── Leaderboard ─────────────────────────────────────────
def get_leaderboard(limit=10):
    conn = get_db()
    users = conn.execute(
        "SELECT id, username, display_name, xp, level, streak_days FROM users ORDER BY xp DESC LIMIT ?",
        (limit,)
    ).fetchall()
    conn.close()
    return [dict(u) for u in users]


if __name__ == "__main__":
    init_db()
    seed_default_data()
    print("[GrammarDB] Ready!")
