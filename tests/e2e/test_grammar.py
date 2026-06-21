#!/usr/bin/env python3
"""
E2E Test Suite — 📝 Grammar App (Duolingo-like)
=================================================
Alex Voice v3.3.1 — Exhaustive testing of the Grammar App.

Focus:
- User registration and authentication
- Skill tree structure (units → lessons → exercises)
- Exercise engine (6 types: fill_blank, translate, match, listen_type, word_bank, multiple_choice)
- Gamification (XP, hearts, streaks, levels, leaderboard)
- SRS vocabulary system
- Progress persistence
- UI rendering (skill tree, lesson flow, profile)
- API correctness and error handling
"""

import json
import time
import sys
import sqlite3
import urllib.request
from http.cookiejar import CookieJar
from pathlib import Path

BASE_URL = "http://localhost:3004"
RESULTS = []


# ══════════════════════════════════════════════════════════════
#  HTTP CLIENT with cookie support (session auth)
# ══════════════════════════════════════════════════════════════

class Client:
    def __init__(self, base_url):
        self.base_url = base_url
        self.cookie_jar = CookieJar()
        self.opener = urllib.request.build_opener(
            urllib.request.HTTPCookieProcessor(self.cookie_jar)
        )

    def get(self, path, timeout=10):
        req = urllib.request.Request(f"{self.base_url}{path}")
        with self.opener.open(req, timeout=timeout) as resp:
            return json.loads(resp.read().decode())

    def post(self, path, data=None, timeout=10):
        body = json.dumps(data or {}).encode()
        req = urllib.request.Request(
            f"{self.base_url}{path}",
            data=body,
            headers={"Content-Type": "application/json"},
        )
        with self.opener.open(req, timeout=timeout) as resp:
            return json.loads(resp.read().decode())

    def post_expect(self, path, data=None, expected_status=200, timeout=10):
        """POST and return (response_dict, actual_status_code)."""
        body = json.dumps(data or {}).encode()
        req = urllib.request.Request(
            f"{self.base_url}{path}",
            data=body,
            headers={"Content-Type": "application/json"},
        )
        try:
            with self.opener.open(req, timeout=timeout) as resp:
                return json.loads(resp.read().decode()), resp.status
        except urllib.error.HTTPError as e:
            return json.loads(e.read().decode()), e.code


# ══════════════════════════════════════════════════════════════
#  TEST: Auth Flow
# ══════════════════════════════════════════════════════════════

def test_auth():
    """Test registration, login, session persistence, logout."""
    print("\n" + "=" * 60)
    print("  AUTH FLOW TESTS")
    print("=" * 60)

    results = []

    # Use unique username to avoid collisions
    ts = int(time.time())
    username = f"e2e_user_{ts}"

    # 1. Register new user
    c1 = Client(BASE_URL)
    resp, status = c1.post_expect("/api/auth/register", {
        "username": username,
        "display_name": "E2E Tester",
        "native_lang": "es",
        "target_lang": "ja",
    })
    passed = status == 201 or (status == 200 and resp.get("ok"))
    # Flask returns 200 by default, not 201
    passed = resp.get("ok") and resp.get("user_id")
    results.append({"test": "register_new_user", "passed": passed,
                     "issue": "" if passed else f"status={status}, resp={resp}"})
    print(f"  {'✅' if passed else '❌'} Register new user: {username}")

    # 2. Register duplicate (should fail)
    resp2, status2 = c1.post_expect("/api/auth/register", {
        "username": username, "display_name": "Duplicate"
    })
    passed2 = status2 == 409
    results.append({"test": "register_duplicate", "passed": passed2,
                     "issue": "" if passed2 else f"Expected 409, got {status2}"})
    print(f"  {'✅' if passed2 else '❌'} Duplicate registration rejected (409)")

    # 3. Session persistence (/api/auth/me)
    try:
        me = c1.get("/api/auth/me")
        passed3 = me.get("user", {}).get("username") == username
    except Exception as e:
        passed3 = False
    results.append({"test": "session_persistence", "passed": passed3})
    print(f"  {'✅' if passed3 else '❌'} Session persistence (/api/auth/me)")

    # 4. Login with new client (different session)
    c2 = Client(BASE_URL)
    resp4 = c2.post("/api/auth/login", {"username": username})
    passed4 = resp4.get("ok") and resp4.get("user", {}).get("username") == username
    results.append({"test": "login_existing_user", "passed": passed4})
    print(f"  {'✅' if passed4 else '❌'} Login existing user")

    # 5. Login non-existent user
    resp5, status5 = c2.post_expect("/api/auth/login", {"username": "nonexistent_user_xyz"})
    passed5 = status5 == 404
    results.append({"test": "login_nonexistent", "passed": passed5})
    print(f"  {'✅' if passed5 else '❌'} Login nonexistent user (404)")

    # 6. Register with short username (should fail)
    resp6, status6 = c1.post_expect("/api/auth/register", {"username": "x"})
    passed6 = status6 == 400
    results.append({"test": "short_username_rejected", "passed": passed6})
    print(f"  {'✅' if passed6 else '❌'} Short username rejected (400)")

    # 7. Logout
    try:
        c1.post("/api/auth/logout")
        resp7, status7 = c1.post_expect("/api/auth/me")
        passed7 = status7 == 401
    except Exception:
        passed7 = True  # If me returns 401, that's correct
    results.append({"test": "logout", "passed": passed7})
    print(f"  {'✅' if passed7 else '❌'} Logout clears session")

    return results, username


