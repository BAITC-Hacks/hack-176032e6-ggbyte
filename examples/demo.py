"""Independent tiny fixture authored for this repository, NOT organizer data."""
import csv
import json
from pathlib import Path


def dataset():
    meta = {'dataset': 'Independent Career Quest demo', 'as_of_date': '2026-10-01'}
    skills = [{'skill_id': 'DESIGN', 'name': 'System Design', 'type': 'hard', 'category': 'engineering', 'description': 'Design maintainable systems.'},
              {'skill_id': 'SPEAK', 'name': 'Public Speaking', 'type': 'soft', 'category': 'communication', 'description': 'Present ideas clearly.'},
              {'skill_id': 'CODE', 'name': 'Programming', 'type': 'hard', 'category': 'engineering', 'description': 'Build reliable software.'}]
    profiles = [{'role': 'Backend Engineer', 'grade': grade, 'required_skills': {'DESIGN': n, 'SPEAK': min(2, n), 'CODE': n}, 'critical_skills': ['DESIGN']} for grade, n in [('Junior', 1), ('Middle', 2), ('Senior', 4), ('Lead', 5)]]
    employees = []
    for eid, name, levels in [('E0001', 'Demo Employee', {'DESIGN': 2, 'SPEAK': 0, 'CODE': 3}), ('DEMO2', 'Ready Employee', {'DESIGN': 4, 'SPEAK': 2, 'CODE': 4}), ('DEMO3', 'Starter Employee', {'DESIGN': 0, 'SPEAK': 1, 'CODE': 1})]:
        employees.append({'employee_id': eid, 'full_name': name, 'department': 'Engineering', 'role': 'Backend Engineer', 'grade': 'Middle',
                          'manager_id': None, 'hire_date': '2024-01-01', 'tenure_months': 33, 'work_format': 'remote', 'preferred_language': 'ru',
                          'career_goal': {'target_role': 'Backend Engineer', 'target_grade': 'Senior'}, 'skills': levels, 'last_review_date': '2026-09-01'})
    def event(eid, title, skill, gain, **extra):
        return {'event_id': eid, 'title': title, 'description': 'Independent demonstration activity.', 'type': 'course', 'format': 'self_paced',
                'duration_hours': 4, 'mandatory': False, 'target_roles': ['Backend Engineer'], 'target_grades': ['Junior', 'Middle', 'Senior', 'Lead'],
                'develops_skills': [{'skill_id': skill, 'gain': gain, 'max_level': 4}], 'prerequisites': {}, 'upcoming_sessions': [], **extra}
    events = [event('DEMO_DESIGN', 'Практика проектирования систем', 'DESIGN', 2),
              event('DEMO_SPEAK', 'Презентации без стресса', 'SPEAK', 1, type='workshop', format='online', upcoming_sessions=['2026-10-10']),
              event('DEMO_CODE', 'Надёжный код', 'CODE', 1, prerequisites={'CODE': 2}),
              event('DEMO_MANDATORY', 'Обязательный инструктаж', 'CODE', 0, mandatory=True, develops_skills=[]),
              event('DEMO_FUTURE', 'Архитектурная лаборатория', 'DESIGN', 1, format='online', upcoming_sessions=['2026-11-01'], prerequisites={'DESIGN': 3})]
    history = [{'record_id': f'FIX{i}', 'employee_id': 'E0001', 'event_id': 'DEMO_SPEAK', 'date': f'2026-08-{i+10}', 'due_date': '',
                'status': 'no_show', 'completion_pct': 0, 'score': '', 'feedback_rating': '', 'assigned_by': 'self'} for i in range(3)]
    return {'employees': {'meta': meta, 'employees': employees}, 'events': {'meta': meta, 'events': events},
            'skills': {'meta': meta, 'skills': skills, 'role_profiles': profiles, 'proficiency_scale': {str(i): str(i) for i in range(6)}}, 'history': history}


def write(root):
    data = Path(root) / 'data'
    data.mkdir(exist_ok=True)
    fixtures = dataset()
    for name in ('employees', 'events', 'skills'):
        (data / f'{name}.json').write_text(json.dumps(fixtures[name], ensure_ascii=False, indent=2), encoding='utf-8')
    with (data / 'activity_history.csv').open('w', encoding='utf-8', newline='') as stream:
        writer = csv.DictWriter(stream, fieldnames=list(fixtures['history'][0]))
        writer.writeheader()
        writer.writerows(fixtures['history'])
