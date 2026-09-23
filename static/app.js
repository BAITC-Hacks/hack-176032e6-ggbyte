const app = document.getElementById("app");
const state = {
  session: null,
  profile: null,
  hr: null,
  view: "home",
  ai: null,
  health: null,
  request: 0,
};
const esc = (v) =>
  String(v ?? "").replace(
    /[&<>"']/g,
    (c) =>
      ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" })[
        c
      ],
  );
const icons = {
  home: '<rect x="3" y="3" width="7" height="7" rx="1"/><rect x="14" y="3" width="7" height="7" rx="1"/><rect x="3" y="14" width="7" height="7" rx="1"/><rect x="14" y="14" width="7" height="7" rx="1"/>',
  skills: '<path d="M4 19V12m8 7V5m8 14V9"/>',
  history: '<circle cx="12" cy="12" r="9"/><path d="M12 7v5l3 2"/>',
  hr: '<path d="M3 20v-7h5v7m4 0V4h5v16m4 0V9"/>',
  import: '<path d="M12 16V3m-5 5 5-5 5 5M4 15v6h16v-6"/>',
};
const icon = (key) =>
  `<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.6" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">${icons[key] || icons.home}</svg>`;
const labels = {
  completed: "Завершено",
  in_progress: "В процессе",
  dropped: "Прекращено",
  no_show: "Пропуск",
  declined: "Отклонено",
  overdue: "Просрочено",
};
const formats = {
  online: "Онлайн",
  offline: "Очно",
  self_paced: "В своём темпе",
};
const types = {
  course: "Курс",
  workshop: "Практикум",
  mentoring: "Менторство",
  certification: "Сертификация",
  meetup: "Встреча",
  onboarding: "Онбординг",
  compliance: "Обязательное",
};
const date = (d) =>
  d
    ? new Date(d + "T12:00:00").toLocaleDateString("ru-RU", {
        day: "numeric",
        month: "short",
        year: "numeric",
      })
    : "";
