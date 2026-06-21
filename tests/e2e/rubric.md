# 📊 E2E Test Rubric — Alex Voice v3.3.1
# =========================================
# Scoring criteria for each subproject.
# Each test is scored 0-10. Minimum passing score varies by category.
# Tests are run FROM each of the 3 source languages (ES, EN, JA).

## Global Criteria (applies to ALL subprojects)

| # | Criterion | Weight | Description |
|---|-----------|--------|-------------|
| 1 | **API Availability** | 2x | Server responds to health check within 5s |
| 2 | **Error Handling** | 1x | Invalid inputs return proper error codes (400/401/404) |
| 3 | **No Crashes** | 3x | Server stays alive through all test scenarios |
| 4 | **Response Validity** | 2x | All responses are valid JSON with expected fields |
| 5 | **Latency Budget** | 2x | All operations complete within specified timeouts |

---

## 🎓 Teacher Mode — Rubric

### Output Quality (30%)
| Criterion | Score | Pass Threshold | What to Check |
|-----------|-------|----------------|---------------|
| Multi-output format | /10 | ≥8 | All 6 fields present: TEXT, TTS_READING, PRONUNCIATION, TRANSLATION, EXPLANATION, EXERCISE |
| No emojis in output | /10 | 10 (zero tolerance) | Zero Unicode emojis in any field |
| Word spacing (joinwords fix) | /10 | ≥9 | No concatenated words: "Sensei,ohayōgozaimasu" ❌ → "Sensei, ohayō gozaimasu" ✅ |
| Language correctness | /10 | ≥9 | TEXT field is in the TARGET language, not source |
| TTS_READING in Latin script | /10 | 10 | Japanese romaji uses macrons (ō, ū), no CJK in TTS_READING |

### Explanation Quality (25%)
| Criterion | Score | Pass Threshold | What to Check |
|-----------|-------|----------------|---------------|
| Grammar accuracy | /10 | ≥9 | Grammatical explanations are factually correct |
| Cultural context | /10 | ≥7 | Japanese examples include cultural notes (formality, etiquette) |
| Examples count | /10 | ≥7 | At least 3 concrete examples per explanation |
| Clarity for beginners | /10 | ≥8 | Vocabulary is simple, concepts are explained step-by-step |

### Translation Accuracy (20%)
| Criterion | Score | Pass Threshold | What to Check |
|-----------|-------|----------------|---------------|
| ES→JA accuracy | /10 | ≥7 | Spanish phrases translated correctly to Japanese |
| EN→JA accuracy | /10 | ≥7 | English phrases translated correctly to Japanese |
| JA→ES accuracy | /10 | ≥7 | Japanese phrases translated correctly to Spanish |
| Idiom handling | /10 | ≥6 | Cultural idioms are translated to equivalents, not literal |
| Formality levels | /10 | ≥8 | Both formal and casual versions provided when asked |

### System Performance (15%)
| Criterion | Score | Pass Threshold | What to Check |
|-----------|-------|----------------|---------------|
| LLM latency (first token) | /10 | ≥7 | <15s cold start, <5s warm |
| TTS latency | /10 | ≥8 | <8s for short text, <15s for long sequential TTS |
| Cache hit speedup | /10 | ≥8 | Cached responses are ≥3x faster |
| VRAM stability | /10 | ≥8 | VRAM doesn't grow >500MB across test run |
| Memory leaks | /10 | ≥9 | No orphaned processes or memory growth |

---

## 💬 Conversation Mode — Rubric

### Natural Conversation (35%)
| Criterion | Score | Pass Threshold | What to Check |
|-----------|-------|----------------|---------------|
| Language matching | /10 | 10 | Responds in EXACTLY the same language as user |
| Natural tone | /10 | ≥8 | Feels like talking to a person, not a chatbot |
| Opinion expression | /10 | ≥7 | Expresses personal opinions ("I think...", "I prefer...") |
| Follow-up questions | /10 | ≥7 | Asks questions to continue the conversation |
| Emotional intelligence | /10 | ≥7 | Responds empathetically to emotional messages |

