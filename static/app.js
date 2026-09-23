const app = document.getElementById("app");
const state = {
  session: null,
  profile: null,
  hr: null,
  view: "home",
  ai: null,
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
function toast(message) {
  const el = document.getElementById("toast");
  el.textContent = message;
  el.style.display = "block";
  clearTimeout(toastTimer);
  toastTimer = setTimeout(() => (el.style.display = "none"), 5500);
}
function renderLogin() {
  app.innerHTML = `<main class="login"><section class="login-story"><div class="brand"><img src="/favicon.svg" alt=""><div>Career Quest<small>ТВОЯ ТРАЕКТОРИЯ</small></div></div><div><div class="eyebrow">РАЗВИТИЕ СО СМЫСЛОМ</div><h1>Следующий шаг.<br><em>Твоя следующая версия.</em></h1><p>Соедини навыки, обучение и карьерную цель в понятный маршрут.</p><div class="login-steps"><div><b>01</b>Выбери цель</div><div><b>02</b>Найди свой шаг</div><div><b>03</b>Увидь прогресс</div></div></div><small>Career Quest · HackAlem AI · Halyk Bank track</small></section><section class="login-form"><form id="login"><h2>Начнём с тебя</h2><p class="muted intro">Войди в свой кабинет развития.</p><label class="field">Режим<select name="role" id="login-role"><option value="employee">Сотрудник</option><option value="hr">HR-специалист</option></select></label><label class="field" id="employee-field">ID сотрудника<input name="employee_id" value="E0001" autocomplete="username" required></label><label class="field">Пароль<input name="password" type="password" autocomplete="current-password" required placeholder="Введи пароль"></label><button class="btn" type="submit">Войти в Career Quest <span aria-hidden="true">↗</span></button><p id="login-error" class="error" role="alert"></p><div class="demo-hint">Демонстрационные доступы:<br>Сотрудник: <b>E0001</b> / <b>quest-demo</b><br>HR: <b>hr-quest-demo</b><br>Используются синтетические данные.</div></form></section></main>`;
  document.getElementById("login-role").onchange = (e) => {
    document.getElementById("employee-field").hidden = e.target.value === "hr";
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
  const p = state.profile,
    e = p?.employee;
  const isHR = state.session.role === "hr";
  const nav = [
    ["home", "Моя траектория"],
    ["skills", "Навыки и цель"],
    ["history", "История развития"],
    ...(isHR
      ? [
          ["hr", "Обзор HR"],
          ["import", "Загрузка данных"],
        ]
      : []),
  ];
  app.innerHTML = `<div class="shell"><aside class="sidebar"><div class="brand"><img src="/favicon.svg" alt=""><div>Career Quest<small>ТВОЯ ТРАЕКТОРИЯ</small></div></div><div class="nav-title">ПРОСТРАНСТВО РОСТА</div><nav class="nav" aria-label="Основная навигация">${nav.map(([key, label]) => `<button data-view="${key}" class="${state.view === key ? "active" : ""}" ${state.view === key ? 'aria-current="page"' : ""}>${icon(key)}${label}</button>`).join("")}</nav><div class="side-note"><b>Твой темп. Твоя цель.</b>Каждый шаг — это вклад в навыки. Выбирай то, что подходит именно тебе.</div><div class="sidebar-footer">HACKALEM AI · 2026<br><br>Демонстрационный прототип</div></aside><div class="content"><header class="topbar"><span class="breadcrumb">Рабочее пространство / <b>${nav.find((n) => n[0] === state.view)?.[1] || ""}</b></span><div class="account"><span class="tag neutral">${isHR ? "HR" : "Сотрудник"}</span><span class="avatar">${
    isHR
      ? "HR"
      : esc(
          e?.full_name
            .split(" ")
            .map((n) => n[0])
            .slice(0, 2)
            .join(""),
        )
  }</span><span class="account-name">${isHR ? "HR-кабинет" : esc(e?.full_name)}</span><button class="logout" id="logout">Выйти</button></div></header><main class="page">${body}</main></div></div>`;
  document
    .querySelectorAll("[data-view]")
    .forEach((b) => (b.onclick = () => navigate(b.dataset.view)));
  const navigation = document.querySelector(".nav");
  const activeItem = navigation.querySelector('[aria-current="page"]');
  if (activeItem && navigation.scrollWidth > navigation.clientWidth) {
    navigation.scrollLeft += activeItem.getBoundingClientRect().left -
      navigation.getBoundingClientRect().left -
      (navigation.clientWidth - activeItem.clientWidth) / 2;
  }
  document.getElementById("logout").onclick = async () => {
    await api("/logout", {});
    state.request++;
    state.session = null;
    state.ai = null;
    renderLogin();
  };
}
function heading(title, sub) {
  return `<div class="page-heading"><div><h1>${title}</h1><p>${sub}</p></div><span class="date-pill">Срез данных · ${date(state.profile?.today)}</span></div>`;
}
function stats(items) {
  return `<div class="stats stats-${items.length}">${items.map(([number, label, symbol]) => `<div class="stat"><div class="stat-icon" aria-hidden="true">${symbol}</div><div><b>${number}</b><span>${label}</span></div></div>`).join("")}</div>`;
}
function skillRows(gaps) {
  return gaps
    .map(
      (g) =>
        `<div class="skill"><div class="skill-label"><strong>${esc(g.name)}${g.critical ? '<small class="critical-mark">◆ ключевой</small>' : ""}</strong><span>${g.current} / ${g.required}</span></div><div class="bar" role="progressbar" aria-label="${esc(g.name)}" aria-valuemin="0" aria-valuemax="${g.required || 5}" aria-valuenow="${Math.min(g.current, g.required || 5)}"><span style="width:${Math.min(100, (g.current / (g.required || 5)) * 100)}%"></span></div></div>`,
    )
    .join("");
}
function quests() {
  const p = state.profile;
  const recs = state.ai?.recommendations || p.recommendations;
  if (!recs.length) return `<div class="empty">${esc(p.empty_reason)}</div>`;
  return `<div class="quest-grid">${recs
    .map(
      (r, i) =>
        `<article class="quest"><div class="quest-top"><span class="tag ${i === 0 ? "" : "neutral"}">${i === 0 ? "Следующий шаг" : types[r.type] || esc(r.type)}</span><span class="quest-number">0${i + 1}</span></div><h3>${esc(r.title)}</h3><div class="quest-meta"><span>◷ ${r.duration_hours} ч</span><span>${formats[r.format]}</span>${r.in_progress ? "<span>Уже начато</span>" : ""}</div><div class="impact">${
          r.gains.length
            ? r.gains
                .slice(0, 2)
                .map((g) => `${esc(g.name)} <b>${g.before} → ${g.after}</b>`)
                .join("<br>")
            : `Откроет следующий шаг: ${esc(r.unlocks[0])}`
        }<br><small>Прогресс к цели: ${p.progress}% → ${r.projected_progress}%</small></div><details><summary>Почему этот шаг подходит</summary><ul>${r.reasons.map((reason) => `<li>${esc(reason)}</li>`).join("")}</ul><p class="muted">${esc(r.description)}</p><p class="muted">${r.next_session ? "Ближайшая сессия: " + date(r.next_session) : "Можно начать в любое время"}</p></details><button class="btn ${i === 0 ? "" : "secondary"}" data-complete="${esc(r.event_id)}">Отметить выполненным <span aria-hidden="true">✓</span></button></article>`,
    )
    .join("")}</div>`;
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
  const p = state.profile,
    e = p.employee;
  const done = p.history.filter((r) => r.status === "completed");
  const closed = p.gaps.filter((g) => g.current >= g.required).length;
  shell(
    `${heading(`Твоя следующая глава`, `${esc(e.full_name)} · ${esc(e.role)} · ${esc(e.grade)}`)}<section class="hero"><div><div class="eyebrow">ТВОЙ КАРЬЕРНЫЙ МАРШРУТ</div><h2>${esc(p.target.role)} <span style="color:var(--lime)">${esc(p.target.grade)}</span></h2><p>Сделай рост видимым: развивай навыки, которые нужны для твоей цели, и двигайся в удобном темпе.</p><div class="hero-actions"><button class="btn light" id="show-skills">Посмотреть маршрут ↗</button><span class="tag">${p.critical_ready ? "Ключевые навыки готовы" : "Фокус на ключевых навыках"}</span></div></div><div class="progress-ring" style="--progress:${p.progress}" role="img" aria-label="${p.progress}% требований цели"><div><b>${p.progress}%</b><span>к карьерной цели</span></div></div></section>${stats(
      [
        [
          `${closed}<small class="muted"> / ${p.gaps.length}</small>`,
          "навыков на уровне цели",
          "◇",
        ],
        [done.length, "активностей завершено", "✓"],
        [
          p.gaps.filter((g) => g.critical && g.current < g.required).length,
          "ключевых навыков в фокусе",
          "↗",
        ],
      ],
    )}<section><div class="section-head"><div><h2>AI-навигатор: следующий шаг</h2><p>При подключении модель выбирает до трёх активностей по разрывам навыков и истории участия. Решение об участии — за вами.</p></div><button class="btn secondary" id="refresh-ai">✧ Обновить подбор</button></div><div id="ai-state" class="ai-state" role="status">${esc(state.ai?.message || (p.ai.configured ? "Модель подключена. Подбираем шаги…" : "Многофакторный подбор · LLM пока не подключена"))}</div><div id="quests">${quests()}</div></section><div class="lower-grid"><section class="panel"><div class="section-head"><h2>Навыки в фокусе</h2><button class="btn text" id="all-skills">Все навыки ↗</button></div><p class="sub">Текущий уровень / требования ${esc(p.target.grade)}</p>${skillRows(p.gaps.filter((g) => g.current < g.required).slice(0, 5)) || '<p class="notice">Все требования выбранной цели выполнены.</p>'}</section><section class="panel"><div class="section-head"><h2>Твой путь уже начался</h2></div><p class="sub">Последние завершённые активности</p><div class="timeline">${
      done
        .slice(0, 4)
        .map(
          (r) =>
            `<div class="timeline-item"><b>${esc(r.title)}</b><p>${date(r.date)} · Завершено</p></div>`,
        )
        .join("") ||
      '<div class="empty">Здесь появятся первые завершённые шаги.</div>'
    }</div><button class="btn text" id="all-history">Вся история ↗</button></section></div><p class="footer-note">Прогресс показывает соответствие навыков выбранной цели. Решение о повышении принимает руководитель после оценки.</p>`,
  );
  document.getElementById("show-skills").onclick = document.getElementById(
    "all-skills",
  ).onclick = () => navigate("skills");
  document.getElementById("all-history").onclick = () => navigate("history");
  document.getElementById("refresh-ai").onclick = () => refreshAI();
  bindCompletions();
}
async function refreshAI() {
  const request = ++state.request;
  const eid = state.profile.employee.employee_id;
  const button = document.getElementById("refresh-ai");
  if (button) {
    button.disabled = true;
    button.textContent = "Подбираем…";
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
      document.getElementById("ai-state").textContent =
        answer.message +
        (answer.latency_ms
          ? ` · ${(answer.latency_ms / 1000).toFixed(1)} с`
          : "");
      document.getElementById("quests").innerHTML = quests();
      bindCompletions();
    }
  } catch (error) {
    if (request === state.request) toast(error.message);
  } finally {
    if (request === state.request && button?.isConnected) {
      button.disabled = false;
      button.textContent = "✧ Обновить подбор";
    }
  }
}
function profileSkills(profile) {
  return `<section class="panel"><h2>Все навыки профиля</h2><p class="sub">Текущие уровни с учётом завершённых активностей. Прочерк означает, что навык не входит в требования выбранной цели.</p><div class="table-wrap"><table><thead><tr><th>Навык</th><th>Тип</th><th>Уровень</th><th>Требование цели</th></tr></thead><tbody>${profile.skill_details.map((s) => `<tr><td>${esc(s.name)}</td><td>${s.type === "hard" ? "Профессиональный" : "Гибкий"}</td><td>${esc(s.level)} / 5</td><td>${s.required == null ? "—" : esc(s.required)}</td></tr>`).join("")}</tbody></table></div></section>`;
}
function renderSkills() {
  const p = state.profile;
  shell(
    `${heading("Твоя цель и навыки", "Меняй цель и смотри, какие навыки приблизят тебя к ней.")}<section class="panel"><h2>Куда хочешь двигаться?</h2><form id="goal" class="goal-form"><label class="field">Роль<select name="role">${p.roles.map((r) => `<option ${r === p.target.role ? "selected" : ""}>${esc(r)}</option>`).join("")}</select></label><label class="field">Грейд<select name="grade">${["Junior", "Middle", "Senior", "Lead"].map((g) => `<option ${g === p.target.grade ? "selected" : ""}>${g}</option>`).join("")}</select></label><button class="btn">Сохранить цель</button></form><div class="step-path">${["Junior", "Middle", "Senior", "Lead"].map((g) => `<div class="${g === p.target.grade ? "selected" : ""}"><b>${g}</b><span>${g === p.employee.grade ? "Текущий грейд" : g === p.target.grade ? "Выбранная цель" : "Уровень развития"}</span></div>`).join("")}</div><p class="sub">${esc(p.employee.role)} → ${esc(p.target.role)}. При смене роли доступность мероприятий всё ещё определяется текущей ролью и грейдом.</p></section><div class="lower-grid"><section class="panel"><h2>Требования выбранной цели</h2><p class="sub">◆ Ключевые навыки обязательны для соответствия грейду.</p>${skillRows(p.gaps)}</section><section class="panel"><h2>Как считается прогресс</h2><p class="notice">${p.progress}% — сумма достигнутых уровней, ограниченных требованиями цели, делённая на сумму требуемых уровней.</p><p class="sub">После завершения активности навык растёт на gain, но не выше max_level. Уже достигнутый более высокий уровень не снижается.</p><br><p class="sub">Учтены завершения после последней оценки ${date(p.employee.last_review_date)}. Ранее завершённые активности уже отражены в профиле.</p><br><h3>${p.critical_ready ? "Ключевые навыки соответствуют цели" : "Остались ключевые разрывы"}</h3><p class="sub">Даже высокий общий процент не заменяет достижения каждого ключевого навыка.</p><br><button class="btn secondary" id="back-home">К рекомендованным шагам</button></section></div><br>${profileSkills(p)}`,
  );
  document.getElementById("back-home").onclick = () => navigate("home");
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
    `${heading("История развития", `${esc(p.employee.full_name)} · Все активности и результаты`)}<section class="panel"><div class="filters"><label for="history-filter">Показать</label><select id="history-filter"><option value="all">Все статусы</option>${Object.entries(
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
  shell(
    `${heading("Развитие команды", "Компетенции, участие и сотрудники, которым нужна поддержка.")}${stats(
      [
        [count, "сотрудников в обзоре", "◇"],
        [
          h.employees.filter((e) => !e.has_step && !e.goal_reached).length,
          "без доступного шага",
          "↗",
        ],
        [
          h.employees.filter((e) => e.inactive).length,
          "без завершений за 90 дней",
          "◷",
        ],
        [h.employees.filter((e) => e.goal_reached).length, "достигли цели по навыкам", "✓"],
      ],
    )}<div class="hr-grid"><section class="panel"><h2>Где нужна поддержка</h2><p class="sub">Количество сотрудников с разрывом до своей цели</p>${h.gaps
      .slice(0, 7)
      .map(
        (g) =>
          `<div class="skill"><div class="skill-label"><strong>${esc(g.name)}</strong><span>${g.count} чел.</span></div><div class="bar"><span style="width:${(g.count / count) * 100}%"></span></div></div>`,
      )
      .join(
        "",
      ) || '<p class="notice">Все сотрудники достигли требований своих целей по навыкам.</p>'}</section><section class="panel"><h2>Участие в активностях</h2><p class="sub">Завершено / всего участий за период датасета</p><div class="table-wrap activity-table"><table><thead><tr><th>Активность</th><th>Завершено</th><th>Пропуски и отказы</th></tr></thead><tbody>${h.events
      .slice()
      .sort((a, b) => b.total - a.total)
      .map(
        (e) =>
          `<tr><td>${esc(e.title)}</td><td>${e.completed} / ${e.total}</td><td>${e.missed}</td></tr>`,
      )
      .join(
        "",
      ) || '<tr><td colspan="3" class="table-empty">История участия пока пуста. Загрузите CSV в разделе «Загрузка данных».</td></tr>'}</tbody></table></div></section></div><section class="panel"><h2>Сотрудники</h2><p class="sub">Достижение цели означает соответствие навыков, а не автоматическое повышение. Данные о вовлечённости доступны только HR.</p><div class="filters"><input id="employee-search" class="search" placeholder="Поиск по имени, ID или роли" aria-label="Поиск сотрудника"><select id="employee-filter" aria-label="Фильтр сотрудников"><option value="all">Все сотрудники</option><option value="no_step">Нет следующего шага</option><option value="goal_reached">Цель достигнута</option><option value="inactive">Нет завершений 90 дней</option></select><button class="btn secondary" id="reset-employee-filters">Сбросить</button></div><p id="employee-count" class="sub" role="status"></p><div class="table-wrap"><table><thead><tr><th>Сотрудник</th><th>Роль / грейд</th><th>К цели</th><th>Статус развития</th></tr></thead><tbody id="employee-body"></tbody></table></div></section>`,
  );
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
  shell(
    `${heading("Загрузка данных", "Добавь проверочные профили и историю участия в формате датасета.")}<section class="panel"><h2>Новые данные — тот же маршрут</h2><p class="sub">Новые ID будут добавлены, совпадающие — обновлены. При ошибке проверки изменения не сохраняются.</p><form id="import-form"><div class="upload-grid"><label class="upload-box field">Профили сотрудников · JSON<p>Объект с employees, массив профилей или один профиль.</p><input id="profiles-file" type="file" accept=".json,application/json"></label><label class="upload-box field">История участия · CSV<p>Исходные столбцы датасета, кодировка UTF-8.</p><input id="history-file" type="file" accept=".csv,text/csv"></label></div><details class="import-text"><summary>Вставить JSON / CSV текстом</summary><p class="sub">Можно использовать вместо файлов. Данные проходят ту же проверку.</p><label class="field">Профили JSON<textarea id="profiles-text" rows="7" spellcheck="false" placeholder="{ &quot;employees&quot;: [...] }"></textarea></label><label class="field">История CSV<textarea id="history-text" rows="5" spellcheck="false" placeholder="record_id,employee_id,event_id,date,status,completion_pct"></textarea></label></details><p id="upload-summary" class="sub upload-summary" role="status">Выберите JSON, CSV или оба файла. Общий размер — до 4 МБ.</p><button class="btn" type="submit">Проверить и загрузить</button><p id="import-result" role="status" class="notice" hidden></p><button class="btn secondary" id="open-imported-hr" type="button" hidden>Открыть обзор HR ↗</button></form></section><p class="footer-note">Каталог мероприятий и требования к ролям остаются исходными. После импорта рекомендации и HR-обзор пересчитываются автоматически.</p>`,
  );
  const selectedFiles = () => [document.getElementById("profiles-file").files[0], document.getElementById("history-file").files[0]].filter(Boolean);
  const updateSummary = () => {
    const files = selectedFiles();
    const pasted = document.getElementById("profiles-text").value + document.getElementById("history-text").value;
    const bytes = files.reduce((sum, file) => sum + file.size, 0) + new TextEncoder().encode(pasted).length;
    document.getElementById("upload-summary").textContent = bytes
      ? `Файлов: ${files.length}; общий объём файлов и текста: ${(bytes / 1000).toFixed(1)} КБ. Готово к проверке.`
      : "Выберите файлы или вставьте JSON/CSV. Общий размер — до 4 МБ.";
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
        throw new Error("Выберите файл или вставьте текст JSON/CSV ниже.");
      if ((pf?.size || 0) + (hf?.size || 0) + new TextEncoder().encode(pastedProfiles + pastedHistory).length > 4_000_000)
        throw new Error("Размер файлов должен быть меньше 4 МБ.");
      const result = await api("/import", {
        profiles: pf ? await pf.text() : pastedProfiles,
        history: hf ? await hf.text() : pastedHistory,
      });
      out.textContent = `Загружено профилей: ${result.profiles}, записей истории: ${result.records}. Открой «Обзор HR», чтобы выбрать сотрудника.`;
      out.hidden = false;
      document.getElementById("open-imported-hr").hidden = false;
      state.ai = null;
      state.request++;
      state.profile = await api(
        "/profile?id=" + encodeURIComponent(state.profile.employee.employee_id),
      );
    } catch (error) {
      out.textContent = ["NotFoundError", "NotReadableError"].includes(error.name)
        ? "Не удалось прочитать файл. Выберите его заново или вставьте содержимое в поля JSON/CSV ниже."
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
