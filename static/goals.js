/* Goal choices are calculated by the server; this view only filters and selects them. */
const CareerGoals = (() => {
  const entries = (value) => Array.isArray(value) ? value : [];
  const normalize = (value) => String(value ?? "").trim().toLocaleLowerCase("ru-RU");
  const progress = (value) => Math.max(0, Math.min(100, Number(value) || 0));
  const sameGoal = (a, b) => a?.role === b?.role && a?.grade === b?.grade;
  const gradeOrder = ["Junior", "Middle", "Senior", "Lead"];

  function skillRow(skill) {
    const achieved = Number(skill.current) >= Number(skill.required);
    return `<li class="goal-catalog-skill"><div><span>${esc(skill.name)}</span>${skill.critical ? '<small class="critical-mark">Ключевой</small>' : ""}</div><span class="goal-catalog-level">${esc(skill.current)} / ${esc(skill.required)}<small>${achieved ? "На уровне цели" : "Нужно развить"}</small></span></li>`;
  }

  function card(option, index, activeTarget) {
    const selected = sameGoal(option, activeTarget);
    const skills = entries(option.skills).slice().sort((a, b) => {
      const aOpen = Number(a.current) < Number(a.required);
      const bOpen = Number(b.current) < Number(b.required);
      return Number(Boolean(b.critical) && bOpen) - Number(Boolean(a.critical) && aOpen) || Number(bOpen) - Number(aOpen) || Number(Boolean(b.critical)) - Number(Boolean(a.critical));
    });
    const value = progress(option.progress);
    return `<article class="goal-catalog-card${selected ? " is-selected" : ""}" aria-label="${esc(option.role)} · ${esc(option.grade)}">
      <div class="goal-catalog-card-head"><span class="tag ${selected ? "" : "neutral"}">${esc(option.grade)}</span>${selected ? '<span class="goal-catalog-selected">Текущая цель</span>' : ""}</div>
      <h3>${esc(option.role)}</h3>
      <div class="goal-catalog-progress"><div class="skill-label"><span>Соответствие навыков</span><strong>${value}%</strong></div><div class="bar" role="progressbar" aria-label="${esc(option.role)} ${esc(option.grade)}: соответствие навыков" aria-valuemin="0" aria-valuemax="100" aria-valuenow="${value}"><span style="width:${value}%"></span></div></div>
      <p class="goal-catalog-summary">Требований: <strong>${esc(option.skill_count)}</strong> · Разрывов: <strong>${esc(option.gaps_count)}</strong>${Number(option.critical_gaps) > 0 ? `<br>Из них ключевых: <strong>${esc(option.critical_gaps)}</strong>` : ""}</p>
      ${skills.length ? `<ul class="goal-catalog-skills">${skills.slice(0, 3).map(skillRow).join("")}</ul>${skills.length > 3 ? `<details class="goal-catalog-more"><summary>Ещё требований: ${skills.length - 3}</summary><ul class="goal-catalog-skills">${skills.slice(3).map(skillRow).join("")}</ul></details>` : ""}` : '<p class="sub">Требования к навыкам не указаны.</p>'}
      <button class="btn ${selected ? "secondary" : ""}" type="button" data-goal-choice="${index}"${selected ? " disabled" : ""}>${selected ? "Текущая цель" : "Выбрать цель"}</button>
    </article>`;
  }

  function markup(profile) {
    const options = entries(profile.goal_options);
    const roles = [...new Set(options.map((option) => option.role))].sort((a, b) => a.localeCompare(b, "ru"));
    const grades = [...new Set(options.map((option) => option.grade))].sort((a, b) => {
      const ai = gradeOrder.indexOf(a), bi = gradeOrder.indexOf(b);
      return (ai < 0 ? gradeOrder.length : ai) - (bi < 0 ? gradeOrder.length : bi) || a.localeCompare(b, "ru");
    });
    const defaultGrade = grades.includes(profile.target?.grade) ? profile.target.grade : "all";
    return `<section class="panel goal-catalog" id="goal-catalog" aria-labelledby="goal-catalog-heading">
      <div class="section-head"><div><h2 id="goal-catalog-heading">Карьерные траектории</h2><p>Сравните требования к ролям и выберите направление развития.</p></div><span class="tag neutral">Вариантов: ${options.length}</span></div>
      <p class="sub">Активная цель: <strong>${esc(profile.target?.role)} · ${esc(profile.target?.grade)}</strong>. Одновременно действует одна цель; её можно изменить.</p>
      ${options.length ? `<div class="workspace-toolbar goal-catalog-toolbar"><label class="field" for="goal-catalog-search">Поиск роли<input id="goal-catalog-search" type="search" placeholder="Название роли" autocomplete="off"></label><label class="field" for="goal-catalog-role">Роль<select id="goal-catalog-role"><option value="all">Все роли</option>${roles.map((role) => `<option value="${esc(role)}">${esc(role)}</option>`).join("")}</select></label><label class="field" for="goal-catalog-grade">Грейд<select id="goal-catalog-grade"><option value="all"${defaultGrade === "all" ? " selected" : ""}>Все грейды</option>${grades.map((grade) => `<option value="${esc(grade)}"${grade === defaultGrade ? " selected" : ""}>${esc(grade)}</option>`).join("")}</select></label><button class="btn secondary" type="button" id="goal-catalog-reset">Сбросить фильтры</button></div><p id="goal-catalog-count" class="workspace-count" role="status"></p><div class="goal-catalog-grid" id="goal-catalog-grid"></div>` : '<p class="empty">В каталоге пока нет вариантов карьерных целей.</p>'}
      <p class="footer-note">Уровни указаны как «сейчас / требуется». Оценка навыков помогает выбрать направление и не означает автоматического повышения или перехода на другую роль.</p>
    </section>`;
  }

  function bind(profile, onSelect) {
    const root = document.getElementById("goal-catalog");
    const search = document.getElementById("goal-catalog-search");
    const role = document.getElementById("goal-catalog-role");
    const grade = document.getElementById("goal-catalog-grade");
    const reset = document.getElementById("goal-catalog-reset");
    const count = document.getElementById("goal-catalog-count");
    const grid = document.getElementById("goal-catalog-grid");
    if (!root || !search || !role || !grade || !reset || !count || !grid) return;
    const options = entries(profile.goal_options);
    let activeTarget = profile.target;
    let busy = false;

    function renderCards() {
      const query = normalize(search.value);
      const shown = options.map((option, index) => ({ option, index })).filter(({ option }) =>
        normalize(option.role).includes(query) &&
        (role.value === "all" || option.role === role.value) &&
        (grade.value === "all" || option.grade === grade.value)
      );
      count.textContent = `Показано целей: ${shown.length} из ${options.length}.`;
      grid.innerHTML = shown.map(({ option, index }) => card(option, index, activeTarget)).join("") || '<p class="empty goal-catalog-empty">По выбранным условиям целей нет. Измените фильтры или нажмите «Сбросить фильтры».</p>';
      grid.querySelectorAll("[data-goal-choice]").forEach((button) => {
        button.onclick = async () => {
          const option = options[Number(button.dataset.goalChoice)];
          if (busy || !option || sameGoal(option, activeTarget)) return;
          busy = true;
          root.querySelectorAll("input, select, button").forEach((control) => { control.disabled = true; });
          button.textContent = "Сохраняем цель…";
          try {
            await onSelect({ role: option.role, grade: option.grade });
            activeTarget = { role: option.role, grade: option.grade };
          } catch (error) {
            toast(error.message || "Не удалось изменить цель. Попробуйте ещё раз.");
          } finally {
            busy = false;
            if (root.isConnected) {
              [search, role, grade, reset].forEach((control) => { control.disabled = false; });
              renderCards();
            }
          }
        };
      });
    }

    search.oninput = renderCards;
    role.onchange = renderCards;
    grade.onchange = renderCards;
    reset.onclick = () => {
      search.value = "";
      role.value = "all";
      grade.value = "all";
      renderCards();
    };
    renderCards();
  }

  return { markup, bind };
})();
