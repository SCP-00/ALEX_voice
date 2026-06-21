// Grammar App — Main Application Logic
let currentUser = null;
let currentLesson = null;
let currentExercises = [];
let currentExerciseIndex = 0;
let selectedAnswer = '';
let exerciseStartTime = 0;
let heartsLostThisLesson = 0;
let correctThisLesson = 0;

// ── Screen Management ─────────────────────────────────
function showScreen(id) {
  document.querySelectorAll('.screen').forEach(s => s.classList.remove('active'));
  document.getElementById('screen-' + id).classList.add('active');
}

function showTab(tab) {
  document.querySelectorAll('.nav-btn').forEach(b => b.classList.remove('active'));
  event.currentTarget.classList.add('active');
  if (tab === 'tree') loadDashboard();
  else if (tab === 'practice') loadDashboard(); // TODO: spaced repetition view
  else if (tab === 'profile') loadProfile();
}

// ── Auth ──────────────────────────────────────────────
async function handleLogin() {
  const username = document.getElementById('login-username').value.trim();
  const targetLang = document.getElementById('login-target-lang').value;
  const errorEl = document.getElementById('login-error');
  if (!username) { errorEl.textContent = 'Escribe tu nombre'; return; }
  
  try {
    let result;
    try {
      result = await api.login(username);
    } catch (e) {
      result = await api.register(username, 'es', targetLang);
    }
    currentUser = result.user || (await api.me()).user;
    errorEl.textContent = '';
    loadDashboard();
  } catch (e) {
    errorEl.textContent = e.message;
  }
}

async function handleLogout() {
  await api.logout();
  currentUser = null;
  showScreen('login');
}

// ── Dashboard ─────────────────────────────────────────
async function loadDashboard() {
  try {
    const me = await api.me();
    currentUser = me.user;
  } catch (e) {
    showScreen('login');
    return;
  }
  
  document.getElementById('dash-level').textContent = `Lv ${currentUser.level}`;
  document.getElementById('dash-xp').textContent = currentUser.xp;
  document.getElementById('dash-hearts').textContent = currentUser.hearts;
  document.getElementById('dash-streak').textContent = currentUser.streak_days;
  
  await loadSkillTree();
  showScreen('dashboard');
}

async function loadSkillTree() {
  const { units } = await api.getUnits();
  const tree = document.getElementById('skill-tree');
  tree.innerHTML = '';
  
  for (const unit of units) {
    const { lessons } = await api.getLessons(unit.id);
    const unitEl = document.createElement('div');
    unitEl.className = 'unit-node';
    unitEl.innerHTML = `
      <div class="unit-header">
        <span class="unit-icon">${unit.icon}</span>
        <span class="unit-name">${unit.name}</span>
      </div>
      <div class="unit-lessons" id="unit-${unit.id}-lessons"></div>
    `;
    tree.appendChild(unitEl);
    
    const lessonsContainer = unitEl.querySelector('.unit-lessons');
    lessons.forEach((lesson, i) => {
      if (i > 0) {
        const connector = document.createElement('div');
        connector.className = 'unit-connector';
        lessonsContainer.appendChild(connector);
      }
      
      const available = currentUser.level >= unit.required_level;
      const circleClass = lesson.is_boss_lesson ? 'boss' : (available ? 'available' : 'locked');
      
      const node = document.createElement('div');
      node.className = 'lesson-node';
      node.innerHTML = `
        <div class="lesson-circle ${circleClass}" onclick="${available ? `startLesson(${lesson.id})` : ''}">
          ${lesson.is_boss_lesson ? '👑' : '📖'}
        </div>
        <div class="lesson-name">${lesson.name}</div>
      `;
      lessonsContainer.appendChild(node);
    });
  }
}

// ── Lesson ────────────────────────────────────────────
async function startLesson(lessonId) {
  if (currentUser.hearts <= 0) {
    alert('¡Sin corazones! Espera a que se recarguen.');
    return;
  }
  
  try {
    const result = await api.getLesson(lessonId);
    currentLesson = result.lesson;
    currentExercises = result.exercises;
    currentExerciseIndex = 0;
    heartsLostThisLesson = 0;
    correctThisLesson = 0;
    
    document.getElementById('lesson-hearts').textContent = currentUser.hearts;
    showScreen('lesson');
    renderExercise();
  } catch (e) {
    alert('Error cargando lección: ' + e.message);
  }
}

