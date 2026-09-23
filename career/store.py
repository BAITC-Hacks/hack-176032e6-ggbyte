import csv
import io
import json
import sqlite3
import secrets
import os
from datetime import date
from pathlib import Path

from .engine import GRADES

STATUSES = {'completed', 'in_progress', 'dropped', 'no_show', 'declined', 'overdue'}


def validate(employees, history, events, skill_ids, profiles):
    if not isinstance(employees, list) or not employees:
        raise ValueError('Нужен непустой список employees.')
    ids = set()
    role_grades = {(p['role'], p['grade']) for p in profiles}
    for e in employees:
        if not isinstance(e, dict):
            raise ValueError('Каждый профиль должен быть JSON-объектом.')
        eid = e.get('employee_id')
        if not isinstance(eid, str) or not eid or len(eid) > 80 or eid in ids:
            raise ValueError('Некорректный или повторяющийся employee_id.')
        ids.add(eid)
        for field in ['full_name', 'department', 'role', 'grade', 'last_review_date']:
            if not isinstance(e.get(field), str) or not e[field]:
                raise ValueError(f'{eid}: отсутствует {field}.')
        if (e['role'], e['grade']) not in role_grades:
            raise ValueError(f'{eid}: неизвестная роль или грейд.')
        date.fromisoformat(e['last_review_date'])
        if not isinstance(e.get('skills'), dict) or any(s not in skill_ids or type(n) not in (int, float) or not 0 <= n <= 5 for s, n in e['skills'].items()):
            raise ValueError(f'{eid}: навыки должны иметь известные ID и уровни от 0 до 5.')
        goal = e.get('career_goal')
        if goal is not None and (not isinstance(goal, dict) or (goal.get('target_role'), goal.get('target_grade')) not in role_grades):
            raise ValueError(f'{eid}: неизвестная карьерная цель.')
    record_ids = set()
    for r in history:
        rid = r.get('record_id')
        if not rid or rid in record_ids:
            raise ValueError('Повторяющийся или отсутствующий record_id.')
        record_ids.add(rid)
        if r.get('employee_id') not in ids or r.get('event_id') not in events:
            raise ValueError(f'{rid}: неизвестный сотрудник или мероприятие.')
        if r.get('status') not in STATUSES:
            raise ValueError(f'{rid}: неизвестный статус.')
        date.fromisoformat(r['date'])
        if r.get('due_date'):
            date.fromisoformat(r['due_date'])
        pct = int(r.get('completion_pct', 0))
        if not 0 <= pct <= 100 or (r['status'] == 'completed' and pct != 100):
            raise ValueError(f'{rid}: неверный процент выполнения.')


class Store:
    def __init__(self, root):
        self.root = Path(root)
        self.root.joinpath('runtime').mkdir(exist_ok=True)
        self.db = sqlite3.connect(self.root / 'runtime' / 'career.sqlite3', check_same_thread=False)
        self.db.execute('CREATE TABLE IF NOT EXISTS state (id INTEGER PRIMARY KEY, content TEXT NOT NULL)')
        def read(name):
            return json.loads((self.root / 'data' / name).read_text(encoding='utf-8-sig'))
        sk = read('skills.json')
        self.skills = {s['skill_id']: s for s in sk['skills']}
        self.profiles = sk['role_profiles']
        self.events = {e['event_id']: e for e in read('events.json')['events']}
        initial = read('employees.json')
        self.today = initial['meta']['as_of_date']
        row = self.db.execute('SELECT content FROM state WHERE id=1').fetchone()
        if row:
            saved = json.loads(row[0])
            self.employees, self.history = saved['employees'], saved['history']
        else:
            self.employees = initial['employees']
            with (self.root / 'data' / 'activity_history.csv').open(encoding='utf-8-sig', newline='') as f:
                self.history = list(csv.DictReader(f))
        validate(self.employees, self.history, self.events, self.skills, self.profiles)
        credentials_path = self.root / 'runtime' / 'employee-credentials.json'
        self.credentials = json.loads(credentials_path.read_text()) if credentials_path.exists() else {}
        self.ensure_credentials()
        self.save()

    def ensure_credentials(self):
        for e in self.employees:
            self.credentials.setdefault(e['employee_id'], secrets.token_urlsafe(18))
        (self.root / 'runtime' / 'employee-credentials.json').write_text(json.dumps(self.credentials, indent=2), encoding='utf-8')

    def password_for(self, eid):
        if eid == 'E0001':
            return os.environ.get('CQ_EMPLOYEE_PASSWORD', 'quest-demo')
        return self.credentials.get(eid, secrets.token_urlsafe(18))

    def save(self):
        with self.db:
            self.db.execute('INSERT OR REPLACE INTO state VALUES (1,?)', (json.dumps({'employees': self.employees, 'history': self.history}, ensure_ascii=False),))

    def merge(self, profiles_json, history_csv):
        incoming = json.loads(profiles_json) if profiles_json.strip() else []
        if isinstance(incoming, dict):
            incoming = incoming.get('employees', [incoming] if 'employee_id' in incoming else None)
        if not isinstance(incoming, list):
            raise ValueError('JSON должен содержать список employees или профиль сотрудника.')
        if any(not isinstance(e, dict) for e in incoming):
            raise ValueError('Каждый профиль должен быть JSON-объектом.')
        records = list(csv.DictReader(io.StringIO(history_csv.lstrip('\ufeff')))) if history_csv.strip() else []
        if not incoming and not records:
            raise ValueError('Выберите хотя бы один непустой файл.')
        # Reject duplicates inside the upload before merging by identifier.
        if len({e.get('employee_id') for e in incoming}) != len(incoming):
            raise ValueError('Повторяющиеся employee_id в загружаемом файле.')
        if len({r.get('record_id') for r in records}) != len(records):
            raise ValueError('Повторяющиеся record_id в загружаемом файле.')
        new_employees = {e['employee_id']: e for e in self.employees}
        new_employees.update({e['employee_id']: e for e in incoming})
        new_history = {r['record_id']: r for r in self.history}
        new_history.update({r['record_id']: r for r in records})
        employees, history = list(new_employees.values()), list(new_history.values())
        validate(employees, history, self.events, self.skills, self.profiles)
        self.employees, self.history = employees, history
        self.ensure_credentials()
        self.save()
        return {'profiles': len(incoming), 'records': len(records)}