async function api(path, data) {
  const response = await fetch(
    "/api" + path,
    data === undefined
      ? {}
      : {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify(data),
        },
  );
  const result = await response.json();
  if (!response.ok) {
    if (response.status === 401 && path !== "/login") {
      state.session = null;
      renderLogin();
    }
    throw new Error(result.error || "Не удалось выполнить запрос.");
  }
  return result;
}
let toastTimer;
function isDemo() {
  return (state.profile?.data_mode || state.health?.mode) === "independent_demo";
}
function aiSetupHint(config) {
  if (!config || config.configured) return "";
  if (!config.provider || config.provider === "none")
    return "Для модели укажите AI_PROVIDER=openai и OPENAI_API_KEY в локальном файле .env, затем перезапустите приложение.";
  if (["openai", "nvidia"].includes(config.provider) && !config.key_configured)
    return `Добавьте ${config.provider === "openai" ? "OPENAI_API_KEY" : "NVIDIA_API_KEY"} в локальный файл .env и перезапустите приложение. Ключ остаётся на сервере.`;
  if (!config.cloud_allowed && !config.demo_data_allowed)
    return isDemo()
      ? "В этот профиль импортированы данные. Для них внешняя обработка выключена. Проверить модель можно на исходном демопрофиле E0001 после сброса сценария."
      : "Внешняя обработка данных датасета выключена. Чтобы проверить модель на независимых примерах, запустите: python run.py --demo-ai.";
  return "Проверьте настройки AI_PROVIDER и модели в файле .env, затем перезапустите приложение.";
}
function dataModeBanner() {
  return isDemo() ? '<span class="environment">Демоданные</span>' : "";
}
function aiStatus() {
  const answer = state.ai;
  const config = state.profile.ai;
  const label = answer?.mode === "llm"
    ? "Подбор AI"
    : answer?.mode === "fallback"
      ? "AI недоступен · подбор по правилам"
      : config.configured && !answer ? "Ожидаем ответ AI" : "Подбор по правилам";
  const message = answer?.message || (config.configured
    ? "Модель выбирает активности по навыкам, цели и истории участия."
    : "Рекомендации рассчитаны по навыкам, цели и истории участия без модели.");
  const timing = answer?.cached ? "Сохранённый ответ модели." : answer?.latency_ms ? `Время ответа: ${(answer.latency_ms / 1000).toFixed(1)} с.` : "";
  const hint = aiSetupHint(config);
  return `<div class="ai-status-line"><span class="tag ${answer?.mode === "llm" ? "" : "neutral"}">${label}</span><details class="ai-details"><summary>О подборе</summary><p>${esc(message)}</p>${timing ? `<p>${esc(timing)}</p>` : ""}${hint ? `<p>${esc(hint)}</p>` : ""}${isDemo() ? '<p>Облачная обработка разрешена только для исходных демопрофилей. Импортированные данные не получают это разрешение автоматически.</p>' : ""}</details></div>`;
}
function demoResetControl() {
  if (!isDemo() || state.profile.employee.employee_id !== "E0001") return "";
  return `<details class="demo-reset"><summary>Повторить демосценарий</summary><p>Сброс восстановит исходные навыки, цель и историю только демосотрудника E0001. Его прогресс вернётся к 50%; добавленные для него завершения и импортированные изменения будут удалены.</p><button class="btn secondary" id="reset-demo" type="button">Сбросить демопрофиль E0001</button></details>`;
}
function bindDemoReset() {
  const button = document.getElementById("reset-demo");
  if (!button) return;
  button.onclick = async () => {
    button.disabled = true;
    state.request++;
    try {
      state.profile = await api("/demo/reset", { employee_id: "E0001" });
      state.ai = null;
      render();
      toast("Демосценарий E0001 восстановлен. Прогресс — 50%.");
      refreshAI();
    } catch (error) {
      toast(error.message);
      button.disabled = false;
    }
  };
}
function toast(message) {
  const el = document.getElementById("toast");
  el.textContent = message;
  el.style.display = "block";
  clearTimeout(toastTimer);
  toastTimer = setTimeout(() => (el.style.display = "none"), 5500);
}
function renderLogin() {
  app.innerHTML = `<main class="login"><section class="login-form"><div class="brand"><img src="/favicon.svg" alt=""><span>Career Quest</span></div><form id="login"><div class="login-head"><h1>Вход в кабинет</h1>${dataModeBanner()}</div><label class="field">Режим<select name="role" id="login-role"><option value="employee">Сотрудник</option><option value="hr">HR-специалист</option></select></label><label class="field" id="employee-field">ID сотрудника<input name="employee_id" value="E0001" autocomplete="username" required></label><label class="field">Пароль<input name="password" type="password" autocomplete="current-password" required></label><button class="btn" type="submit">Войти</button><p id="login-error" class="error" role="alert"></p><details class="demo-hint"><summary>Доступ для демонстрации</summary><p>Сотрудник: <b>E0001</b> / <b>quest-demo</b><br>HR: <b>hr-quest-demo</b></p></details></form></section></main>`;
  document.getElementById("login-role").onchange = (e) => {
    const field = document.getElementById("employee-field");
    const isHR = e.target.value === "hr";
    field.hidden = isHR;
    field.querySelector("input").required = !isHR;
  };
  document.getElementById("login").onsubmit = async (e) => {
    e.preventDefault();
    const button = e.target.querySelector("button");
    button.disabled = true;
    try {
      await api("/login", Object.fromEntries(new FormData(e.target)));
      await boot();
    } catch (error) {
      document.getElementById("login-error").textContent = error.message;
      button.disabled = false;
    }
  };
}
function shell(body) {
  const e = state.profile?.employee;
  const isHR = state.session.role === "hr";
  const nav = [
    ...(isHR ? [["hr", "Сотрудники"]] : []),
    ["home", "Обзор"],
    ["skills", "Цель и навыки"],
    ["history", "История"],
    ...(isHR ? [["import", "Импорт"]] : []),
  ];
  app.innerHTML = `<div class="shell"><aside class="sidebar"><div class="brand"><img src="/favicon.svg" alt=""><span>Career Quest</span></div><nav class="nav" aria-label="Основная навигация">${nav.map(([key, label]) => `<button data-view="${key}" class="${state.view === key ? "active" : ""}" ${state.view === key ? 'aria-current="page"' : ""}>${icon(key)}${label}</button>`).join("")}</nav></aside><div class="content"><header class="topbar">${dataModeBanner()}<div class="account"><span class="avatar" aria-hidden="true">${isHR ? "HR" : esc(e?.full_name.split(" ").map((n) => n[0]).slice(0, 2).join(""))}</span><span class="account-name">${isHR ? "HR-кабинет" : esc(e?.full_name)}</span><button class="logout" id="logout">Выйти</button></div></header><main class="page">${body}</main></div></div>`;
  document.querySelectorAll("[data-view]").forEach((b) => (b.onclick = () => navigate(b.dataset.view)));
  const navigation = document.querySelector(".nav");
  const activeItem = navigation.querySelector('[aria-current="page"]');
  if (activeItem && navigation.scrollWidth > navigation.clientWidth) {
    navigation.scrollLeft += activeItem.getBoundingClientRect().left -
      navigation.getBoundingClientRect().left -
      (navigation.clientWidth - activeItem.clientWidth) / 2;
  }
  document.getElementById("logout").onclick = async () => {
    try {
      await api("/logout", {});
      state.request++;
      state.session = null;
      state.ai = null;
      renderLogin();
    } catch (error) {
      toast(error.message);
    }
  };
}
function heading(title, sub = "") {
  return `<div class="page-heading"><div><h1>${title}</h1>${sub ? `<p>${sub}</p>` : ""}</div></div>`;
}
function stats(items) {
  return `<div class="stats stats-${items.length}">${items.map(([number, label]) => `<div class="stat"><b>${number}</b><span>${label}</span></div>`).join("")}</div>`;
}
function quests() {
  const p = state.profile;
  const recs = state.ai?.recommendations || p.recommendations;
  if (!recs.length) return `<div class="empty">${esc(p.empty_reason)}</div>`;
  return `<div class="quest-grid">${recs.map((r, i) =>
    `<article class="quest"><div class="quest-top"><span class="tag neutral">${types[r.type] || esc(r.type)}</span>${r.in_progress ? '<span class="tag blue">В процессе</span>' : ""}</div><h3>${esc(r.title)}</h3><div class="quest-meta"><span>${r.duration_hours} ч</span><span>${formats[r.format] || esc(r.format)}</span></div><div class="impact">${r.gains.length
      ? r.gains.slice(0, 2).map((g) => `${esc(g.name)} <b>${g.before} → ${g.after}</b>`).join("<br>")
      : `Откроет доступ: ${esc(r.unlocks[0])}`}</div><div class="quest-projection">Прогресс после завершения <b>${p.progress}% → ${r.projected_progress}%</b></div><details><summary>Почему подходит</summary><ul>${r.reasons.map((reason) => `<li>${esc(reason)}</li>`).join("")}</ul><p class="muted">${esc(r.description)}</p><p class="muted">${r.next_session ? "Ближайшая сессия: " + date(r.next_session) : "Можно начать в любое время"}</p></details><button class="btn ${i === 0 ? "" : "secondary"}" data-complete="${esc(r.event_id)}">Отметить выполненным</button></article>`
  ).join("")}</div>`;
}
function bindCompletions() {
  document.querySelectorAll("[data-complete]").forEach(
    (button) =>
      (button.onclick = async () => {
        button.disabled = true;
        try {
          const before = state.profile.progress;
          state.profile = await api("/complete", {
            employee_id: state.profile.employee.employee_id,
            event_id: button.dataset.complete,
          });
          state.ai = null;
          state.request++;
          render();
          toast(
            `Активность завершена. Прогресс: ${before}% → ${state.profile.progress}%.`,
          );
          refreshAI();
        } catch (error) {
          toast(error.message);
          button.disabled = false;
        }
      }),
  );
}
function renderHome() {
  const p = state.profile, e = p.employee;
  const isHR = state.session.role === "hr";
  const done = p.history.filter((r) => r.status === "completed").length;
  const closed = p.gaps.filter((g) => g.current >= g.required).length;
  const critical = p.gaps.filter((g) => g.critical && g.current < g.required).length;
  shell(`${isHR ? '<button class="btn text" id="back-staff">← К сотрудникам</button>' : ""}${heading(isHR ? esc(e.full_name) : "Моё развитие", `${esc(e.role)} · ${esc(e.grade)}`)}<section class="panel goal-summary"><div><p class="goal-label">Карьерная цель</p><h2>${esc(p.target.role)} · ${esc(p.target.grade)}</h2><button class="btn text" id="edit-goal">Изменить цель</button></div><div class="goal-progress"><div class="skill-label"><span>Соответствие цели</span><strong>${p.progress}%</strong></div><div class="bar" role="progressbar" aria-label="Соответствие навыков цели" aria-valuemin="0" aria-valuemax="100" aria-valuenow="${p.progress}"><span style="width:${p.progress}%"></span></div></div></section><div class="goal-metrics"><span>Навыки на уровне цели: <b>${closed} из ${p.gaps.length}</b></span><span>Ключевые навыки для развития: <b>${critical}</b></span><span>Завершено активностей: <b>${done}</b></span></div><section id="ai-navigator" aria-labelledby="ai-heading"><div class="section-head"><h2 id="ai-heading">Рекомендации</h2><button class="btn secondary" id="refresh-ai">Обновить</button></div><div id="ai-state" class="ai-state" role="status">${aiStatus()}</div><div id="quests">${quests()}</div></section>${demoResetControl()}`);
  document.getElementById("edit-goal").onclick = () => navigate("skills");
  if (isHR) document.getElementById("back-staff").onclick = () => navigate("hr");
  document.getElementById("refresh-ai").onclick = () => refreshAI();
  bindCompletions();
  bindDemoReset();
}
async function refreshAI() {
  const request = ++state.request;
  const eid = state.profile.employee.employee_id;
  const button = document.getElementById("refresh-ai");
  if (button) {
    button.disabled = true;
    button.textContent = "Подбираем…";
  }
  const status = document.getElementById("ai-state");
  if (status && state.profile.ai.configured) {
    status.innerHTML = '<span class="tag neutral">AI подбирает рекомендации…</span>';
  }
  try {
    const answer = await api("/ai", { employee_id: eid });
    if (
      request !== state.request ||
      !state.session ||
      state.profile.employee.employee_id !== eid
    )
      return;
    state.ai = answer;
    if (state.view === "home") {
      document.getElementById("ai-state").innerHTML = aiStatus();
      document.getElementById("quests").innerHTML = quests();
      bindCompletions();
    }
  } catch (error) {
    if (request === state.request) {
      state.ai = { mode: "fallback", message: `Не удалось получить ответ AI: ${error.message}. Показан подбор по правилам.` };
      const currentStatus = document.getElementById("ai-state");
      if (currentStatus) {
        currentStatus.innerHTML = aiStatus();
        document.getElementById("quests").innerHTML = quests();
        bindCompletions();
      }
      toast(error.message);
    }
  } finally {
    if (request === state.request && button?.isConnected) {
      button.disabled = false;
      button.textContent = "Обновить";
    }
  }
}
function profileSkills(profile) {
  const skills = new Map(profile.skill_details.map((s) => [s.skill_id, s]));
  for (const gap of profile.gaps) {
    if (!skills.has(gap.skill_id)) {
      skills.set(gap.skill_id, { ...gap, level: gap.current });
    }
  }
  return `<section class="panel"><div class="section-head"><h2>Навыки</h2><span class="sub">Уровни от 0 до 5</span></div><div class="table-wrap"><table><thead><tr><th>Навык</th><th>Тип</th><th>Сейчас</th><th>Для цели</th></tr></thead><tbody>${[...skills.values()].sort((a, b) => a.name.localeCompare(b.name, "ru")).map((s) => {
    const gap = profile.gaps.find((g) => g.skill_id === s.skill_id);
    return `<tr><td>${esc(s.name)}${gap?.critical ? '<small class="critical-mark">Ключевой</small>' : ""}</td><td>${s.type === "hard" ? "Профессиональный" : s.type === "soft" ? "Гибкий" : "—"}</td><td>${esc(s.level)}</td><td>${s.required == null ? "—" : esc(s.required)}</td></tr>`;
  }).join("")}</tbody></table></div><p class="sub">Ключевые навыки обязательны. Прочерк в «Для цели» — навык не требуется.</p></section>`;
}
function renderSkills() {
  const p = state.profile;
  shell(`${heading("Цель и навыки", `${state.session.role === "hr" ? esc(p.employee.full_name) + " · " : ""}${esc(p.employee.role)} · ${esc(p.employee.grade)}`)}<div class="stack"><section class="panel"><h2>Карьерная цель</h2><form id="goal" class="goal-form"><label class="field">Роль<select name="role">${p.roles.map((r) => `<option ${r === p.target.role ? "selected" : ""}>${esc(r)}</option>`).join("")}</select></label><label class="field">Грейд<select name="grade">${["Junior", "Middle", "Senior", "Lead"].map((g) => `<option ${g === p.target.grade ? "selected" : ""}>${g}</option>`).join("")}</select></label><button class="btn">Сохранить цель</button></form></section>${profileSkills(p)}<details class="panel calculation"><summary>Как считается прогресс · ${p.progress}%</summary><p>Прогресс — доля требований цели, которой соответствуют текущие навыки. Уровень сверх требования не увеличивает процент.</p><p>Учтены завершённые активности после оценки ${date(p.employee.last_review_date)}. Повторное обучение повышает навык только до уровня, предусмотренного активностью; достигнутые уровни не снижаются.</p><p>Доступность активностей определяется текущей ролью и грейдом. Для соответствия цели нужно развить каждый ключевой навык. Решение о повышении принимает руководитель после оценки.</p></details></div>`);
  document.getElementById("goal").onsubmit = async (ev) => {
    ev.preventDefault();
    const button = ev.target.querySelector("button");
    button.disabled = true;
    try {
      state.profile = await api("/goal", {
        ...Object.fromEntries(new FormData(ev.target)),
        employee_id: p.employee.employee_id,
      });
      state.ai = null;
      state.request++;
      render();
      toast("Карьерная цель обновлена.");
    } catch (error) {
      toast(error.message);
      button.disabled = false;
    }
  };
}
function renderHistory() {
  const p = state.profile;
  shell(
    `${heading("История", state.session.role === "hr" ? esc(p.employee.full_name) : "")}<section class="panel"><div class="filters"><label for="history-filter">Показать</label><select id="history-filter"><option value="all">Все статусы</option>${Object.entries(
      labels,
    )
      .map(([k, v]) => `<option value="${k}">${v}</option>`)
      .join(
        "",
      )}</select></div><div class="table-wrap"><table><thead><tr><th>Активность</th><th>Дата</th><th>Статус</th><th>Выполнение</th></tr></thead><tbody id="history-body"></tbody></table></div></section>`,
  );
  function rows(filter) {
    document.getElementById("history-body").innerHTML =
      p.history
        .filter((r) => filter === "all" || r.status === filter)
        .map(
          (r) =>
            `<tr><td>${esc(r.title)}</td><td>${date(r.date)}</td><td><span class="tag ${r.status === "completed" ? "" : r.status === "in_progress" ? "blue" : "amber"}">${labels[r.status]}</span></td><td>${esc(r.completion_pct)}%</td></tr>`,
        )
        .join("") ||
      '<tr><td colspan="4">Активностей с этим статусом пока нет.</td></tr>';
  }
  rows("all");
  document.getElementById("history-filter").onchange = (e) =>
    rows(e.target.value);
}
function renderHR() {
  const h = state.hr;
  const count = h.employees.length;
  shell(`${heading("Сотрудники", `Данные на ${date(state.profile.today)}`)}${stats([
    [count, "Всего сотрудников"],
    [h.employees.filter((e) => !e.has_step && !e.goal_reached).length, "Без доступного шага"],
    [h.employees.filter((e) => e.inactive).length, "Без завершений за 90 дней"],
    [h.employees.filter((e) => e.goal_reached).length, "Достигли цели по навыкам"],
  ])}<section class="panel"><div class="filters"><input id="employee-search" class="search" placeholder="Имя, ID или роль" aria-label="Поиск сотрудника"><select id="employee-filter" aria-label="Фильтр сотрудников"><option value="all">Все сотрудники</option><option value="no_step">Нет доступного шага</option><option value="goal_reached">Цель достигнута</option><option value="inactive">Нет завершений 90 дней</option></select><button class="btn secondary" id="reset-employee-filters">Сбросить</button></div><p id="employee-count" class="sub" role="status"></p><div class="table-wrap"><table><thead><tr><th>Сотрудник</th><th>Роль / грейд</th><th>Прогресс</th><th>Статус</th></tr></thead><tbody id="employee-body"></tbody></table></div></section><div class="hr-grid"><section class="panel"><h2>Навыки для развития</h2><p class="sub">Сотрудники, не достигшие уровня своей цели</p>${h.gaps.slice(0, 7).map((g) => `<div class="skill"><div class="skill-label"><strong>${esc(g.name)}</strong><span>${g.count} чел.</span></div><div class="bar"><span style="width:${count ? (g.count / count) * 100 : 0}%"></span></div></div>`).join("") || '<p class="notice">Все сотрудники достигли требований своих целей.</p>'}</section><section class="panel"><h2>Участие в активностях</h2><p class="sub">За весь период данных</p><div class="table-wrap activity-table"><table><thead><tr><th>Активность</th><th>Завершено / всего</th><th>Пропуски и отказы</th></tr></thead><tbody>${h.events.slice().sort((a, b) => b.total - a.total).map((e) => `<tr><td>${esc(e.title)}</td><td>${e.completed} / ${e.total}</td><td>${e.missed}</td></tr>`).join("") || '<tr><td colspan="3" class="table-empty">Истории участия пока нет.</td></tr>'}</tbody></table></div></section></div><p class="footer-note">Достижение цели по навыкам не означает автоматическое повышение.</p>`);
  function rows() {
    const q = document.getElementById("employee-search").value.trim().toLowerCase();
    const f = document.getElementById("employee-filter").value;
    const employees = h.employees
        .filter(
          (e) =>
            (e.full_name + " " + e.employee_id + " " + e.role)
              .toLowerCase()
              .includes(q) &&
            (f === "all" ||
              (f === "no_step" && !e.has_step && !e.goal_reached) ||
              (f === "goal_reached" && e.goal_reached) ||
              (f === "inactive" && e.inactive)),
        );
    document.getElementById("employee-count").textContent = `Показано: ${employees.length} из ${count}`;
    document.getElementById("employee-body").innerHTML = employees.map(
          (e) =>
            `<tr><td><button class="btn text" data-employee="${esc(e.employee_id)}">${esc(e.full_name)}</button><br><small class="muted">${esc(e.employee_id)}</small></td><td>${esc(e.role)}<br><small class="muted">${esc(e.grade)}</small></td><td>${e.progress}%</td><td><span class="tag ${e.goal_reached ? "blue" : e.has_step ? "" : "amber"}">${e.goal_reached ? "Цель достигнута" : e.has_step ? "Шаг подобран" : "Нужен план с HR"}</span></td></tr>`,
        )
        .join("") || '<tr><td colspan="4" class="table-empty">Нет сотрудников по выбранным условиям. Измените поиск или нажмите «Сбросить».</td></tr>';
    document.querySelectorAll("[data-employee]").forEach(
      (b) =>
        (b.onclick = async () => {
          try {
            state.request++;
            state.profile = await api(
              "/profile?id=" + encodeURIComponent(b.dataset.employee),
            );
            state.ai = null;
            await navigate("home");
          } catch (error) {
            toast(error.message);
          }
        }),
    );
  }
  rows();
  document.getElementById("employee-search").oninput = rows;
  document.getElementById("employee-filter").onchange = rows;
  document.getElementById("reset-employee-filters").onclick = () => {
    document.getElementById("employee-search").value = "";
    document.getElementById("employee-filter").value = "all";
    rows();
  };
}
function renderImport() {
  shell(`${heading("Импорт данных")}<section class="panel"><p class="sub">Новые ID добавляются, существующие обновляются. При ошибке проверки изменения не сохраняются.</p><form id="import-form"><div class="upload-grid"><label class="upload-box field">Профили · JSON<input id="profiles-file" type="file" accept=".json,application/json"></label><label class="upload-box field">История участия · CSV<input id="history-file" type="file" accept=".csv,text/csv"></label></div><details class="import-text"><summary>Вставить данные текстом</summary><label class="field">Профили JSON<textarea id="profiles-text" rows="7" spellcheck="false" placeholder="{ &quot;employees&quot;: [...] }"></textarea></label><label class="field">История CSV<textarea id="history-text" rows="5" spellcheck="false" placeholder="record_id,employee_id,event_id,date,status,completion_pct"></textarea></label></details><details class="import-text"><summary>Требования к данным</summary><p>JSON: объект с employees, массив профилей или один профиль. CSV: исходные столбцы датасета, кодировка UTF-8. Можно загрузить один или оба типа данных.</p><p>Каталог активностей и требования к ролям не меняются. Рекомендации и аналитика обновятся автоматически.</p>${isDemo() ? '<p>Импорт не разрешает отправку профилей в облачную AI-модель.</p>' : ""}</details><p id="upload-summary" class="sub upload-summary" role="status">Файл или текст · до 4 МБ суммарно</p><button class="btn" type="submit">Проверить и загрузить</button><p id="import-result" role="status" class="notice" hidden></p><button class="btn secondary" id="open-imported-hr" type="button" hidden>К сотрудникам</button></form></section>`);
  const selectedFiles = () => [document.getElementById("profiles-file").files[0], document.getElementById("history-file").files[0]].filter(Boolean);
  const updateSummary = () => {
    const files = selectedFiles();
    const pasted = document.getElementById("profiles-text").value + document.getElementById("history-text").value;
    const bytes = files.reduce((sum, file) => sum + file.size, 0) + new TextEncoder().encode(pasted).length;
    document.getElementById("upload-summary").textContent = bytes
      ? `Выбрано: ${(bytes / 1000).toFixed(1)} КБ из 4 МБ`
      : "Файл или текст · до 4 МБ суммарно";
  };
  document.getElementById("profiles-file").onchange = updateSummary;
  document.getElementById("history-file").onchange = updateSummary;
  document.getElementById("profiles-text").oninput = updateSummary;
  document.getElementById("history-text").oninput = updateSummary;
  document.getElementById("open-imported-hr").onclick = () => navigate("hr");
  document.getElementById("import-form").onsubmit = async (ev) => {
    ev.preventDefault();
    const button = ev.target.querySelector("button"),
      out = document.getElementById("import-result");
    button.disabled = true;
    button.textContent = "Проверяем и загружаем…";
    out.hidden = true;
    out.className = "notice";
    out.setAttribute("role", "status");
    document.getElementById("open-imported-hr").hidden = true;
    try {
      const pf = document.getElementById("profiles-file").files[0],
        hf = document.getElementById("history-file").files[0];
      const pastedProfiles = document.getElementById("profiles-text").value.trim();
      const pastedHistory = document.getElementById("history-text").value.trim();
      if ((pf && pastedProfiles) || (hf && pastedHistory))
        throw new Error("Для каждого типа данных выберите один источник: файл или текст.");
      if (!pf && !hf && !pastedProfiles && !pastedHistory)
        throw new Error("Выберите файл или вставьте JSON/CSV.");
      if ((pf?.size || 0) + (hf?.size || 0) + new TextEncoder().encode(pastedProfiles + pastedHistory).length > 4_000_000)
        throw new Error("Общий размер файлов и текста должен быть не больше 4 МБ.");
      const result = await api("/import", {
        profiles: pf ? await pf.text() : pastedProfiles,
        history: hf ? await hf.text() : pastedHistory,
      });
      out.textContent = `Загружено профилей: ${result.profiles}, записей истории: ${result.records}.`;
      out.hidden = false;
      document.getElementById("open-imported-hr").hidden = false;
      state.ai = null;
      state.request++;
      state.profile = await api(
        "/profile?id=" + encodeURIComponent(state.profile.employee.employee_id),
      );
    } catch (error) {
      out.textContent = ["NotFoundError", "NotReadableError"].includes(error.name)
        ? "Не удалось прочитать файл. Выберите его заново или вставьте содержимое в поля JSON/CSV."
        : error.message;
      out.className = "notice notice-error";
      out.setAttribute("role", "alert");
      out.hidden = false;
    } finally {
      button.disabled = false;
      button.textContent = "Проверить и загрузить";
    }
  };
}
function render() {
  (
    ({
      home: renderHome,
      skills: renderSkills,
      history: renderHistory,
      hr: renderHR,
      import: renderImport,
    })[state.view] || renderHome
  )();
}
async function navigate(view) {
  try {
    if (view === "hr") state.hr = await api("/hr");
    state.view = view;
    render();
    window.scrollTo(0, 0);
    if (view === "home" && !state.ai) refreshAI();
  } catch (error) {
    toast(error.message);
  }
}
async function boot() {
  try {
    state.health = await api("/health");
    state.session = await api("/session");
    state.profile = await api("/profile");
    state.ai = null;
    state.view = state.session.role === "hr" ? "hr" : "home";
    await navigate(state.view);
  } catch (error) {
    renderLogin();
  }
}
boot();