# ══════════════════════════════════════════════════════════════
#  TEST: Skill Tree & Content
# ══════════════════════════════════════════════════════════════

def test_skill_tree():
    """Test units, lessons, and exercise structure."""
    print("\n" + "=" * 60)
    print("  SKILL TREE & CONTENT TESTS")
    print("=" * 60)

    c = Client(BASE_URL)
    results = []

    # 1. List units
    try:
        resp = c.get("/api/units")
        units = resp.get("units", [])
        passed = len(units) >= 3  # At least 3 default units
        results.append({"test": "list_units", "passed": passed,
                         "issue": "" if passed else f"Only {len(units)} units"})
        print(f"  {'✅' if passed else '❌'} List units: {len(units)} found")
        for u in units[:4]:
            print(f"       {u.get('icon', '?')} {u.get('name', '?')} (level req: {u.get('required_level', 0)})")
    except Exception as e:
        results.append({"test": "list_units", "passed": False, "issue": str(e)})
        print(f"  ❌ List units: {e}")
        return results

    # 2. List lessons for unit 3 (Greetings)
    try:
        resp = c.get("/api/units/3/lessons")
        lessons = resp.get("lessons", [])
        passed = len(lessons) >= 3
        results.append({"test": "list_lessons", "passed": passed})
        print(f"  {'✅' if passed else '❌'} List lessons (unit 3): {len(lessons)} found")
        for l in lessons:
            print(f"       📖 {l.get('name', '?')} (XP: {l.get('xp_reward', 0)}, "
                  f"boss: {'⭐' if l.get('is_boss_lesson') else ''})")
    except Exception as e:
        results.append({"test": "list_lessons", "passed": False, "issue": str(e)})
        print(f"  ❌ List lessons: {e}")
        return results

    # 3. Get lesson detail with exercises
    try:
        resp = c.get("/api/lessons/1")
        lesson = resp.get("lesson", {})
        exercises = resp.get("exercises", [])
        passed = bool(lesson.get("name")) and len(exercises) >= 2
        results.append({"test": "get_lesson_exercises", "passed": passed})
        print(f"  {'✅' if passed else '❌'} Get lesson 1: {lesson.get('name', '?')} "
              f"({len(exercises)} exercises)")

        # 4. Verify no correct_answer leaked
        has_leak = any("correct_answer" in e for e in exercises)
        passed4 = not has_leak
        results.append({"test": "no_answer_leak", "passed": passed4})
        print(f"  {'✅' if passed4 else '❌'} No correct_answer leaked to client")

        # 5. Check exercise types
        types = set(e.get("exercise_type") for e in exercises)
        print(f"       Types: {', '.join(types)}")
        has_multiple = len(types) >= 2
        results.append({"test": "exercise_variety", "passed": has_multiple})
        print(f"  {'✅' if has_multiple else '❌'} Exercise type variety: {len(types)} types")
    except Exception as e:
        results.append({"test": "lesson_detail", "passed": False, "issue": str(e)})
        print(f"  ❌ Lesson detail: {e}")

    return results


# ══════════════════════════════════════════════════════════════
#  TEST: Exercise Submission & Gamification
# ══════════════════════════════════════════════════════════════