function exitLesson() {
  if (currentExerciseIndex > 0) {
    if (!confirm('¿Salir? Perderás el progreso de esta lección.')) return;
  }
  showScreen('dashboard');
}

function renderExercise() {
  if (currentExerciseIndex >= currentExercises.length) {
    completeLessonFlow();
    return;
  }
  
  const exercise = currentExercises[currentExerciseIndex];
  const area = document.getElementById('exercise-area');
  const progress = ((currentExerciseIndex) / currentExercises.length) * 100;
  document.getElementById('lesson-progress-fill').style.width = progress + '%';
  
  selectedAnswer = '';
  exerciseStartTime = Date.now();
  
  // Reset buttons
  document.getElementById('check-btn').classList.remove('hidden');
  document.getElementById('check-btn').disabled = true;
  document.getElementById('continue-btn').classList.add('hidden');
  document.getElementById('exercise-feedback').classList.remove('show', 'correct', 'wrong');
  
  let html = `<div class="exercise-type">${typeLabel(exercise.exercise_type)}</div>`;
  html += `<div class="exercise-question">${exercise.question}</div>`;
  if (exercise.hint) html += `<div class="exercise-hint">💡 ${exercise.hint}</div>`;
  
  switch (exercise.exercise_type) {
    case 'multiple_choice':
      html += renderMultipleChoice(exercise);
      break;
    case 'fill_blank':
      html += renderFillBlank(exercise);
      break;
    case 'word_bank':
      html += renderWordBank(exercise);
      break;
    case 'translate':
      html += renderTranslate(exercise);
      break;
    default:
      html += renderTranslate(exercise);
  }
  
  area.innerHTML = html;
}

function typeLabel(type) {
  const labels = {
    multiple_choice: 'Opción múltiple',
    fill_blank: 'Completar',
    word_bank: 'Ordenar palabras',
    translate: 'Traducir',
    listen_type: 'Escuchar y escribir',
    match: 'Emparejar'
  };
  return labels[type] || type;
}

// ── Exercise Renderers ────────────────────────────────
function renderMultipleChoice(exercise) {
  const options = JSON.parse(exercise.options || '[]');
  return `<div class="mc-options">${options.map((opt, i) => 
    `<button class="mc-option" onclick="selectMC(this, '${opt.replace(/'/g, "\\'")}')">${opt}</button>`
  ).join('')}</div>`;
}

function selectMC(el, value) {
  document.querySelectorAll('.mc-option').forEach(o => o.classList.remove('selected'));
  el.classList.add('selected');
  selectedAnswer = value;
  document.getElementById('check-btn').disabled = false;
}

function renderFillBlank(exercise) {
  return `<input type="text" class="fill-input" id="fill-answer" placeholder="Escribe tu respuesta..." oninput="onFillInput()">`;
}

function onFillInput() {
  const val = document.getElementById('fill-answer').value.trim();
  selectedAnswer = val;
  document.getElementById('check-btn').disabled = val.length === 0;
}

function renderWordBank(exercise) {
  const words = JSON.parse(exercise.options || '[]');
  const shuffled = [...words].sort(() => Math.random() - 0.5);
  
  let html = '<div class="answer-area" id="answer-area"></div>';
  html += `<div class="word-bank" id="word-bank">`;
  shuffled.forEach((word, i) => {
    html += `<button class="word-chip" onclick="addWord(this, '${word.replace(/'/g, "\\'")}')">${word}</button>`;
  });
  html += '</div>';
  return html;
}

function addWord(el, word) {
  if (el.classList.contains('placed')) return;
  el.classList.add('placed');
  
  const answerArea = document.getElementById('answer-area');
  const chip = document.createElement('span');
  chip.className = 'answer-word';
  chip.textContent = word;
  chip.onclick = () => removeWord(chip, el);
  answerArea.appendChild(chip);
  
  // Update selected answer
  const words = [...answerArea.querySelectorAll('.answer-word')].map(c => c.textContent);
  selectedAnswer = words.join(' ');
  document.getElementById('check-btn').disabled = false;
}

function removeWord(chip, original) {
  original.classList.remove('placed');
  chip.remove();
  const words = [...document.querySelectorAll('.answer-word')].map(c => c.textContent);
  selectedAnswer = words.join(' ');
  document.getElementById('check-btn').disabled = words.length === 0;
}

function renderTranslate(exercise) {
  return `<input type="text" class="fill-input" id="fill-answer" placeholder="Escribe la traducción..." oninput="onFillInput()">`;
}

