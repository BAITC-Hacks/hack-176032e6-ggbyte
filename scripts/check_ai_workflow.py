"""Exercise the actual HTTP AI route on independent fixtures, never organizer data."""
import http.cookiejar
import json
import os
from pathlib import Path
import sys
import tempfile
import threading
import time
from http.server import ThreadingHTTPServer
import urllib.request

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from career.ai import load_env, configuration
from career.store import Store
from examples.demo import write


def main():
    # Only the API configuration is read from the project, never data/ or SQLite.
    load_env(ROOT)
    config = configuration(independent_demo=True)
    if config['provider'] not in ('openai', 'nvidia', 'ollama'):
        raise ValueError('Configure an AI provider first.')
    if config['provider'] != 'ollama' and not config['key_configured']:
        raise ValueError('API key is missing.')
    # This process serves ONLY independently authored temporary fixtures.
    # The application's .env and cloud-data setting are never changed.
    os.environ['CQ_EMPLOYEE_PASSWORD'] = 'workflow-demo-only'
    import server

    print('Source: independent temporary fixtures. No organizer data is read.', flush=True)
    (ROOT / 'runtime').mkdir(exist_ok=True)
    with tempfile.TemporaryDirectory(prefix='ai-workflow-', dir=ROOT / 'runtime') as directory:
        write(directory)
        server.STORE = Store(directory, independent_demo=True)
        http_server = ThreadingHTTPServer(('127.0.0.1', 0), server.Handler)
        worker = threading.Thread(target=http_server.serve_forever, daemon=True)
        worker.start()
        client = urllib.request.build_opener(urllib.request.HTTPCookieProcessor(http.cookiejar.CookieJar()))

        def call(path, body=None):
            request = urllib.request.Request(
                f'http://127.0.0.1:{http_server.server_port}' + path,
                data=json.dumps(body).encode() if body is not None else None,
                headers={'Content-Type': 'application/json'})
            with client.open(request, timeout=10) as response:
                return json.loads(response.read())

        try:
            call('/api/login', {'role': 'employee', 'employee_id': 'E0001', 'password': 'workflow-demo-only'})
            before = call('/api/profile')
            started = time.monotonic()
            answer = call('/api/ai', {'employee_id': 'E0001'})
            elapsed = time.monotonic() - started
            if answer['mode'] != 'llm':
                raise ValueError('AI route returned fallback instead of a model answer.')
            if answer['recommendations'][0]['event_id'] != 'DEMO_DESIGN':
                raise ValueError('Critical skill must be first on this independent example.')
            if elapsed >= 10:
                raise ValueError('AI route exceeded 10 seconds.')
            after = call('/api/complete', {'event_id': 'DEMO_DESIGN'})
            if before['progress'] != 50 or after['progress'] != 70 or after['skills']['DESIGN'] != 4:
                raise ValueError('Unexpected skill or progress after completion.')
            if call('/api/profile')['progress'] != 70:
                raise ValueError('Progress did not persist.')
            reset = call('/api/demo/reset', {'employee_id': 'E0001'})
            if reset['progress'] != 50 or not reset['ai']['demo_data_allowed']:
                raise ValueError('Demo reset did not restore the independent scenario.')
            call('/api/logout', {})
            print(f"PASS: HTTP login -> {config['provider']} / {config['model']} -> validated recommendation -> completion -> saved progress 50% to 70% -> reset 50%; AI {elapsed:.2f}s.")
        finally:
            http_server.shutdown()
            http_server.server_close()
            worker.join()
            server.STORE.db.close()


if __name__ == '__main__':
    try:
        main()
    except Exception as error:
        # Keys, provider response bodies and request headers are never printed.
        print(f'FAIL: {type(error).__name__}; HTTP status: {getattr(error, "code", "n/a")}. Check model, key, latency and connection.')
        raise SystemExit(1)