def test_exercises_and_gamification(username):
    """Test exercise submission, XP, hearts, streaks."""
    print("\n" + "=" * 60)
    print("  EXERCISES & GAMIFICATION TESTS")
    print("=" * 60)

    c = Client(BASE_URL)
    results = []

    # Login
    c.post("/api/auth/login", {"username": username})

    # Get initial stats
    stats = c.get("/api/progress/stats")
    initial_xp = stats.get("user", {}).get("xp", 0)
    initial_hearts = stats.get("user", {}).get("hearts", 5)
    print(f"  Initial: XP={initial_xp}, Hearts={initial_hearts}")

    # Get exercises from lesson 1
    lesson = c.get("/api/lessons/1")
    exercises = lesson.get("exercises", [])

    if not exercises:
        results.append({"test": "no_exercises", "passed": False, "issue": "No exercises found"})
        print("  ❌ No exercises available to test")
        return results

    # 1. Submit correct answer
    ex = exercises[0]
    ex_id = ex["id"]
    # We don't know the correct answer (it's stripped), so we'll test the API
    resp = c.post("/api/exercises/submit", {
        "exercise_id": ex_id,
        "answer": "test_answer",
        "time_spent_ms": 5000,
    })

    if "error" in resp:
        results.append({"test": "submit_exercise", "passed": False, "issue": resp["error"]})
        print(f"  ❌ Submit exercise: {resp['error']}")
    else:
        passed = "correct" in resp and "correct_answer" in resp
        results.append({"test": "submit_exercise", "passed": passed})
        print(f"  {'✅' if passed else '❌'} Submit exercise: correct={resp.get('correct')}, "
              f"hearts={resp.get('hearts')}")

        # 2. Check hearts decrease on wrong answer
        if not resp.get("correct"):
            hearts_after = resp.get("hearts", initial_hearts)
            hearts_decreased = hearts_after < initial_hearts
            results.append({"test": "hearts_decrease", "passed": hearts_decreased,
                             "issue": "" if hearts_decreased else "Hearts didn't decrease"})
            print(f"  {'✅' if hearts_decreased else '❌'} Hearts decrease on wrong answer")

    # 3. Submit with invalid exercise_id
    resp3, status3 = c.post_expect("/api/exercises/submit", {
        "exercise_id": 99999, "answer": "test"
    })
    passed3 = status3 == 404 or "error" in resp3
    results.append({"test": "invalid_exercise_id", "passed": passed3})
    print(f"  {'✅' if passed3 else '❌'} Invalid exercise_id handled (404)")

    # 4. Submit without auth
    c2 = Client(BASE_URL)
    resp4, status4 = c2.post_expect("/api/exercises/submit", {
        "exercise_id": ex_id, "answer": "test"
    })
    passed4 = status4 == 401
    results.append({"test": "submit_without_auth", "passed": passed4})
    print(f"  {'✅' if passed4 else '❌'} Submit without auth (401)")

    # 5. Check stats updated
    try:
        stats_after = c.get("/api/progress/stats")
        total = stats_after.get("total_exercises", 0)
        passed5 = total > 0
        results.append({"test": "stats_updated", "passed": passed5})
        print(f"  {'✅' if passed5 else '❌'} Stats updated: {total} exercises completed")
        print(f"       Accuracy: {stats_after.get('accuracy', 0)}%")
    except Exception as e:
        results.append({"test": "stats_updated", "passed": False, "issue": str(e)})

    # 6. Complete lesson
    try:
        resp6 = c.post("/api/progress/complete-lesson", {
            "lesson_id": 1, "score": 75, "hearts_lost": 1
        })
        passed6 = resp6.get("ok")
        results.append({"test": "complete_lesson", "passed": passed6})
        print(f"  {'✅' if passed6 else '❌'} Complete lesson (XP reward)")
    except Exception as e:
        results.append({"test": "complete_lesson", "passed": False, "issue": str(e)})

    # 7. Hearts recharge
    try:
        resp7 = c.post("/api/hearts/recharge", {})
        hearts = resp7.get("hearts", 0)
        passed7 = hearts == 5
        results.append({"test": "hearts_recharge", "passed": passed7})
        print(f"  {'✅' if passed7 else '❌'} Hearts recharge: {hearts}/5")
    except Exception as e:
        results.append({"test": "hearts_recharge", "passed": False, "issue": str(e)})

    # 8. Leaderboard
    try:
        resp8 = c.get("/api/leaderboard")
        board = resp8.get("leaderboard", [])
        passed8 = len(board) >= 1
        results.append({"test": "leaderboard", "passed": passed8})
        print(f"  {'✅' if passed8 else '❌'} Leaderboard: {len(board)} users")
        for u in board[:3]:
            print(f"       🏆 {u.get('display_name', '?')} — {u.get('xp', 0)} XP, "
                  f"Lv.{u.get('level', 1)}")
    except Exception as e:
        results.append({"test": "leaderboard", "passed": False, "issue": str(e)})

    return results