### Context Memory (20%)
| Criterion | Score | Pass Threshold | What to Check |
|-----------|-------|----------------|---------------|
| Name recall | /10 | 10 | Remembers name given 3 messages earlier |
| Location recall | /10 | 10 | Remembers location given 3 messages earlier |
| Topic continuity | /10 | ≥8 | Maintains topic across 5+ messages |
| Topic switching | /10 | ≥7 | Handles abrupt topic changes gracefully |
| Long conversation | /10 | ≥8 | 10-message conversation doesn't degrade |

### Voice Pipeline (15%)
| Criterion | Score | Pass Threshold | What to Check |
|-----------|-------|----------------|---------------|
| ASR accuracy | /10 | ≥7 | Speech-to-text correctly transcribes clear speech |
| TTS streaming | /10 | ≥8 | Audio starts playing within 2s of response |
| TTS per language | /10 | ≥8 | Correct voice for ES/EN/JA |
| Voice→Text→Voice flow | /10 | ≥7 | Complete round-trip works without errors |

### UX Quality (15%)
| Criterion | Score | Pass Threshold | What to Check |
|-----------|-------|----------------|---------------|
| Welcome screen | /10 | 10 | Clear instructions, correct branding |
| Message bubbles | /10 | ≥9 | User/assistant messages visually distinct |
| Timestamps | /10 | 10 | Each message has timestamp |
| Copy button | /10 | 10 | Clipboard copy works correctly |
| Auto-scroll | /10 | 10 | View scrolls to latest message |

---

## 🌍 Translator Mode — Rubric

### Translation Accuracy (40%)
| Criterion | Score | Pass Threshold | What to Check |
|-----------|-------|----------------|---------------|
| EN↔ES accuracy | /10 | ≥8 | Direct translations are correct |
| EN→JA accuracy | /10 | ≥7 | English to Japanese translations are natural |
| JA→EN accuracy | /10 | ≥7 | Japanese to English translations are accurate |
| JA→ES accuracy | /10 | ≥7 | Japanese to Spanish (pivot via EN) works |
| ES→JA accuracy | /10 | ≥7 | Spanish to Japanese (pivot via EN) works |
| Idiom translation | /10 | ≥6 | "raining cats and dogs" → "lloviendo a cántaros" |
| Formality preservation | /10 | ≥7 | Formal input → formal output |

### TTS Quality (25%)
| Criterion | Score | Pass Threshold | What to Check |
|-----------|-------|----------------|---------------|
| Spanish TTS | /10 | ≥8 | em_alex voice, speed 0.9x, natural pronunciation |
| English TTS | /10 | ≥8 | af_heart voice, natural flow |
| Japanese TTS | /10 | ≥7 | jf_alpha voice, kanji pronunciation correct |
| TTS latency | /10 | ≥7 | <8s generation for short sentences |
| Audio validity | /10 | 10 | WAV header correct, playable audio |

### Pipeline Performance (20%)
| Criterion | Score | Pass Threshold | What to Check |
|-----------|-------|----------------|---------------|
| Translation latency | /10 | ≥8 | <5s for sync translation |
| ASR accuracy | /10 | ≥7 | Speech transcription is correct |
| Full pipeline | /10 | ≥7 | ASR→Translation→TTS completes in <15s |
| Model loading | /10 | ≥7 | Models load within 30s of first request |
| Model unloading | /10 | 10 | VRAM freed after /api/unload |

### Edge Cases (10%)
| Criterion | Score | Pass Threshold | What to Check |
|-----------|-------|----------------|---------------|
| Empty input | /10 | 10 | Returns error, doesn't crash |
| Same language | /10 | 10 | EN→EN returns original text unchanged |
| Long text | /10 | ≥7 | 1300+ char text translates without timeout |
| Special characters | /10 | 10 | @#$%^&*() handled gracefully |
| Japanese kanji | /10 | ≥8 | Complex kanji sentences translate correctly |

