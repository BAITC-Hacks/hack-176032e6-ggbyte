"""Auditable candidate selection and skill projection; no network or UI dependencies."""
from datetime import date

GRADES = ['Junior', 'Middle', 'Senior', 'Lead']
NEGATIVE = {'no_show', 'declined', 'dropped'}


def history_sort_key(row):
    """Keep legacy ordering, then apply same-day interactive completions in sequence."""
    order = row.get('completion_order', 0)
    # CSV strings, booleans and invalid values do not become trusted sequence numbers.
    if type(order) is not int or order <= 0:
        order = 0
    return row['date'], order, row['record_id']


def target_for(employee, profiles):
    goal = employee.get('career_goal')
    role = goal['target_role'] if goal else employee['role']
    grade = goal['target_grade'] if goal else GRADES[min(3, GRADES.index(employee['grade']) + 1)]
    return next(p for p in profiles if p['role'] == role and p['grade'] == grade)


def apply_gain(levels, event):
    result = dict(levels)
    for gain in event['develops_skills']:
        sid = gain['skill_id']
        old = result.get(sid, 0)
        result[sid] = max(old, min(5, gain['max_level'], old + gain['gain']))
    return result


def current_skills(employee, history, events, today):
    levels = dict(employee['skills'])
    seen = set()
    for row in sorted(history, key=history_sort_key):
        if row['employee_id'] != employee['employee_id'] or row['status'] != 'completed':
            continue
        eid = row['event_id']
        if not employee['last_review_date'] < row['date'] <= today:
            continue
        if eid in seen and eid != 'EV_036':
            continue
        seen.add(eid)
        levels = apply_gain(levels, events[eid])
    return levels


def progress(levels, target):
    required = target['required_skills']
    total = sum(required.values())
    if not total or all(levels.get(s, 0) >= n for s, n in required.items()):
        return 100
    # Rounding must not label an unfinished goal as achieved.
    return min(99, round(100 * sum(min(levels.get(s, 0), n) for s, n in required.items()) / total))


def eligible(event, employee, levels, history, today):
    if event['mandatory']:
        return False
    if employee['role'] not in event['target_roles'] or employee['grade'] not in event['target_grades']:
        return False
    if any(levels.get(s, 0) < n for s, n in event['prerequisites'].items()):
        return False
    if event['event_id'] != 'EV_036' and any(r['event_id'] == event['event_id'] and r['status'] == 'completed' for r in history):
        return False
    if any(r['event_id'] == event['event_id'] and r['status'] == 'completed' and r['date'] == today for r in history):
        return False
    return event['format'] == 'self_paced' or any(d >= today for d in event['upcoming_sessions'])


def recommend(employee, history, events, skills, profiles, today):
    personal = sorted((r for r in history if r['employee_id'] == employee['employee_id'] and r['date'] <= today), key=history_sort_key)
    levels = current_skills(employee, personal, events, today)
    target = target_for(employee, profiles)
    candidates = []
    for event in events.values():
        if not eligible(event, employee, levels, personal, today):
            continue
        after = apply_gain(levels, event)
        gains = []
        benefit = 0
        for sid, required in target['required_skills'].items():
            delta = min(after.get(sid, 0), required) - min(levels.get(sid, 0), required)
            if delta > 0:
                critical = sid in target['critical_skills']
                benefit += delta * (4 if critical else 1)
                gains.append({'skill_id': sid, 'name': skills[sid]['name'], 'before': levels.get(sid, 0), 'after': after[sid], 'required': required, 'critical': critical})
        # A prerequisite-building activity is useful even without an immediate target gain.
        unlocks = []
        if not gains:
            for other in events.values():
                if other['event_id'] == event['event_id'] or not eligible(other, employee, after, personal, today):
                    continue
                if eligible(other, employee, levels, personal, today):
                    continue
                projected = apply_gain(after, other)
                if any(min(projected.get(s, 0), n) > min(after.get(s, 0), n) for s, n in target['required_skills'].items()):
                    unlocks.append(other['title'])
            if not unlocks:
                continue
            benefit = 0.6
        related = [r for r in personal if events[r['event_id']]['type'] == event['type'] or any(g['skill_id'] in {x['skill_id'] for x in event['develops_skills']} for g in events[r['event_id']]['develops_skills'])]
        recent = related[-12:]
        missed = sum(r['status'] in NEGATIVE for r in recent)
        finished = sum(r['status'] == 'completed' for r in recent)
        participation = (finished + 2) / (len(recent) + 4)
        in_progress = any(r['event_id'] == event['event_id'] and r['status'] == 'in_progress' for r in personal)
        format_fit = 0.5 if employee.get('work_format') == 'remote' and event['format'] != 'offline' else 0
        score = benefit * 10 + participation * 3 - missed * 2 + (2 if in_progress else 0) + format_fit - event['duration_hours'] * 0.08
        gap_text = '; '.join(f"{g['name']}: {g['before']} → {g['after']} при цели {g['required']}" + (' (критический навык)' if g['critical'] else '') for g in gains)
        reasons = [
            f"Ваш профиль: {employee['role']} · {employee['grade']}. Активность доступна для вашей роли и грейда.",
            f"Цель: {target['role']} · {target['grade']}. " + (gap_text if gains else 'Шаг открывает доступ к: ' + ', '.join(unlocks)),
            f"История похожих активностей: завершено {finished}, пропущено или прекращено {missed} из последних {len(recent)} участий." if recent else 'В истории нет похожих активностей: используем нейтральную оценку участия.',
        ]
        if missed:
            reasons.append('Пропуски снизили приоритет этого шага; это сигнал подобрать удобный формат, а не оценка сотрудника.')
        candidates.append({**event, 'score': round(score, 2), 'gains': gains, 'unlocks': unlocks, 'reasons': reasons,
                           'projected_progress': progress(after, target), 'in_progress': in_progress,
                           'participation': {'completed': finished, 'missed': missed, 'total': len(recent)},
                           'next_session': next(iter(sorted(d for d in event['upcoming_sessions'] if d >= today)), None)})
    candidates.sort(key=lambda c: (-c['score'], c['event_id']))
    gaps = [{'skill_id': s, 'name': skills[s]['name'], 'current': levels.get(s, 0), 'required': n,
             'critical': s in target['critical_skills']} for s, n in target['required_skills'].items()]
    gaps.sort(key=lambda g: (not g['critical'], -(g['required'] - g['current']), g['name']))
    return {'employee': employee, 'target': target, 'skills': levels, 'gaps': gaps, 'progress': progress(levels, target),
            'critical_ready': all(levels.get(s, 0) >= target['required_skills'][s] for s in target['critical_skills']),
            'recommendations': candidates[:3], 'candidates': candidates, 'history': personal,
            'empty_reason': 'Требования цели выполнены. Обсудите оценку и следующую цель с руководителем.' if progress(levels, target) == 100 else 'В каталоге нет доступного шага, закрывающего разрыв. Нужны другая активность или индивидуальный план с HR.'}
