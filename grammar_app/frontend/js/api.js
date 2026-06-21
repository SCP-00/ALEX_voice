// Grammar App — API Client
const API_BASE = '';

const api = {
  async request(method, path, data) {
    const opts = {
      method,
      headers: {'Content-Type': 'application/json'},
      credentials: 'same-origin'
    };
    if (data) opts.body = JSON.stringify(data);
    const r = await fetch(API_BASE + path, opts);
    const json = await r.json();
    if (!r.ok) throw new Error(json.error || `HTTP ${r.status}`);
    return json;
  },

  // Auth
  register(username, nativeLang, targetLang) {
    return this.request('POST', '/api/auth/register', {username, display_name: username, native_lang: nativeLang, target_lang: targetLang});
  },
  login(username) {
    return this.request('POST', '/api/auth/login', {username});
  },
  me() {
    return this.request('GET', '/api/auth/me');
  },
  logout() {
    return this.request('POST', '/api/auth/logout');
  },

  // Content
  getUnits() { return this.request('GET', '/api/units'); },
  getLessons(unitId) { return this.request('GET', `/api/units/${unitId}/lessons`); },
  getLesson(lessonId) { return this.request('GET', `/api/lessons/${lessonId}`); },

  // Exercises
  submitExercise(exerciseId, answer, timeSpentMs) {
    return this.request('POST', '/api/exercises/submit', {exercise_id: exerciseId, answer, time_spent_ms: timeSpentMs});
  },

  // Progress
  getStats() { return this.request('GET', '/api/progress/stats'); },
  completeLesson(lessonId, score, heartsLost) {
    return this.request('POST', '/api/progress/complete-lesson', {lesson_id: lessonId, score, hearts_lost: heartsLost});
  },

  // Vocabulary
  getVocabReview() { return this.request('GET', '/api/vocab/review'); },
  addVocab(word, translation, source, target) {
    return this.request('POST', '/api/vocab/add', {word, translation, source_lang: source, target_lang: target});
  },
  updateVocab(vocabId, correct) {
    return this.request('POST', '/api/vocab/update', {vocab_id: vocabId, correct});
  },

  // Leaderboard
  getLeaderboard() { return this.request('GET', '/api/leaderboard'); },

  // Hearts
  rechargeHearts() { return this.request('POST', '/api/hearts/recharge'); }
};
