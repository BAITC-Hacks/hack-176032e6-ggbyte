"""Career Quest: python server.py. Python 3.11+, standard library only."""
import argparse
import hmac
import json
import mimetypes
import os
import secrets
import threading
import time
from datetime import date, timedelta
from collections import Counter, defaultdict
from http.cookies import SimpleCookie
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, urlparse

from career.ai import rerank, load_env, configuration
from career.engine import recommend, apply_gain, eligible
from career.store import Store

ROOT = Path(__file__).resolve().parent
load_env(ROOT)
LOCK = threading.RLock()
SESSIONS = {}
LOGIN_ATTEMPTS = defaultdict(list)
STORE = None


def profile(eid):
    employee = next((e for e in STORE.employees if e['employee_id'] == eid), None)
    if not employee:
        raise ValueError('Сотрудник не найден.')
    return recommend(employee, STORE.history, STORE.events, STORE.skills, STORE.profiles, STORE.today)


def ai_configuration(eid):
    return configuration(independent_demo=STORE.demo_data_allowed(eid))


def public_profile(result):
    result = dict(result)
    result.pop('candidates', None)
    result['history'] = [{**r, 'title': STORE.events[r['event_id']]['title']} for r in reversed(result['history'])]
    result['today'] = STORE.today
    result['roles'] = sorted({p['role'] for p in STORE.profiles})
    result['skill_details'] = [
        {'skill_id': sid, 'name': STORE.skills[sid]['name'],
         'type': STORE.skills[sid]['type'], 'level': level,
         'required': result['target']['required_skills'].get(sid)}
        for sid, level in sorted(result['skills'].items(), key=lambda item: STORE.skills[item[0]]['name'])
    ]
    result['ai'] = ai_configuration(result['employee']['employee_id'])
    result['data_mode'] = 'independent_demo' if STORE.independent_demo else 'dataset'
    return result


