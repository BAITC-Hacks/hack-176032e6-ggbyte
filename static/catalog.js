/* Catalogue uses the same availability checks and completion endpoint as the navigator. */
const CareerCatalog = (() => {
  function restriction(event, profile) {
    if (event.available) return "Можно пройти сейчас";
    if (event.completed) return "Активность уже завершена";
    if (event.mandatory) return "Обязательная активность назначается отдельно от карьерного маршрута";
    if (!event.target_roles.includes(profile.employee.role) || !event.target_grades.includes(profile.employee.grade))
      return "Для другой текущей роли или грейда";
    if (event.requirements.some(skill => skill.current < skill.required)) return "Сначала развейте навыки из условий участия";
    return "Пока нет доступной сессии";
  }
  function card(event, profile) {
    const next = event.upcoming_sessions.filter(day => day >= profile.today).sort()[0];
    const delta = event.projected_progress - profile.progress;
    const finished = event.completed && !event.available;
    const hasGain = event.skill_effects.some(skill => skill.after > skill.before);
    return `<article class="learning-card panel"><div class="quest-top"><span class="tag ${event.available ? '' : 'neutral'}">${event.available ? 'Доступно' : event.completed ? 'Завершено' : 'Есть условия'}</span><span class="sub">${types[event.type] || esc(event.type)}</span></div><h2>${esc(event.title)}</h2><p class="learning-description">${esc(event.description)}</p><div class="quest-meta"><span>${event.duration_hours} ч</span><span>${formats[event.format] || esc(event.format)}</span></div><div class="learning-effects">${event.skill_effects.map((skill, index) => `<div><span>${esc(skill.name)}</span><strong>${finished ? `Сейчас ${skill.before}` : event.available ? `${skill.before} → ${skill.after}` : `+${event.develops_skills[index].gain}, предел ${event.develops_skills[index].max_level}`}</strong></div>`).join('') || '<p class="sub">Без изменения уровней навыков</p>'}</div><p class="sub">${finished ? 'Результат завершения уже учтён в профиле' : !event.available ? 'Прогноз прогресса появится после выполнения условий участия' : delta > 0 ? `Соответствие цели после шага: ${profile.progress}% → ${event.projected_progress}%` : hasGain ? 'Развивает навыки вне требований текущей цели' : 'Не повышает текущие уровни навыков'}</p><details><summary>Условия участия</summary><p>Роли: ${event.target_roles.map(esc).join(', ')}. Грейды: ${event.target_grades.map(esc).join(', ')}.</p>${event.requirements.length ? `<ul>${event.requirements.map(skill => `<li>${esc(skill.name)}: нужно ${skill.required}, сейчас ${skill.current}</li>`).join('')}</ul>` : '<p>Предварительные навыки не требуются.</p>'}<p>${event.format === 'self_paced' ? 'Можно начать в удобное время.' : next ? `Ближайшая сессия: ${date(next)}` : 'Будущая сессия пока не назначена.'}</p></details><div class="learning-action"><p class="sub">${restriction(event, profile)}</p><button class="btn ${event.available ? '' : 'secondary'}" ${event.available ? `data-complete="${esc(event.event_id)}"` : 'disabled'}>${event.available ? 'Отметить выполненным' : event.completed ? 'Уже завершено' : 'Пока недоступно'}</button></div></article>`;
  }
  function markup(profile) {
    const events = profile.catalog || [];
    const skills = new Map(events.flatMap(event => event.skill_effects.map(skill => [skill.skill_id, skill.name])));
    return `<section class="panel learning-intro"><h2>Развивайте навыки в своём темпе</h2><p class="sub">Активностей в каталоге: ${events.length} · доступны для вашего профиля: ${events.filter(event => event.available).length}. AI-навигатор выделяет следующие шаги, а здесь можно изучить весь каталог.</p><p class="sub">В приложении фиксируется результат участия. Само обучение проводится отдельно; отметка о завершении пересчитывает навыки и карьерный прогресс.</p><div class="workspace-toolbar"><label class="field">Поиск обучения<input id="learning-search" type="search" placeholder="Название, описание или навык"></label><label class="field">Навык<select id="learning-skill"><option value="all">Все навыки</option>${[...skills].sort((a,b) => a[1].localeCompare(b[1], 'ru')).map(([id,name]) => `<option value="${esc(id)}">${esc(name)}</option>`).join('')}</select></label><label class="field">Доступность<select id="learning-status"><option value="all">Все активности</option><option value="available">Доступны сейчас</option><option value="completed">Завершённые</option><option value="locked">Пока недоступные</option></select></label><button class="btn secondary" id="learning-reset">Сбросить</button></div><p id="learning-count" class="sub" role="status"></p></section><div id="learning-results" class="learning-grid"></div>`;
  }
  function bind(profile, bindActions) {
    const search = document.getElementById('learning-search');
    const skill = document.getElementById('learning-skill');
    const status = document.getElementById('learning-status');
    const events = profile.catalog || [];
    function update() {
      const query = search.value.trim().toLocaleLowerCase('ru');
      const rows = events.filter(event => (!query || `${event.title} ${event.description} ${event.skill_effects.map(s => s.name).join(' ')}`.toLocaleLowerCase('ru').includes(query))
        && (skill.value === 'all' || event.skill_effects.some(s => s.skill_id === skill.value))
        && (status.value === 'all' || status.value === 'available' && event.available || status.value === 'completed' && event.completed || status.value === 'locked' && !event.available && !event.completed));
      rows.sort((a,b) => Number(b.available) - Number(a.available) || a.title.localeCompare(b.title, 'ru'));
      document.getElementById('learning-count').textContent = `Показано активностей: ${rows.length} из ${events.length}.`;
      document.getElementById('learning-results').innerHTML = rows.length ? rows.map(event => card(event, profile)).join('') : '<div class="panel empty">По этим условиям активностей нет. Измените поиск или сбросьте фильтры.</div>';
      bindActions();
    }
    search.oninput = update;
    skill.onchange = update;
    status.onchange = update;
    document.getElementById('learning-reset').onclick = () => { search.value = ''; skill.value = 'all'; status.value = 'all'; update(); };
    update();
  }
  return {markup, bind};
})();