// ── Check Answer ──────────────────────────────────────
async function checkAnswer() {
  const exercise = currentExercises[currentExerciseIndex];
  const timeSpent = Date.now() - exerciseStartTime;
  
  try {
    const result = await api.submitExercise(exercise.id, selectedAnswer, timeSpent);
    
    const feedback = document.getElementById('exercise-feedback');
    feedback.classList.add('show');
    
    if (result.correct) {
      feedback.classList.add('correct');
      feedback.innerHTML = '✅ ¡Correcto!';
      correctThisLesson++;
    } else {
      feedback.classList.add('wrong');
      feedback.innerHTML = `❌ Incorrecto. La respuesta correcta es: <strong>${result.correct_answer}</strong>`;
      if (result.explanation) feedback.innerHTML += `<br><em>${result.explanation}</em>`;
      heartsLostThisLesson++;
      
      if (result.no_hearts) {
        feedback.innerHTML += '<br><strong>¡Sin corazones! La lección ha terminado.</strong>';
        document.getElementById('check-btn').classList.add('hidden');
        document.getElementById('continue-btn').classList.remove('hidden');
        document.getElementById('continue-btn').onclick = () => completeLessonFlow();
        return;
      }
    }
    
    // Update hearts display
    document.getElementById('lesson-hearts').textContent = result.hearts;
    currentUser.hearts = result.hearts;
    
    // Show continue button
    document.getElementById('check-btn').classList.add('hidden');
    document.getElementById('continue-btn').classList.remove('hidden');
    
  } catch (e) {
    console.error('Submit error:', e);
  }
}

function nextExercise() {
  currentExerciseIndex++;
  renderExercise();
}

// ── Complete Lesson ───────────────────────────────────
async function completeLessonFlow() {
  const total = currentExercises.length || 1;
  const score = Math.round((correctThisLesson / total) * 100);
  
  try {
    await api.completeLesson(currentLesson.id, score, heartsLostThisLesson);
    const me = await api.me();
    currentUser = me.user;
  } catch (e) {}
  
  document.getElementById('complete-xp').textContent = `+${currentLesson.xp_reward || 10}`;
  document.getElementById('complete-accuracy').textContent = `${correctThisLesson}/${total} (${Math.round(correctThisLesson/total*100)}%)`;
  document.getElementById('complete-streak').textContent = currentUser.streak_days;
  
  showScreen('complete');
}

function backToDashboard() {
  loadDashboard();
}

// ── Profile ───────────────────────────────────────────
async function loadProfile() {
  try {
    const me = await api.me();
    currentUser = me.user;
  } catch (e) {
    showScreen('login');
    return;
  }
  
  document.getElementById('profile-name').textContent = currentUser.display_name;
  document.getElementById('profile-level').textContent = `Nivel ${currentUser.level} · ${currentUser.xp} XP`;
  
  try {
    const stats = await api.getStats();
    const statsEl = document.getElementById('profile-stats');
    statsEl.innerHTML = `
      <div class="profile-stat"><div class="profile-stat-value">${stats.total_exercises || 0}</div><div class="profile-stat-label">Ejercicios</div></div>
      <div class="profile-stat"><div class="profile-stat-value">${stats.accuracy || 0}%</div><div class="profile-stat-label">Precisión</div></div>
      <div class="profile-stat"><div class="profile-stat-value">${currentUser.streak_days}</div><div class="profile-stat-label">🔥 Racha</div></div>
      <div class="profile-stat"><div class="profile-stat-value">${stats.vocabulary_count || 0}</div><div class="profile-stat-label">Vocabulario</div></div>
    `;
  } catch (e) {}
  
  try {
    const { leaderboard } = await api.getLeaderboard();
    const lbEl = document.getElementById('profile-leaderboard');
    lbEl.innerHTML = '<h3>🏆 Ranking</h3>';
    leaderboard.forEach((u, i) => {
      lbEl.innerHTML += `
        <div class="lb-entry">
          <span class="lb-rank">${i + 1}</span>
          <span class="lb-name">${u.display_name}</span>
          <span class="lb-xp">${u.xp} XP</span>
        </div>
      `;
    });
  } catch (e) {}
  
  showScreen('profile');
}

// ── Init ──────────────────────────────────────────────
(async () => {
  try {
    const me = await api.me();
    currentUser = me.user;
    loadDashboard();
  } catch (e) {
    showScreen('login');
  }
})();