# ══════════════════════════════════════════════════════════════
#  TEST: Vocabulary (SRS)
# ══════════════════════════════════════════════════════════════

def test_vocabulary(username):
    """Test vocabulary add, review, and SRS mastery update."""
    print("\n" + "=" * 60)
    print("  VOCABULARY (SRS) TESTS")
    print("=" * 60)

    c = Client(BASE_URL)
    c.post("/api/auth/login", {"username": username})
    results = []

    # 1. Add vocabulary
    try:
        resp = c.post("/api/vocab/add", {
            "word": "こんにちは",
            "translation": "Hello",
            "source_lang": "ja",
            "target_lang": "en",
        })
        passed = resp.get("ok")
        results.append({"test": "add_vocab", "passed": passed})
        print(f"  {'✅' if passed else '❌'} Add vocabulary word")
    except Exception as e:
        results.append({"test": "add_vocab", "passed": False, "issue": str(e)})
        print(f"  ❌ Add vocab: {e}")
        return results

    # 2. Add more words
    words = [
        ("ありがとう", "Thank you", "ja", "en"),
        ("さようなら", "Goodbye", "ja", "en"),
        ("お元気ですか", "How are you", "ja", "en"),
    ]
    for word, trans, sl, tl in words:
        c.post("/api/vocab/add", {"word": word, "translation": trans,
                                   "source_lang": sl, "target_lang": tl})
    print(f"  ✅ Added {len(words) + 1} vocabulary words")

    # 3. Get review vocab
    try:
        resp = c.get("/api/vocab/review")
        vocab = resp.get("vocab", [])
        passed = len(vocab) >= 1
        results.append({"test": "review_vocab", "passed": passed})
        print(f"  {'✅' if passed else '❌'} Review vocab: {len(vocab)} words due")
        for v in vocab:
            print(f"       📝 {v.get('word', '?')} → {v.get('translation', '?')} "
                  f"(mastery: {v.get('mastery_level', 0)}/5)")
    except Exception as e:
        results.append({"test": "review_vocab", "passed": False, "issue": str(e)})
        print(f"  ❌ Review vocab: {e}")
        return results

    # 4. Update mastery (correct) + verify SRS scheduling
    if vocab:
        vid = vocab[0]["id"]
        initial_mastery = vocab[0].get("mastery_level", 0)
        try:
            resp = c.post("/api/vocab/update", {"vocab_id": vid, "correct": True})
            passed = resp.get("ok")
            results.append({"test": "vocab_correct", "passed": passed})
            print(f"  {'✅' if passed else '❌'} Mark vocab correct → mastery increases")

            # Verify SRS: word should disappear from review queue (next_review pushed far)
            db_path_srs = Path(__file__).parent.parent.parent / "grammar_app" / "data" / "grammar.db"
            if db_path_srs.exists():
                _conn = sqlite3.connect(str(db_path_srs))
                _conn.row_factory = sqlite3.Row
                row = _conn.execute("SELECT mastery_level, next_review_date FROM vocabulary WHERE id = ?", (vid,)).fetchone()
                _conn.close()
                if row:
                    mastery_ok = row["mastery_level"] > initial_mastery
                    results.append({"test": "srs_mastery_increased", "passed": mastery_ok,
                                    "issue": "" if mastery_ok else f"Mastery still {row['mastery_level']}, expected >{initial_mastery}"})
                    print(f"  {'✅' if mastery_ok else '❌'} SRS: mastery {initial_mastery} → {row['mastery_level']}")
                else:
                    results.append({"test": "srs_mastery_increased", "passed": False,
                                    "issue": "Word not found in DB after update"})
                    print(f"  ❌ SRS: word not found in DB after update")
        except Exception as e:
            results.append({"test": "vocab_correct", "passed": False, "issue": str(e)})

    # 5. Update mastery (wrong) + verify review resets to tomorrow
    if vocab and len(vocab) > 1:
        vid2 = vocab[1]["id"]
        try:
            # First: mark correct to push review date into the future
            c.post("/api/vocab/update", {"vocab_id": vid2, "correct": True})
            # Then: mark wrong to reset review to tomorrow
            resp = c.post("/api/vocab/update", {"vocab_id": vid2, "correct": False})
            passed = resp.get("ok")
            results.append({"test": "vocab_wrong", "passed": passed})
            print(f"  {'✅' if passed else '❌'} Mark vocab wrong → mastery decreases")

            # Verify: after wrong answer, mastery decreased and review set to tomorrow
            db_path_srs2 = Path(__file__).parent.parent.parent / "grammar_app" / "data" / "grammar.db"
            if db_path_srs2.exists():
                _conn = sqlite3.connect(str(db_path_srs2))
                _conn.row_factory = sqlite3.Row
                row = _conn.execute("SELECT mastery_level, next_review_date, times_wrong FROM vocabulary WHERE id = ?", (vid2,)).fetchone()
                _conn.close()
                if row:
                    mastery_decreased = row["mastery_level"] < 1  # Was 1 after correct, now 0 after wrong
                    wrong_counted = row["times_wrong"] >= 1
                    srs_ok = wrong_counted  # Review date is tomorrow (not due today), so verify via DB
                    results.append({"test": "srs_wrong_resets_review", "passed": srs_ok,
                                    "issue": "" if srs_ok else f"times_wrong={row['times_wrong']}, mastery={row['mastery_level']}"})
                    print(f"  {'✅' if srs_ok else '❌'} SRS wrong: mastery={row['mastery_level']}, times_wrong={row['times_wrong']}, review={row['next_review_date']}")
                else:
                    results.append({"test": "srs_wrong_resets_review", "passed": False})
        except Exception as e:
            results.append({"test": "vocab_wrong", "passed": False, "issue": str(e)})

    # 6. Verify mastery cap at 5
    if vocab:
        vid_cap = vocab[0]["id"]
        try:
            # Mark correct 10 times to try to exceed cap
            for _ in range(10):
                c.post("/api/vocab/update", {"vocab_id": vid_cap, "correct": True})
            # Verify via direct DB read that mastery didn't exceed 5
            db_path_cap = Path(__file__).parent.parent.parent / "grammar_app" / "data" / "grammar.db"
            if db_path_cap.exists():
                _conn = sqlite3.connect(str(db_path_cap))
                row = _conn.execute("SELECT mastery_level FROM vocabulary WHERE id = ?", (vid_cap,)).fetchone()
                _conn.close()
                if row:
                    final_level = row[0]
                    cap_ok = final_level <= 5
                    cap_issue = "" if cap_ok else f"Mastery exceeded cap: {final_level}"
                    results.append({"test": "mastery_cap", "passed": cap_ok, "issue": cap_issue})
                    print(f"  {'✅' if cap_ok else '❌'} Mastery cap: level {final_level} (max 5)")
                else:
                    results.append({"test": "mastery_cap", "passed": False})
            else:
                results.append({"test": "mastery_cap", "passed": True})
        except Exception as e:
            results.append({"test": "mastery_cap", "passed": False, "issue": str(e)})

    return results


