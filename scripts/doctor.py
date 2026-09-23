"""Local readiness check. No network calls, data changes, or secret output."""
import csv
import json
import sqlite3
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from career.ai import configuration, load_env
from career.engine import recommend
from career.store import validate
from examples.demo import dataset


def main():
    load_env(ROOT)
    config = configuration()
    print(f"Python: {sys.version.split()[0]}")
    print(f"AI provider: {config['provider']}; model: {config['model'] or 'none'}")
    print(f"AI enabled for application: {config['configured']}")
    if config['provider'] in ('openai', 'nvidia'):
        print(f"API key present: {config['key_configured']}; cloud processing allowed: {config['cloud_allowed']}")
    if not config['configured']:
        print('ACTION: configure AI before presenting the full AI scenario; see README.')
    print('No API request is made. Test the provider separately: python scripts/check_ai.py')
    data = ROOT / 'data'
    names = ('employees.json', 'skills.json', 'events.json', 'activity_history.csv')
    present = [(data / name).exists() for name in names]
    if any(present) and not all(present):
        raise ValueError('Incomplete data directory. Supply all four dataset files.')
    if all(present):
        def read(name):
            return json.loads((data / name).read_text(encoding='utf-8-sig'))
        employees, skills, events = read('employees.json'), read('skills.json'), read('events.json')
        with (data / 'activity_history.csv').open(encoding='utf-8-sig', newline='') as source:
            history = list(csv.DictReader(source))
        source_name = 'local data files'
    else:
        fixture = dataset()
        employees, skills, events, history = (fixture[k] for k in ('employees', 'skills', 'events', 'history'))
        source_name = 'independent built-in examples (first launch)'
    today = employees['meta']['as_of_date']
    employees = employees['employees']
    db_path = ROOT / 'runtime' / 'career.sqlite3'
    if db_path.exists():
        if not all(present):
            raise ValueError('Saved database requires its original data catalogs.')
        connection = sqlite3.connect(db_path.resolve().as_uri() + '?mode=ro', uri=True)
        try:
            row = connection.execute('SELECT content FROM state WHERE id=1').fetchone()
            if row:
                saved = json.loads(row[0])
                employees, history = saved['employees'], saved['history']
                source_name = 'saved SQLite state + local catalogs'
        finally:
            connection.close()
    event_map = {e['event_id']: e for e in events['events']}
    skill_map = {s['skill_id']: s for s in skills['skills']}
    validate(employees, history, event_map, skill_map, skills['role_profiles'])
    started = time.perf_counter()
    no_step, slowest = 0, 0
    for employee in employees:
        tick = time.perf_counter()
        result = recommend(employee, history, event_map, skill_map, skills['role_profiles'], today)
        slowest = max(slowest, time.perf_counter() - tick)
        if not 0 <= result['progress'] <= 100 or len(result['recommendations']) > 3:
            raise ValueError('Invalid progress or recommendation count.')
        for step in result['recommendations']:
            if len(step['reasons']) < 3:
                raise ValueError('Recommendation requires at least three explanation factors.')
        no_step += not result['recommendations']
    elapsed = time.perf_counter() - started
    print(f"Data source: {source_name}")
    print(f"PASS: {len(employees)} profiles, {len(event_map)} events, {len(skill_map)} skills, {len(history)} history rows.")
    print(f"Profiles without a step: {no_step}; these are shown explicitly to HR.")
    print(f"Local calculation: all profiles {elapsed:.3f}s; slowest profile {slowest:.3f}s (not browser or AI latency).")
    print('Readiness check complete. No data or credentials were modified.')
    return 0 if config['configured'] else 2


if __name__ == '__main__':
    try:
        raise SystemExit(main())
    except (OSError, ValueError, KeyError, TypeError, sqlite3.Error) as error:
        # Dataset/provider values can be sensitive: print only error type.
        print(f'FAIL: {type(error).__name__}. Check the dataset format and README.')
        raise SystemExit(1)
