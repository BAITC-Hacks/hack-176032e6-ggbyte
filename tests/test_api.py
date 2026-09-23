import copy
import http.cookiejar
import json
import tempfile
import threading
import unittest
import urllib.error
import urllib.request
from http.server import ThreadingHTTPServer
from unittest.mock import patch

import server
from career.store import Store
from examples.demo import write


class ApiTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.directory = tempfile.TemporaryDirectory()
        write(cls.directory.name)
        server.STORE = Store(cls.directory.name)
        cls.http = ThreadingHTTPServer(('127.0.0.1', 0), server.Handler)
        cls.url = f'http://127.0.0.1:{cls.http.server_port}'
        cls.thread = threading.Thread(target=cls.http.serve_forever, daemon=True)
        cls.thread.start()

    @classmethod
    def tearDownClass(cls):
        cls.http.shutdown(); cls.http.server_close(); cls.thread.join()
        server.STORE.db.close(); cls.directory.cleanup()

    def setUp(self):
        self.client = urllib.request.build_opener(urllib.request.HTTPCookieProcessor(http.cookiejar.CookieJar()))

    def call(self, path, data=None, origin=None):
        headers = {'Content-Type': 'application/json'}
        if origin:
            headers['Origin'] = origin
        req = urllib.request.Request(self.url + path, data=json.dumps(data).encode() if data is not None else None, headers=headers)
        try:
            response = self.client.open(req, timeout=5)
        except urllib.error.HTTPError as exc:
            response = exc
        with response:
            return response.status, json.loads(response.read())

    def login(self, role='employee'):
        return self.call('/api/login', {'role': role, 'employee_id': 'E0001', 'password': 'hr-quest-demo' if role == 'hr' else 'quest-demo'})

    def test_anonymous_and_employee_access_controls(self):
        self.assertEqual(self.call('/api/profile')[0], 401)
        self.assertEqual(self.login()[0], 200)
        self.assertEqual(self.call('/api/profile?id=DEMO2')[0], 403)
        self.assertEqual(self.call('/api/hr')[0], 403)
        self.assertEqual(self.call('/api/import', {'profiles': '[]'})[0], 403)
        self.assertEqual(self.call('/api/goal', {'employee_id': 'DEMO2', 'role': 'Backend Engineer', 'grade': 'Lead'})[0], 403)

    def test_common_demo_password_cannot_log_in_as_other_employee(self):
        self.assertEqual(self.call('/api/login', {'role': 'employee', 'employee_id': 'DEMO2', 'password': 'quest-demo'})[0], 401)

    def test_complete_increases_progress_and_cannot_repeat(self):
        self.login()
        before = self.call('/api/profile')[1]
        status, after = self.call('/api/complete', {'event_id': 'DEMO_DESIGN'})
        self.assertEqual(status, 200)
        self.assertGreater(after['progress'], before['progress'])
        self.assertEqual(self.call('/api/complete', {'event_id': 'DEMO_DESIGN'})[0], 400)
        self.assertEqual(self.call('/api/profile')[1]['progress'], after['progress'])

    def test_hr_and_import(self):
        self.login('hr')
        self.assertEqual(self.call('/api/hr')[0], 200)
        profile = copy.deepcopy(server.STORE.employees[0]); profile['employee_id'] = 'JURY_API'
        self.assertEqual(self.call('/api/import', {'profiles': json.dumps([profile])})[0], 200)
        self.assertEqual(self.call('/api/profile?id=JURY_API')[0], 200)
        self.assertEqual(self.call('/api/import', {'profiles': '[1,2]'})[0], 400)

    def test_hr_distinguishes_goal_reached_from_no_available_step(self):
        self.login('hr')
        status, summary = self.call('/api/hr')
        self.assertEqual(status, 200)
        ready = next(e for e in summary['employees'] if e['employee_id'] == 'DEMO2')
        self.assertTrue(ready['goal_reached'])
        self.assertFalse(ready['has_step'])
        starter = next(e for e in summary['employees'] if e['employee_id'] == 'DEMO3')
        self.assertFalse(starter['goal_reached'])

    def test_import_rejects_non_text_fields_without_changing_data(self):
        self.login('hr')
        before = copy.deepcopy(server.STORE.employees)
        for payload in ({'profiles': None}, {'history': []}, {'profiles': {}}):
            with self.subTest(payload=payload):
                status, response = self.call('/api/import', payload)
                self.assertEqual(status, 400)
                self.assertIn('error', response)
                self.assertEqual(server.STORE.employees, before)

    def test_hr_includes_events_without_participation(self):
        self.login('hr')
        status, summary = self.call('/api/hr')
        self.assertEqual(status, 200)
        self.assertEqual(len(summary['events']), len(server.STORE.events))
        empty = next(e for e in summary['events'] if e['title'] == server.STORE.events['DEMO_FUTURE']['title'])
        self.assertEqual((empty['total'], empty['completed'], empty['missed']), (0, 0, 0))

    def test_cross_origin_mutation_rejected_and_secrets_not_served(self):
        self.assertEqual(self.call('/api/login', {}, 'https://untrusted.example')[0], 403)
        self.assertEqual(self.call('/.env')[0], 404)
        self.assertEqual(self.call('/data/employees.json')[0], 404)

    def test_untrusted_host_is_rejected(self):
        request = urllib.request.Request(self.url + '/api/health', headers={'Host': 'attacker.example'})
        with self.assertRaises(urllib.error.HTTPError) as error:
            self.client.open(request)
        self.assertEqual(error.exception.code, 403)
        error.exception.close()

    def test_cloud_requires_explicit_opt_in(self):
        from career.ai import configuration
        with patch.dict('os.environ', {'AI_PROVIDER': 'openai', 'OPENAI_API_KEY': 'test-key', 'CQ_ALLOW_CLOUD_DATA': 'false'}):
            self.assertFalse(configuration()['configured'])


if __name__ == '__main__':
    unittest.main()