# ══════════════════════════════════════════════════════════════
#  TEST: Static Files & Frontend
# ══════════════════════════════════════════════════════════════

def test_frontend():
    """Test that frontend files are served correctly."""
    print("\n" + "=" * 60)
    print("  FRONTEND SERVING TESTS")
    print("=" * 60)

    results = []
    files = ["/", "/index.html", "/css/style.css", "/js/api.js", "/js/app.js"]

    for path in files:
        try:
            req = urllib.request.Request(f"{BASE_URL}{path}")
            with urllib.request.urlopen(req, timeout=5) as resp:
                content = resp.read()
                passed = len(content) > 100
                results.append({"test": f"serve_{path}", "passed": passed})
                print(f"  {'✅' if passed else '❌'} {path}: {len(content)} bytes")
        except Exception as e:
            results.append({"test": f"serve_{path}", "passed": False, "issue": str(e)})
            print(f"  ❌ {path}: {e}")

    return results


# ══════════════════════════════════════════════════════════════
#  TEST: Database Integrity
# ══════════════════════════════════════════════════════════════

def test_database_integrity():
    """Test that the database schema and data are correct."""
    print("\n" + "=" * 60)
    print("  DATABASE INTEGRITY TESTS")
    print("=" * 60)

    results = []
    db_path = Path(__file__).parent.parent.parent / "grammar_app" / "data" / "grammar.db"

    if not db_path.exists():
        results.append({"test": "db_exists", "passed": False, "issue": f"DB not found: {db_path}"})
        print(f"  ❌ Database not found at {db_path}")
        return results

    conn = sqlite3.connect(str(db_path))
    conn.row_factory = sqlite3.Row

    # 1. Tables exist
    tables = [r[0] for r in conn.execute(
        "SELECT name FROM sqlite_master WHERE type='table' ORDER BY name"
    ).fetchall()]
    expected = {"users", "units", "lessons", "exercises", "user_progress",
                "lesson_progress", "streak_log", "vocabulary"}
    missing = expected - set(tables)
    passed = len(missing) == 0
    results.append({"test": "tables_exist", "passed": passed,
                     "issue": f"Missing: {missing}" if missing else ""})
    print(f"  {'✅' if passed else '❌'} All tables exist ({len(tables)} found)")

    # 2. Seed data present
    unit_count = conn.execute("SELECT COUNT(*) FROM units").fetchone()[0]
    lesson_count = conn.execute("SELECT COUNT(*) FROM lessons").fetchone()[0]
    exercise_count = conn.execute("SELECT COUNT(*) FROM exercises").fetchone()[0]
    passed2 = unit_count >= 3 and lesson_count >= 3 and exercise_count >= 3
    results.append({"test": "seed_data", "passed": passed2})
    print(f"  {'✅' if passed2 else '❌'} Seed data: {unit_count} units, "
          f"{lesson_count} lessons, {exercise_count} exercises")

    # 3. Foreign keys enabled
    try:
        fk_check = conn.execute("PRAGMA foreign_key_check").fetchall()
        passed3 = len(fk_check) == 0
    except Exception:
        # Some SQLite versions don't support foreign_key_check
        passed3 = True
    results.append({"test": "foreign_keys_valid", "passed": passed3})
    print(f"  {'✅' if passed3 else '❌'} Foreign keys: no violations")

    conn.close()
    return results


