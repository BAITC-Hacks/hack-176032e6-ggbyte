/* HR views use only the existing /api/hr response. No profile data is changed. */
const HRViews = {
  markup(h, today) {
    const count = h.employees.length;
    const reached = h.employees.filter(e => e.goal_reached).length;
    const blocked = h.employees.filter(e => !e.has_step && !e.goal_reached).length;
    const active = count - reached - blocked;
    const inactive = h.employees.filter(e => e.inactive).length;
    const roles = [...new Set(h.employees.map(e => e.role))].sort((a, b) => a.localeCompare(b, 'ru'));
    const segments = [['ready', reached, 'Цель достигнута'], ['active', active, 'Есть следующий шаг'], ['blocked', blocked, 'Нужен план с HR']];
    const metrics = [['all', count, 'Всего сотрудников'], ['no_step', blocked, 'Без доступного шага'], ['inactive', inactive, 'Без завершений за 90 дней'], ['goal_reached', reached, 'Достигли цели по навыкам']];
    return `${heading('Развитие команды', `Обзор HR · данные на ${date(today)}`)}
      <div class="page-actions"><p class="section-subtitle">Найдите сотрудников, которым нужна помощь с маршрутом, и оцените участие в обучении.</p><button class="btn secondary" id="hr-import">Импортировать данные</button></div>
      <div class="stats stats-4">${metrics.map(([filter, value, label]) => `<button type="button" class="stat hr-metric-button" data-hr-filter="${filter}" aria-pressed="${filter === 'all'}"><b>${value}</b><span>${label}</span><small>Показать сотрудников →</small></button>`).join('')}</div>
      <section class="panel coverage-panel"><div class="section-head"><div><h2>Состояние карьерных маршрутов</h2><p class="sub">Каждый сотрудник входит в одну из трёх групп.</p></div><strong>${count ? Math.round((active + reached) / count * 100) : 0}% с шагом или достигнутой целью</strong></div>
        <div class="coverage-bar" role="img" aria-label="${segments.map(([, n, label]) => `${label}: ${n}`).join('; ')}">${segments.filter(([, n]) => n > 0).map(([key, n]) => `<span class="coverage-segment ${key}" style="flex:${n}" aria-hidden="true"></span>`).join('')}</div>
        <div class="inline-metrics">${segments.map(([, n, label]) => `<div class="metric-item"><strong>${n}</strong><span>${label}</span></div>`).join('')}</div>
      </section>
      <section class="panel" id="hr-staff"><div class="section-head"><h2>Сотрудники</h2><span class="sub">Откройте профиль, чтобы изучить навыки и рекомендации</span></div>
        <div class="workspace-toolbar"><label class="field">Поиск сотрудника<input id="employee-search" placeholder="Имя, ID или роль"></label>
          <label class="field">Состояние<select id="employee-filter"><option value="all">Все сотрудники</option><option value="no_step">Нет доступного шага</option><option value="has_step">Есть следующий шаг</option><option value="goal_reached">Цель достигнута</option><option value="inactive">Нет завершений 90 дней</option></select></label>
          <label class="field">Роль сотрудника<select id="employee-role"><option value="all">Все роли</option>${roles.map(role => `<option value="${esc(role)}">${esc(role)}</option>`).join('')}</select></label>
          <label class="field">Порядок сотрудников<select id="employee-sort"><option value="name">По имени</option><option value="role">По роли</option><option value="attention">Сначала без шага</option></select></label>
          <button class="btn secondary" id="reset-employee-filters" type="button">Сбросить фильтры</button></div>
        <p id="employee-count" class="workspace-count" role="status"></p><div class="table-wrap"><table><thead><tr><th>Сотрудник</th><th>Роль / грейд</th><th>Прогресс</th><th>Состояние</th></tr></thead><tbody id="employee-body"></tbody></table></div>
      </section>
      <div class="hr-grid"><section class="panel"><div class="section-head"><h2>Навыки для развития</h2><span class="tag neutral">${h.gaps.length} навыков в сводке</span></div><p class="sub">Самые частые разрывы до выбранной цели. Число — количество сотрудников с таким разрывом.</p>
        ${h.gaps.map(g => `<div class="skill"><div class="skill-label"><strong>${esc(g.name)}</strong><span>${g.count} чел.</span></div><div class="bar" role="progressbar" aria-label="${esc(g.name)}: сотрудников с разрывом" aria-valuemin="0" aria-valuemax="${Math.max(count, 1)}" aria-valuenow="${g.count}"><span style="width:${count ? g.count / count * 100 : 0}%"></span></div></div>`).join('') || '<p class="notice">В сводке нет незакрытых разрывов навыков.</p>'}
      </section><section class="panel"><h2>Участие в активностях</h2><p class="sub">Записи за весь период данных; один сотрудник может участвовать несколько раз.</p>
        <div class="inline-metrics"><div class="metric-item"><strong>${h.events.reduce((n, e) => n + e.completed, 0)}</strong><span>Завершений</span></div><div class="metric-item"><strong>${h.events.reduce((n, e) => n + e.missed, 0)}</strong><span>Пропусков и отказов</span></div><div class="metric-item"><strong>${h.events.filter(e => e.total === 0).length}</strong><span>Активностей без участия</span></div></div>
        <div class="workspace-toolbar"><label class="field">Найти активность<input id="activity-search" placeholder="Название активности"></label><label class="field">Участие<select id="activity-filter"><option value="all">Все активности</option><option value="unused">Без участия</option><option value="missed">Есть пропуски / отказы</option><option value="completed">Есть завершения</option></select></label><button class="btn secondary" id="reset-activity-filters" type="button">Сбросить</button></div>
        <p id="activity-count" class="workspace-count" role="status"></p><div class="table-wrap activity-table"><table><thead><tr><th>Активность</th><th>Завершено / записей</th><th>Пропуски и отказы</th></tr></thead><tbody id="activity-body"></tbody></table></div>
      </section></div><p class="footer-note">Это обзор потребностей в развитии. Достижение цели по навыкам не означает автоматическое повышение.</p>`;
  },
  bind(h, openEmployee, openImport) {
    const el = id => document.getElementById(id);
    const controls = ['employee-search', 'employee-filter', 'employee-role', 'employee-sort'];
    const matchesState = (e, filter) => filter === 'all' || (filter === 'no_step' && !e.has_step && !e.goal_reached) || (filter === 'has_step' && e.has_step && !e.goal_reached) || (filter === 'goal_reached' && e.goal_reached) || (filter === 'inactive' && e.inactive);
    function rows() {
      const query = el('employee-search').value.trim().toLocaleLowerCase('ru');
      const filter = el('employee-filter').value;
      const role = el('employee-role').value;
      const order = el('employee-sort').value;
      const staff = h.employees.filter(e => `${e.full_name} ${e.employee_id} ${e.role}`.toLocaleLowerCase('ru').includes(query) && matchesState(e, filter) && (role === 'all' || role === e.role));
      staff.sort((a, b) => {
        if (order === 'attention') {
          const diff = Number(!b.has_step && !b.goal_reached) - Number(!a.has_step && !a.goal_reached);
          if (diff) return diff;
        }
        if (order === 'role') {
          const diff = a.role.localeCompare(b.role, 'ru');
          if (diff) return diff;
        }
        return a.full_name.localeCompare(b.full_name, 'ru') || a.employee_id.localeCompare(b.employee_id);
      });
      el('employee-count').textContent = `Показано: ${staff.length} из ${h.employees.length}`;
      el('employee-body').innerHTML = staff.map(e => `<tr><td><button class="btn text" data-employee="${esc(e.employee_id)}">${esc(e.full_name)}</button><br><small class="muted">${esc(e.employee_id)}</small></td><td>${esc(e.role)}<br><small class="muted">${esc(e.grade)}</small></td><td>${e.progress}%</td><td><span class="tag ${e.goal_reached ? 'blue' : e.has_step ? '' : 'amber'}">${e.goal_reached ? 'Цель достигнута' : e.has_step ? 'Шаг подобран' : 'Нужен план с HR'}</span>${e.inactive ? '<p class="sub">Нет завершений за 90 дней</p>' : ''}</td></tr>`).join('') || '<tr><td colspan="4" class="table-empty">Нет сотрудников по этим условиям. Измените поиск или сбросьте фильтры.</td></tr>';
      document.querySelectorAll('[data-employee]').forEach(button => {
        button.onclick = () => openEmployee(button.dataset.employee);
      });
      document.querySelectorAll('[data-hr-filter]').forEach(button => button.setAttribute('aria-pressed', String(button.dataset.hrFilter === filter && !query && role === 'all')));
    }
    controls.forEach(id => el(id).addEventListener(id.endsWith('search') ? 'input' : 'change', rows));
    function clearStaff() {
      el('employee-search').value = '';
      el('employee-filter').value = 'all';
      el('employee-role').value = 'all';
      el('employee-sort').value = 'name';
    }
    el('reset-employee-filters').onclick = () => { clearStaff(); rows(); };
    document.querySelectorAll('[data-hr-filter]').forEach(button => {
      button.onclick = () => {
        clearStaff();
        el('employee-filter').value = button.dataset.hrFilter;
        rows();
        el('hr-staff').scrollIntoView({ block: 'start' });
        el('employee-search').focus({ preventScroll: true });
      };
    });
    function activities() {
      const query = el('activity-search').value.trim().toLocaleLowerCase('ru');
      const filter = el('activity-filter').value;
      const events = h.events.filter(e => e.title.toLocaleLowerCase('ru').includes(query) && (filter === 'all' || (filter === 'unused' && e.total === 0) || (filter === 'missed' && e.missed > 0) || (filter === 'completed' && e.completed > 0))).sort((a, b) => b.total - a.total || a.title.localeCompare(b.title, 'ru'));
      el('activity-count').textContent = `Показано активностей: ${events.length} из ${h.events.length}`;
      el('activity-body').innerHTML = events.map(e => `<tr><td>${esc(e.title)}</td><td>${e.completed} / ${e.total}</td><td>${e.missed}</td></tr>`).join('') || '<tr><td colspan="3" class="table-empty">По этим условиям активностей нет. Попробуйте другой фильтр.</td></tr>';
    }
    el('activity-search').oninput = activities;
    el('activity-filter').onchange = activities;
    el('reset-activity-filters').onclick = () => { el('activity-search').value = ''; el('activity-filter').value = 'all'; activities(); };
    el('hr-import').onclick = openImport;
    rows();
    activities();
  },
};