class Handler(BaseHTTPRequestHandler):
    def session_cookie_name(self):
        # Browsers share cookies between localhost ports. Keep main/demo logins separate.
        return f'cq_session_{self.server.server_port}'

    def valid_host(self):
        return self.headers.get('Host') in {f'127.0.0.1:{self.server.server_port}', f'localhost:{self.server.server_port}'}

    def log_message(self, fmt, *args):
        pass

    def send_json(self, data, status=200, cookie=None):
        body = json.dumps(data, ensure_ascii=False).encode()
        self.send_response(status)
        self.send_header('Content-Type', 'application/json; charset=utf-8')
        self.send_header('Content-Length', str(len(body)))
        self.send_header('Cache-Control', 'no-store')
        self.send_header('X-Content-Type-Options', 'nosniff')
        if cookie:
            self.send_header('Set-Cookie', cookie)
        self.end_headers()
        self.wfile.write(body)

    def session(self):
        cookie = SimpleCookie()
        try:
            cookie.load(self.headers.get('Cookie', ''))
            name = self.session_cookie_name()
            token = cookie[name].value if name in cookie else ''
        except Exception:
            token = ''
        session = SESSIONS.get(token)
        return session if session and session['expires'] > time.time() else None

    def do_GET(self):
        if not self.valid_host():
            return self.send_json({'error': 'Недопустимый адрес сервера.'}, 403)
        path = urlparse(self.path).path
        if path == '/api/health':
            with LOCK:
                return self.send_json({'ok': True, 'mode': 'independent_demo' if STORE.independent_demo else 'dataset',
                                       'ai': ai_configuration('E0001')})
        if not path.startswith('/api/'):
            return self.static(path)
        with LOCK:
            session = self.session()
            if not session:
                return self.send_json({'error': 'Войдите в приложение.'}, 401)
            query = parse_qs(urlparse(self.path).query)
            if path == '/api/session':
                return self.send_json({k: v for k, v in session.items() if k != 'expires'})
            if path == '/api/profile':
                eid = query.get('id', [session['employee_id']])[0]
                if session['role'] != 'hr' and eid != session['employee_id']:
                    return self.send_json({'error': 'Нет доступа к чужому профилю.'}, 403)
                try:
                    return self.send_json(public_profile(profile(eid)))
                except ValueError as exc:
                    return self.send_json({'error': str(exc)}, 404)
            if path == '/api/hr':
                if session['role'] != 'hr':
                    return self.send_json({'error': 'Доступ только для HR.'}, 403)
                return self.send_json(self.hr_summary())
            return self.send_json({'error': 'Не найдено.'}, 404)

    def hr_summary(self):
        gaps = Counter()
        employees = []
        for e in STORE.employees:
            p = profile(e['employee_id'])
            for g in p['gaps']:
                if g['current'] < g['required']:
                    gaps[g['skill_id']] += 1
            recent_start = (date.fromisoformat(STORE.today) - timedelta(days=90)).isoformat()
            recent = [r for r in p['history'] if r['date'] >= recent_start and not STORE.events[r['event_id']]['mandatory']]
            employees.append({'employee_id': e['employee_id'], 'full_name': e['full_name'], 'role': e['role'], 'grade': e['grade'],
                              'progress': p['progress'], 'has_step': bool(p['recommendations']),
                              'goal_reached': all(g['current'] >= g['required'] for g in p['gaps']),
                              'inactive': not any(r['status'] == 'completed' for r in recent)})
        counts = {eid: Counter() for eid in STORE.events}
        for row in STORE.history:
            if row['date'] <= STORE.today:
                counts[row['event_id']][row['status']] += 1
        return {'employees': employees, 'gaps': [{'name': STORE.skills[s]['name'], 'count': n} for s, n in gaps.most_common(12)],
                'events': [{'title': STORE.events[eid]['title'], 'total': sum(c.values()), 'completed': c['completed'],
                            'missed': c['no_show'] + c['declined'] + c['dropped']} for eid, c in sorted(counts.items())], 'today': STORE.today}

    def do_POST(self):
        try:
            size = int(self.headers.get('Content-Length', '0'))
            if size > 5_000_000 or size < 0:
                return self.send_json({'error': 'Лимит загрузки — 5 МБ.'}, 413)
            # Consume the bounded body before an early 403. Closing a socket with
            # unread request bytes can reset the connection on Windows and hide
            # the JSON error from the browser. No parsing or mutation happens yet.
            self.connection.settimeout(5)
            body = self.rfile.read(size)
            if not self.valid_host():
                return self.send_json({'error': 'Недопустимый адрес сервера.'}, 403)
            origin = self.headers.get('Origin')
            if origin and origin != 'http://' + self.headers.get('Host', ''):
                return self.send_json({'error': 'Недопустимый источник запроса.'}, 403)
            data = json.loads(body or b'{}')
            if not isinstance(data, dict):
                raise ValueError('Ожидается JSON-объект.')
            with LOCK:
                return self.post_action(urlparse(self.path).path, data)
        except (ValueError, KeyError, TypeError) as exc:
            return self.send_json({'error': 'Некорректные данные: ' + str(exc)}, 400)
        except TimeoutError:
            return self.send_json({'error': 'Загрузка запроса заняла слишком много времени.'}, 408)

    def post_action(self, path, data):
        if path == '/api/login':
            now = time.time()
            attempts = LOGIN_ATTEMPTS[self.client_address[0]]
            attempts[:] = [t for t in attempts if t > now - 60]
            if len(attempts) >= 15:
                return self.send_json({'error': 'Слишком много попыток. Повторите через минуту.'}, 429)
            attempts.append(now)
            role = data.get('role', 'employee')
            eid = data.get('employee_id', '')
            expected = os.environ.get('CQ_HR_PASSWORD', 'hr-quest-demo') if role == 'hr' else STORE.password_for(eid)
            valid_id = role == 'hr' or any(e['employee_id'] == eid for e in STORE.employees)
            if role not in ('employee', 'hr') or not valid_id or not hmac.compare_digest(str(data.get('password', '')).encode(), expected.encode()):
                return self.send_json({'error': 'Неверный ID или пароль.'}, 401)
            token = secrets.token_urlsafe(32)
            session = {'role': role, 'employee_id': eid if role == 'employee' else STORE.employees[0]['employee_id'], 'expires': now + 8 * 3600}
            SESSIONS[token] = session
            return self.send_json({'role': role}, cookie=f'{self.session_cookie_name()}={token}; HttpOnly; SameSite=Strict; Path=/; Max-Age=28800')
        session = self.session()
        if not session:
            return self.send_json({'error': 'Войдите в приложение.'}, 401)
        if path == '/api/logout':
            cookie = SimpleCookie(self.headers.get('Cookie', ''))
            name = self.session_cookie_name()
            if name in cookie:
                SESSIONS.pop(cookie[name].value, None)
            return self.send_json({'ok': True}, cookie=f'{name}=; HttpOnly; SameSite=Strict; Path=/; Max-Age=0')
        if path == '/api/import':
            if session['role'] != 'hr':
                return self.send_json({'error': 'Импорт доступен только HR.'}, 403)
            return self.send_json(STORE.merge(data.get('profiles', ''), data.get('history', '')))
        eid = data.get('employee_id', session['employee_id'])
        if session['role'] != 'hr' and eid != session['employee_id']:
            return self.send_json({'error': 'Нет доступа к чужому профилю.'}, 403)
        result = profile(eid)
        if path == '/api/demo/reset':
            STORE.reset_demo_employee(eid)
            return self.send_json(public_profile(profile(eid)))
        if path == '/api/ai':
            config = ai_configuration(eid)
            # Do not block other UI requests while waiting for a model.
            LOCK.release()
            try:
                ai = rerank(result, config=config)
            finally:
                LOCK.acquire()
            choices = {c['event_id']: c for c in result['candidates']}
            return self.send_json({**ai, 'recommendations': [choices[i] for i in ai['ids']] if ai['ids'] else result['recommendations']})
        if path == '/api/goal':
            role, grade = data['role'], data['grade']
            if not any(p['role'] == role and p['grade'] == grade for p in STORE.profiles):
                raise ValueError('Неизвестная цель.')
            result['employee']['career_goal'] = {'target_role': role, 'target_grade': grade}
            STORE.save()
            return self.send_json(public_profile(profile(eid)))
        if path == '/api/complete':
            event = STORE.events.get(data.get('event_id'))
            if not event or not eligible(event, result['employee'], result['skills'], result['history'], STORE.today):
                raise ValueError('Активность недоступна или уже завершена.')
            if any(r['event_id'] == event['event_id'] and r['date'] == STORE.today and r['status'] == 'completed' for r in result['history']):
                raise ValueError('Эта активность уже отмечена сегодня.')
            STORE.history.append({'record_id': 'D' + secrets.token_hex(8), 'employee_id': eid, 'event_id': event['event_id'], 'date': STORE.today,
                                  'due_date': '', 'status': 'completed', 'completion_pct': '100', 'score': '', 'feedback_rating': '', 'assigned_by': 'self'})
            # If the imported assessment is dated today, it precedes this interactive completion.
            if result['employee']['last_review_date'] >= STORE.today:
                result['employee']['skills'] = apply_gain(result['employee']['skills'], event)
            STORE.save()
            return self.send_json(public_profile(profile(eid)))
        return self.send_json({'error': 'Не найдено.'}, 404)

    def static(self, path):
        files = {'/': 'index.html', '/app.js': 'app.js', '/style.css': 'style.css', '/favicon.svg': 'favicon.svg'}
        name = files.get(path)
        if not name:
            return self.send_json({'error': 'Не найдено.'}, 404)
        body = (ROOT / 'static' / name).read_bytes()
        self.send_response(200)
        self.send_header('Content-Type', mimetypes.guess_type(name)[0] + '; charset=utf-8')
        self.send_header('Content-Length', str(len(body)))
        self.send_header('X-Content-Type-Options', 'nosniff')
        self.send_header('Content-Security-Policy', "default-src 'self'; script-src 'self'; style-src 'self' 'unsafe-inline'; img-src 'self' data:; connect-src 'self'; frame-ancestors 'none'; base-uri 'none'")
        self.end_headers()
        self.wfile.write(body)


