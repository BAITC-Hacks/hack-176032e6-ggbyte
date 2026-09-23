/* Profile views use the existing API payload; filtering never changes saved data. */
const CareerViews = (() => {
  const entries = (value) => (Array.isArray(value) ? value : []);
  const normalize = (value) => String(value ?? "").trim().toLocaleLowerCase("ru-RU");
  const statusName = (status) => labels[status] || status;
  const statusClass = (status) => status === "completed" ? "" : status === "in_progress" ? "blue" : "amber";
  const statusTag = (status) => `<span class="tag ${statusClass(status)}">${esc(statusName(status))}</span>`;
  const ready = (skill) => skill.required != null && skill.level >= skill.required;

  function skillsFor(profile) {
    const skills = new Map(entries(profile.skill_details).map((skill) => [skill.skill_id, { ...skill }]));
    for (const gap of entries(profile.gaps)) {
      skills.set(gap.skill_id, {
        ...skills.get(gap.skill_id),
        ...gap,
        level: gap.current,
      });
    }
    return [...skills.values()].sort((a, b) => a.name.localeCompare(b.name, "ru"));
  }

  function levelBar(level, name) {
    return `<div class="bar" role="progressbar" aria-label="${esc(name)}: текущий уровень" aria-valuemin="0" aria-valuemax="5" aria-valuenow="${esc(level)}"><span style="width:${Math.max(0, Math.min(100, level * 20))}%"></span></div>`;
  }

  function focusRow(gap) {
    const achieved = gap.current >= gap.required;
    return `<div class="focus-row"><div class="skill-label"><strong>${esc(gap.name)}</strong><span>${esc(gap.current)} / ${esc(gap.required)}</span></div>${levelBar(gap.current, gap.name)}<div class="focus-meta"><span class="sub">Цель: уровень ${esc(gap.required)} из 5</span><span class="tag ${achieved ? "" : gap.critical ? "amber" : "neutral"}">${achieved ? "На уровне цели" : gap.critical ? "Ключевой для цели" : "Для развития"}</span></div></div>`;
  }

  function dashboard(profile) {
    const gaps = entries(profile.gaps);
    const open = gaps.filter((gap) => gap.current < gap.required);
    const goalReady = gaps.length > 0 && open.length === 0;
    const focus = (open.length ? open : gaps).slice(0, 4);
    const recent = entries(profile.history).slice().sort((a, b) => b.date.localeCompare(a.date)).slice(0, 4);
    const result = goalReady
      ? `<section class="outcome-banner"><div><h2>Навыки соответствуют цели</h2><p>Обсудите результат и следующую карьерную цель с руководителем. Достижение требований по навыкам не означает автоматического повышения.</p></div><button class="btn secondary" data-open-view="skills">Перейти к цели</button></section>`
      : !entries(profile.recommendations).length
        ? `<section class="outcome-banner"><div><h2>Нужен следующий шаг с HR</h2><p>Разрывы навыков остаются, но в текущем каталоге нет доступной активности, которая их закрывает. Карта навыков поможет обсудить индивидуальный план.</p></div><button class="btn secondary" data-open-view="skills">Посмотреть разрывы</button></section>`
        : "";
    return `${result}<div class="workspace-grid"><section class="panel skill-focus"><div class="section-head"><div><h2>${open.length ? "Фокус развития" : "Навыки для цели"}</h2><p>${open.length ? `Навыков ниже уровня цели: ${open.length} из ${gaps.length}` : `На уровне цели: ${gaps.length} из ${gaps.length}`}</p></div><button class="btn text" data-open-view="skills">Все навыки →</button></div>${focus.map(focusRow).join("") || '<p class="empty">Требования к навыкам для этой цели пока не заданы.</p>'}</section><section class="panel"><div class="section-head"><div><h2>Последние активности</h2><p>События из вашей истории участия</p></div><button class="btn text" data-open-view="history">Вся история →</button></div>${recent.length ? `<ol class="history-timeline">${recent.map((row) => `<li class="timeline-row"><div class="timeline-content"><strong>${esc(row.title)}</strong><div class="timeline-meta"><time datetime="${esc(row.date)}">${date(row.date)}</time><span>Выполнение: ${esc(row.completion_pct)}%</span></div></div>${statusTag(row.status)}</li>`).join("")}</ol>` : '<p class="empty">История пока пуста. После завершения рекомендованной активности здесь появится результат.</p>'}</section></div>`;
  }

  function skills(profile) {
    const gaps = entries(profile.gaps);
    const closed = gaps.filter((gap) => gap.current >= gap.required).length;
    const critical = gaps.filter((gap) => gap.critical && gap.current < gap.required).length;
    return `<section class="panel skill-focus"><div class="section-head"><div><h2>Карта навыков</h2><p>Сравните текущие уровни с требованиями выбранной цели</p></div><span class="tag neutral">Шкала: 0–5</span></div><div class="inline-metrics"><div class="metric-item"><b>${closed} / ${gaps.length}</b><span>Навыки на уровне цели</span></div><div class="metric-item"><b>${gaps.length - closed}</b><span>Навыки для развития</span></div><div class="metric-item"><b>${critical}</b><span>Ключевые разрывы</span></div></div><div class="workspace-toolbar"><label class="field" for="skill-search">Поиск навыка<input id="skill-search" type="search" placeholder="Название навыка" autocomplete="off"></label><label class="field" for="skill-filter">Показать<select id="skill-filter"><option value="all">Все навыки</option><option value="development">Ниже уровня цели</option><option value="critical">Ключевые для цели</option><option value="ready">На уровне цели</option></select></label></div><p id="skill-count" class="workspace-count sub" role="status"></p><div class="table-wrap"><table class="skill-table"><thead><tr><th scope="col">Навык</th><th scope="col">Тип</th><th scope="col">Сейчас</th><th scope="col">Для цели</th><th scope="col">Статус</th></tr></thead><tbody id="skill-body"></tbody></table></div><p class="footer-note">Полоса показывает текущий уровень по шкале от 0 до 5. Ключевые навыки обязательны для цели; прочерк означает, что навык для неё не требуется.</p></section>`;
  }

  function bindSkills(profile) {
    const all = skillsFor(profile);
    const search = document.getElementById("skill-search");
    const filter = document.getElementById("skill-filter");
    const body = document.getElementById("skill-body");
    const count = document.getElementById("skill-count");
    if (!search || !filter || !body || !count) return;
    function renderRows() {
      const query = normalize(search.value);
      const shown = all.filter((skill) => normalize(skill.name).includes(query) && (
        filter.value === "all" ||
        (filter.value === "development" && skill.required != null && !ready(skill)) ||
        (filter.value === "critical" && skill.critical) ||
        (filter.value === "ready" && ready(skill))
      ));
      count.textContent = `Показано навыков: ${shown.length} из ${all.length}`;
      body.innerHTML = shown.map((skill) => `<tr><td><strong>${esc(skill.name)}</strong>${skill.critical ? '<small class="critical-mark">Ключевой</small>' : ""}</td><td>${skill.type === "hard" ? "Профессиональный" : skill.type === "soft" ? "Гибкий" : "—"}</td><td class="skill-level"><span>${esc(skill.level)} / 5</span><div class="skill-progress">${levelBar(skill.level, skill.name)}</div></td><td>${skill.required == null ? "—" : esc(skill.required)}</td><td><span class="tag ${skill.required == null ? "neutral" : ready(skill) ? "" : "amber"}">${skill.required == null ? "Вне текущей цели" : ready(skill) ? "На уровне цели" : `Разрыв: ${esc(skill.required - skill.level)}`}</span></td></tr>`).join("") || `<tr><td colspan="5" class="table-empty">${all.length ? "Нет навыков по выбранным условиям. Измените поиск или выберите «Все навыки»." : "В профиле пока нет данных о навыках."}</td></tr>`;
    }
    search.oninput = renderRows;
    filter.onchange = renderRows;
    renderRows();
  }

  function cutoff(today, days) {
    const reference = new Date(`${today}T00:00:00Z`);
    if (!Number.isFinite(reference.getTime())) return null;
    reference.setUTCDate(reference.getUTCDate() - days + 1);
    return reference.toISOString().slice(0, 10);
  }

  function history(profile) {
    const rows = entries(profile.history);
    const completed = rows.filter((row) => row.status === "completed").length;
    const inProgress = rows.filter((row) => row.status === "in_progress").length;
    const since = cutoff(profile.today, 90);
    const recent = since ? rows.filter((row) => row.status === "completed" && row.date >= since && row.date <= profile.today).length : null;
    return `<div class="inline-metrics"><div class="metric-item"><b>${rows.length}</b><span>Записей об участии</span></div><div class="metric-item"><b>${completed}</b><span>Завершено</span></div><div class="metric-item"><b>${inProgress}</b><span>Записей «В процессе»</span></div><div class="metric-item"><b>${recent == null ? "—" : recent}</b><span>Завершено за 90 дней</span></div></div><section class="panel"><div class="section-head"><div><h2>История участия</h2><p>Данные на ${date(profile.today)} · периоды отсчитываются от этой даты.</p></div></div><div class="workspace-toolbar"><label class="field" for="history-search">Поиск активности<input id="history-search" type="search" placeholder="Название активности" autocomplete="off"></label><label class="field" for="history-filter">Статус<select id="history-filter"><option value="all">Все статусы</option>${Object.entries(labels).map(([key, label]) => `<option value="${esc(key)}">${esc(label)}</option>`).join("")}</select></label><label class="field" for="history-period">Период<select id="history-period"><option value="all">За всё время</option><option value="30">Последние 30 дней</option><option value="90">Последние 90 дней</option><option value="365">Последние 365 дней</option></select></label><label class="field" for="history-sort">Порядок<select id="history-sort"><option value="newest">Сначала новые</option><option value="oldest">Сначала старые</option></select></label><button class="btn secondary" id="history-reset" type="button">Сбросить</button></div><p id="history-count" class="workspace-count sub" role="status"></p><div class="table-wrap"><table><thead><tr><th scope="col">Активность</th><th scope="col">Дата</th><th scope="col">Статус</th><th scope="col">Выполнение</th></tr></thead><tbody id="history-body"></tbody></table></div></section>`;
  }

  function bindHistory(profile) {
    const all = entries(profile.history);
    const search = document.getElementById("history-search");
    const filter = document.getElementById("history-filter");
    const period = document.getElementById("history-period");
    const sort = document.getElementById("history-sort");
    const reset = document.getElementById("history-reset");
    const body = document.getElementById("history-body");
    const count = document.getElementById("history-count");
    if (!search || !filter || !period || !sort || !reset || !body || !count) return;
    function renderRows() {
      const query = normalize(search.value);
      const since = period.value === "all" ? null : cutoff(profile.today, Number(period.value));
      const shown = all.filter((row) => normalize(row.title).includes(query) &&
        (filter.value === "all" || row.status === filter.value) &&
        (!since || (row.date >= since && row.date <= profile.today))
      ).sort((a, b) => sort.value === "oldest" ? a.date.localeCompare(b.date) : b.date.localeCompare(a.date));
      count.textContent = `Показано записей: ${shown.length} из ${all.length}. Завершено в выборке: ${shown.filter((row) => row.status === "completed").length}.`;
      body.innerHTML = shown.map((row) => `<tr><td>${esc(row.title)}</td><td><time datetime="${esc(row.date)}">${date(row.date)}</time></td><td>${statusTag(row.status)}</td><td>${esc(row.completion_pct)}%</td></tr>`).join("") || `<tr><td colspan="4" class="table-empty">${all.length ? "Нет активностей по выбранным условиям. Измените фильтры или нажмите «Сбросить»." : "История пока пуста. Завершённые активности появятся здесь автоматически."}</td></tr>`;
    }
    search.oninput = renderRows;
    filter.onchange = renderRows;
    period.onchange = renderRows;
    sort.onchange = renderRows;
    reset.onclick = () => {
      search.value = "";
      filter.value = "all";
      period.value = "all";
      sort.value = "newest";
      renderRows();
    };
    renderRows();
  }

  return { dashboard, skills, bindSkills, history, bindHistory };
})();
