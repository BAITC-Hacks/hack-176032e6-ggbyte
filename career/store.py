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
    def __init__(self, root, independent_demo=False):
        self.root = Path(root)
        # Set only by the isolated launcher, never by uploaded JSON metadata.
        self.independent_demo = independent_demo
        from examples.demo import dataset
        self.demo_employee_ids = {e['employee_id'] for e in dataset()['employees']['employees']}
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
        self.demo_content_version = initial['meta'].get('content_version', 1) if independent_demo else 0
        row = self.db.execute('SELECT content FROM state WHERE id=1').fetchone()
        if row:
            saved = json.loads(row[0])
            self.employees, self.history = saved['employees'], saved['history']
            # Legacy state has no provenance: fail closed instead of trusting IDs.
            self.untrusted_employee_ids = set(saved.get('untrusted_employee_ids', [e['employee_id'] for e in self.employees]))
            if independent_demo:
                self.demo_content_version = saved.get('demo_content_version', 1)
                if 'untrusted_employee_ids' in saved:
                    self.upgrade_demo_content()
        else:
            self.employees = initial['employees']
            with (self.root / 'data' / 'activity_history.csv').open(encoding='utf-8-sig', newline='') as f:
                self.history = list(csv.DictReader(f))
            self.untrusted_employee_ids = set() if independent_demo else {e['employee_id'] for e in self.employees}
        validate(self.employees, self.history, self.events, self.skills, self.profiles)
        credentials_path = self.root / 'runtime' / 'employee-credentials.json'
        self.credentials = json.loads(credentials_path.read_text()) if credentials_path.exists() else {}
        self.ensure_credentials()
        self.save()

    def upgrade_demo_content(self):
        """Add authored demo content once; preserve user progress and imported profiles."""
        from examples.demo import dataset
        fixtures = dataset()
        version = fixtures['employees']['meta'].get('content_version', 1)
        if self.demo_content_version >= version:
            return
        existing = {employee['employee_id']: employee for employee in self.employees}
        trusted = set()
        for seed in fixtures['employees']['employees']:
            eid = seed['employee_id']
            if eid in self.untrusted_employee_ids:
                continue
            trusted.add(eid)
            if eid not in existing:
                self.employees.append(seed)
                existing[eid] = seed
            else:
                for skill_id, level in seed['skills'].items():
                    existing[eid]['skills'].setdefault(skill_id, level)
        record_ids = {record['record_id'] for record in self.history}
        for record in fixtures['history']:
            if record['employee_id'] in trusted and record['record_id'] not in record_ids:
                # E0001 may have a reset history with regenerated IDs. Its old
                # three seed records must not be recreated during enrichment.
                if record['employee_id'] == 'E0001':
                    continue
                self.history.append(record)
                record_ids.add(record['record_id'])
        self.demo_content_version = version

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
            self.db.execute('INSERT OR REPLACE INTO state VALUES (1,?)', (json.dumps({'employees': self.employees, 'history': self.history,
                            'untrusted_employee_ids': sorted(self.untrusted_employee_ids),
                            'demo_content_version': self.demo_content_version}, ensure_ascii=False),))

    def demo_data_allowed(self, eid):
        return bool(self.independent_demo and eid in self.demo_employee_ids and eid not in self.untrusted_employee_ids)

    def reset_demo_employee(self, eid):
        if not self.independent_demo or eid != 'E0001':
            raise ValueError('Сброс доступен только для E0001 в отдельном AI-демо.')
        from examples.demo import dataset
        fixtures = dataset()
        original = next(e for e in fixtures['employees']['employees'] if e['employee_id'] == eid)
        employees = [original if e['employee_id'] == eid else e for e in self.employees]
        # New record IDs preserve any imported records belonging to other people.
        history = [r for r in self.history if r['employee_id'] != eid]
        history.extend({**r, 'record_id': 'RESET' + secrets.token_hex(12)} for r in fixtures['history'] if r['employee_id'] == eid)
        validate(employees, history, self.events, self.skills, self.profiles)
        self.employees, self.history = employees, history
        self.untrusted_employee_ids.discard(eid)
        self.save()

    def merge(self, profiles_json, history_csv):
        if not isinstance(profiles_json, str) or not isinstance(history_csv, str):
            raise ValueError('Профили и история должны передаваться как текст JSON/CSV.')
        profiles_json = profiles_json.lstrip('\ufeff')
        try:
            incoming = json.loads(profiles_json) if profiles_json.strip() else []
        except json.JSONDecodeError as exc:
            raise ValueError(f'Ошибка JSON: строка {exc.lineno}, столбец {exc.colno}. Проверьте формат файла.') from exc
        if isinstance(incoming, dict):
            incoming = incoming.get('employees', [incoming] if 'employee_id' in incoming else None)
        if not isinstance(incoming, list):
            raise ValueError('JSON должен содержать список employees или профиль сотрудника.')
        if any(not isinstance(e, dict) for e in incoming):
            raise ValueError('Каждый профиль должен быть JSON-объектом.')
        records = []
        if history_csv.strip():
            reader = csv.DictReader(io.StringIO(history_csv.lstrip('\ufeff')), strict=True)
            try:
                columns = reader.fieldnames or []
                if len(set(columns)) != len(columns):
                    raise ValueError('Повторяющиеся названия столбцов CSV.')
                required = {'record_id', 'employee_id', 'event_id', 'date', 'status', 'completion_pct'}
                missing = required - set(columns)
                if missing:
                    raise ValueError('В CSV отсутствуют столбцы: ' + ', '.join(sorted(missing)) + '.')
                for row in reader:
                    if None in row or any(value is None for value in row.values()):
                        raise ValueError(f'CSV: строка {reader.line_num} содержит неверное число столбцов.')
                    records.append(row)
            except csv.Error as exc:
                raise ValueError(f'Ошибка CSV: строка {reader.line_num}. Проверьте кавычки и разделители.') from exc
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
        affected = {e['employee_id'] for e in incoming} | {r['employee_id'] for r in records}
        replaced_ids = {r['record_id'] for r in records}
        affected.update(r['employee_id'] for r in self.history if r['record_id'] in replaced_ids)
        self.employees, self.history = employees, history
        self.untrusted_employee_ids.update(affected)
        self.ensure_credentials()
        self.save()
        return {'profiles': len(incoming), 'records': len(records)}