def main(argv=None, *, bootstrap=False):
    global STORE
    parser = argparse.ArgumentParser(description='Career Quest — local career navigator')
    parser.add_argument('--port', type=int, help='Default: 8001 for AI demo, 8000 for dataset')
    parser.add_argument('--demo-ai', action='store_true', help='Use isolated independent fixtures with AI in runtime/ai-demo')
    parser.add_argument('--dataset', help='Import organizer ZIP into the main data folder')
    parser.add_argument('--open-browser', action='store_true', help='Open the local app in your default browser')
    args = parser.parse_args(argv)
    if args.demo_ai and args.dataset:
        parser.error('--demo-ai and --dataset are separate data modes; choose one.')
    port = args.port if args.port is not None else (8001 if args.demo_ai else 8000)
    if not 1 <= port <= 65535:
        parser.error('--port must be between 1 and 65535.')
    root = ROOT
    if args.demo_ai:
        root = ROOT / 'runtime' / 'ai-demo'
        root.mkdir(parents=True, exist_ok=True)
        from examples.demo import write
        # Catalogs and seed data always come from our source-controlled fixtures.
        # SQLite progress and import provenance persist separately in this folder.
        write(root)
    elif args.dataset:
        from scripts.import_dataset import extract
        extract(args.dataset)
    elif bootstrap and not (ROOT / 'data' / 'employees.json').exists():
        from examples.demo import write
        write(ROOT)
        print('Using independent demo fixtures. For a working AI demo: python run.py --demo-ai')
    try:
        STORE = Store(root, independent_demo=args.demo_ai)
    except FileNotFoundError:
        print('Dataset missing. Run: python scripts/import_dataset.py <path-to-career_quest_dataset.zip>')
        raise SystemExit(1)
    try:
        server = ThreadingHTTPServer(('127.0.0.1', port), Handler)
    except OSError:
        STORE.db.close()
        print(f'Cannot start on port {port}. Another server may be running. Open http://127.0.0.1:{port} or use --port {port + 1}.', flush=True)
        raise SystemExit(1)
    url = f'http://127.0.0.1:{port}'
    print(f'Career Quest: {url}', flush=True)
    print('Data mode: independent AI demo (runtime/ai-demo)' if args.demo_ai else 'Data mode: main dataset (data/)', flush=True)
    config = ai_configuration('E0001')
    print(f"AI: {config['provider']} / {config['model']} / {'configured; verified on first recommendation' if config['configured'] else 'disabled; check .env and README'}", flush=True)
    print('Demo employee: E0001 / quest-demo. HR: hr-quest-demo. Override passwords with CQ_EMPLOYEE_PASSWORD and CQ_HR_PASSWORD.', flush=True)
    if args.open_browser:
        import webbrowser
        webbrowser.open(url)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()
        STORE.db.close()


if __name__ == '__main__':
    main()