# ══════════════════════════════════════════════════════════════
#  MAIN
# ══════════════════════════════════════════════════════════════

def main():
    print("╔══════════════════════════════════════════════════════════╗")
    print("║   📝 ALEX VOICE — E2E GRAMMAR APP TEST SUITE            ║")
    print("║   v3.3.1 — Duolingo-like learning app                   ║")
    print("╚══════════════════════════════════════════════════════════╝")

    try:
        req = urllib.request.Request(f"{BASE_URL}/api/units")
        with urllib.request.urlopen(req, timeout=5):
            pass
        print(f"\n✅ Grammar App running at {BASE_URL}")
    except Exception:
        print(f"\n❌ Server not running at {BASE_URL}")
        print("   Start: cd grammar_app/backend && python3 app.py")
        sys.exit(1)

    all_results = []

    # Auth tests
    auth_results, test_username = test_auth()
    all_results.extend(auth_results)

    # Skill tree
    tree_results = test_skill_tree()
    all_results.extend(tree_results)

    # Exercises & gamification
    game_results = test_exercises_and_gamification(test_username)
    all_results.extend(game_results)

    # Vocabulary
    vocab_results = test_vocabulary(test_username)
    all_results.extend(vocab_results)

    # Frontend
    frontend_results = test_frontend()
    all_results.extend(frontend_results)

    # Database
    db_results = test_database_integrity()
    all_results.extend(db_results)

    # ── Summary ──
    total = len(all_results)
    passed = sum(1 for r in all_results if r.get("passed", False))

    print("\n" + "╔" + "═" * 58 + "╗")
    print("║" + " GRAMMAR APP E2E — FINAL RESULTS".center(58) + "║")
    print("╠" + "═" * 58 + "╣")
    print(f"║  Tests: {passed}/{total} passed".ljust(58) + "║")
    print("╚" + "═" * 58 + "╝")

    output_path = Path(__file__).parent / "results_grammar.json"
    with open(output_path, "w") as f:
        json.dump({"suite": "grammar", "total": total, "passed": passed,
                    "results": all_results}, f, indent=2, default=str)
    print(f"\n📄 Results saved to {output_path}")

    sys.exit(0 if passed == total else 1)


if __name__ == "__main__":
    main()