---

## 📝 Grammar App — Rubric

### Authentication (15%)
| Criterion | Score | Pass Threshold | What to Check |
|-----------|-------|----------------|---------------|
| Registration | /10 | 10 | New user created with correct fields |
| Duplicate rejection | /10 | 10 | 409 on duplicate username |
| Login | /10 | 10 | Session cookie set correctly |
| Session persistence | /10 | 10 | /api/auth/me returns user within session |
| Logout | /10 | 10 | Session cleared, /api/auth/me returns 401 |
| Short username | /10 | 10 | 400 for username < 2 chars |

### Skill Tree (20%)
| Criterion | Score | Pass Threshold | What to Check |
|-----------|-------|----------------|---------------|
| Units list | /10 | 10 | ≥3 default units with correct fields |
| Lessons list | /10 | 10 | ≥3 lessons per unit with XP rewards |
| Exercise types | /10 | ≥8 | ≥3 different exercise types in seed data |
| No answer leak | /10 | 10 | correct_answer never sent to client |
| Boss lessons | /10 | 10 | At least 1 boss lesson flagged correctly |

### Exercise Engine (25%)
| Criterion | Score | Pass Threshold | What to Check |
|-----------|-------|----------------|---------------|
| Submit correct | /10 | 10 | Returns correct=true, XP awarded |
| Submit incorrect | /10 | 10 | Returns correct=false, heart consumed |
| XP accumulation | /10 | 10 | XP increases with each correct answer |
| Level calculation | /10 | 10 | Level = (xp / 100) + 1 |
| Hearts system | /10 | 10 | Hearts decrease on wrong, recharge to 5 |
| No hearts penalty | /10 | 10 | no_hearts flag when hearts = 0 |

### Gamification (15%)
| Criterion | Score | Pass Threshold | What to Check |
|-----------|-------|----------------|---------------|
| Streak tracking | /10 | ≥8 | Streak increases daily, resets on gap |
| Lesson completion | /10 | 10 | XP reward on lesson complete |
| Leaderboard | /10 | 10 | Users ranked by XP descending |
| Weekly activity | /10 | ≥7 | Weekly practice count accurate |

### Vocabulary SRS (15%)
| Criterion | Score | Pass Threshold | What to Check |
|-----------|-------|----------------|---------------|
| Add word | /10 | 10 | Word saved with correct fields |
| Review queue | /10 | ≥8 | Due words returned correctly |
| Mastery increase | /10 | 10 | Correct answer → mastery +1, next review delayed |
| Mastery decrease | /10 | 10 | Wrong answer → mastery -1, review tomorrow |
| Max mastery cap | /10 | 10 | Mastery capped at 5 |

### Database Integrity (10%)
| Criterion | Score | Pass Threshold | What to Check |
|-----------|-------|----------------|---------------|
| All tables exist | /10 | 10 | 8 tables present with correct schema |
| Foreign keys | /10 | 10 | No FK violations |
| Indexes | /10 | 10 | Performance indexes present |
| Seed data | /10 | 10 | Units, lessons, exercises pre-populated |

---

## 📋 Scoring Summary

| Subproject | Total Weight | Min Score to Pass |
|------------|:------------:|:-----------------:|
| 🎓 Teacher | 100% | **7.5/10** overall |
| 💬 Conversation | 100% | **7.5/10** overall |
| 🌍 Translator | 100% | **7.0/10** overall |
| 📝 Grammar App | 100% | **8.0/10** overall |

### Failure Conditions (automatic FAIL regardless of score):
- Server crashes during any test
- Data leak (correct_answer exposed to client)
- Memory leak (VRAM grows >1GB during test)
- Security issue (no auth required for protected endpoints)
- Zero emoji policy violated in Teacher/TTS output

---

*Rubric v3.3.1 — June 2026*
*Designed for advanced language learner persona (ES/EN/JA native speakers)*
