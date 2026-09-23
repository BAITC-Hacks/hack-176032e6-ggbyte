"""Cloud access is scoped to independent fixtures, never inferred from an ID."""
import copy
import http.cookiejar
import importlib
import json
import os
import tempfile
import threading
import unittest
import urllib.error
import urllib.request
from collections import defaultdict
from http.server import ThreadingHTTPServer
from unittest.mock import patch

from career.ai import configuration, rerank
from career.engine import recommend
from career.store import Store
from examples.demo import dataset, write


CSV_HEADER = 'record_id,employee_id,event_id,date,status,completion_pct\n'


class DemoStoreTests(unittest.TestCase):
    def setUp(self):
        self.directory = tempfile.TemporaryDirectory()
        self.addCleanup(self.directory.cleanup)
        write(self.directory.name)
        self.store = Store(self.directory.name, independent_demo=True)
        self.addCleanup(self.store.db.close)

    def reopen(self, independent_demo=True):
        self.store.db.close()
        self.store = Store(self.directory.name, independent_demo=independent_demo)
        self.addCleanup(self.store.db.close)

    def test_fixture_trust_survives_restart_but_requires_demo_mode(self):
        for eid in ('E0001', 'DEMO2', 'DEMO3'):
            self.assertTrue(self.store.demo_data_allowed(eid))
        self.assertFalse(self.store.demo_data_allowed('UNKNOWN'))
        self.reopen()
        self.assertTrue(self.store.demo_data_allowed('E0001'))
        self.reopen(independent_demo=False)
        self.assertFalse(self.store.demo_data_allowed('E0001'))

    def test_profile_import_taints_existing_id_and_persists(self):
        imported = copy.deepcopy(self.store.employees[0])
        imported['full_name'] = 'Imported profile with the demo ID'
        self.store.merge(json.dumps([imported]), '')
        self.assertFalse(self.store.demo_data_allowed('E0001'))
        self.assertTrue(self.store.demo_data_allowed('DEMO2'))
        self.reopen()
        self.assertFalse(self.store.demo_data_allowed('E0001'))

    def test_history_only_import_taints_profile_and_persists(self):
        self.store.merge('', CSV_HEADER + 'IMPORTED,E0001,DEMO_DESIGN,2026-09-20,completed,100\n')
        self.assertFalse(self.store.demo_data_allowed('E0001'))
        self.assertTrue(self.store.demo_data_allowed('DEMO3'))
        self.reopen()
        self.assertFalse(self.store.demo_data_allowed('E0001'))

    def test_moving_existing_history_taints_both_affected_profiles(self):
        self.store.merge('', CSV_HEADER + 'FIX0,DEMO2,DEMO_SPEAK,2026-08-10,no_show,0\n')
        self.assertFalse(self.store.demo_data_allowed('E0001'))
        self.assertFalse(self.store.demo_data_allowed('DEMO2'))
        self.assertTrue(self.store.demo_data_allowed('DEMO3'))

    def test_reset_preserves_history_reassigned_to_another_employee(self):
        self.store.merge('', CSV_HEADER + 'FIX0,DEMO2,DEMO_SPEAK,2026-08-10,no_show,0\n')
        other_history = copy.deepcopy([r for r in self.store.history if r['employee_id'] == 'DEMO2'])
        self.store.reset_demo_employee('E0001')
        self.reopen()
        self.assertEqual([r for r in self.store.history if r['employee_id'] == 'DEMO2'], other_history)
        restored = [r for r in self.store.history if r['employee_id'] == 'E0001']
        self.assertEqual(len(restored), 3)
        self.assertTrue(all(r['status'] == 'no_show' for r in restored))
        self.assertEqual(len({r['record_id'] for r in self.store.history}), len(self.store.history))
        self.assertTrue(self.store.demo_data_allowed('E0001'))
        self.assertFalse(self.store.demo_data_allowed('DEMO2'))

    def test_failed_import_preserves_data_and_trust(self):
        before_employees = copy.deepcopy(self.store.employees)
        before_history = copy.deepcopy(self.store.history)
        imported = copy.deepcopy(self.store.employees[0])
        imported['full_name'] = 'Import that must roll back'
        with self.assertRaises(ValueError):
            self.store.merge(json.dumps([imported]), CSV_HEADER + 'BAD,E0001,UNKNOWN,2026-09-20,completed,100\n')
        self.assertEqual(self.store.employees, before_employees)
        self.assertEqual(self.store.history, before_history)
        self.reopen()
        self.assertTrue(self.store.demo_data_allowed('E0001'))

    def test_legacy_database_without_provenance_is_untrusted(self):
        # Old application versions stored only these two keys. Merely reopening
        # such a database with --demo-ai must not grant permission to its data.
        legacy = {'employees': self.store.employees, 'history': self.store.history}
        with self.store.db:
            self.store.db.execute('UPDATE state SET content=? WHERE id=1', (json.dumps(legacy),))
        self.reopen()
        for employee in self.store.employees:
            self.assertFalse(self.store.demo_data_allowed(employee['employee_id']))

    def test_reset_restores_only_own_fixture_and_persists(self):
        original_history = copy.deepcopy([row for row in self.store.history if row['employee_id'] == 'E0001'])
        modified = copy.deepcopy(self.store.employees[0])
        modified['skills']['DESIGN'] = 5
        modified['career_goal']['target_grade'] = 'Lead'
        other = copy.deepcopy(self.store.employees[1])
        other['full_name'] = 'Preserved imported employee'
        self.store.merge(json.dumps([modified, other]), CSV_HEADER +
                         'NEW,E0001,DEMO_DESIGN,2026-09-20,completed,100\n' +
                         'OTHER,DEMO2,DEMO_CODE,2026-09-20,completed,100\n')
        other_history = copy.deepcopy([r for r in self.store.history if r['employee_id'] == 'DEMO2'])
        self.store.reset_demo_employee('E0001')
        self.reopen()
        restored = next(e for e in self.store.employees if e['employee_id'] == 'E0001')
        self.assertEqual(restored, dataset()['employees']['employees'][0])
        # CSV ingestion stores percentages as strings; a reset may use fixture
        # integers, so compare history with the same serialization convention.
        normalize = lambda rows: [{k: str(v) for k, v in r.items() if k != 'record_id'} for r in rows]
        self.assertEqual(normalize([r for r in self.store.history if r['employee_id'] == 'E0001']), normalize(original_history))
        self.assertEqual(next(e for e in self.store.employees if e['employee_id'] == 'DEMO2'), other)
        self.assertEqual([r for r in self.store.history if r['employee_id'] == 'DEMO2'], other_history)
        self.assertTrue(self.store.demo_data_allowed('E0001'))
        self.assertFalse(self.store.demo_data_allowed('DEMO2'))

    def test_reset_rejects_original_mode_and_other_employee(self):
        before = copy.deepcopy(self.store.employees)
        with self.assertRaises(ValueError):
            self.store.reset_demo_employee('DEMO2')
        self.assertEqual(self.store.employees, before)
        self.reopen(independent_demo=False)
        with self.assertRaises(ValueError):
            self.store.reset_demo_employee('E0001')
        self.assertEqual(self.store.employees, before)


class DemoAiTests(unittest.TestCase):
    def setUp(self):
        env = {'AI_PROVIDER': 'openai', 'OPENAI_API_KEY': 'test-key-not-real',
               'OPENAI_MODEL': 'gpt-4.1-mini', 'CQ_ALLOW_CLOUD_DATA': 'false'}
        self.environment = patch.dict(os.environ, env, clear=True)
        self.environment.start()
        self.addCleanup(self.environment.stop)

    def test_demo_permission_does_not_enable_original_data_or_change_env(self):
        self.assertFalse(configuration()['configured'])
        self.assertTrue(configuration(independent_demo=True)['configured'])
        self.assertEqual(os.environ['CQ_ALLOW_CLOUD_DATA'], 'false')
        self.assertFalse(configuration()['configured'])
        os.environ.pop('OPENAI_API_KEY')
        self.assertFalse(configuration(independent_demo=True)['configured'])

    def test_explicit_config_controls_rerank_without_global_override(self):
        fixture = dataset()
        result = recommend(fixture['employees']['employees'][0], fixture['history'],
                           {e['event_id']: e for e in fixture['events']['events']},
                           {s['skill_id']: s for s in fixture['skills']['skills']},
                           fixture['skills']['role_profiles'], '2026-10-01')
        with patch('career.ai.CACHE', {}), patch('career.ai.request_model', return_value=['C1']) as model:
            self.assertEqual(rerank(result, config=configuration())['mode'], 'rules')
            model.assert_not_called()
            response = rerank(result, config=configuration(independent_demo=True))
            self.assertEqual(response['mode'], 'llm')
            self.assertEqual(response['ids'], ['DEMO_DESIGN'])
            model.assert_called_once()
            # A cached demo result must not bypass authorization on a later
            # ordinary request, even when all recommendation features match.
            self.assertEqual(rerank(result, config=configuration())['mode'], 'rules')
            model.assert_called_once()


class DemoHttpTests(unittest.TestCase):
    def setUp(self):
        env = {'AI_PROVIDER': 'openai', 'OPENAI_API_KEY': 'test-key-not-real',
               'OPENAI_MODEL': 'gpt-4.1-mini', 'CQ_ALLOW_CLOUD_DATA': 'false',
               'CQ_EMPLOYEE_PASSWORD': 'quest-demo', 'CQ_HR_PASSWORD': 'hr-quest-demo'}
        environment = patch.dict(os.environ, env, clear=True)
        environment.start()
        self.addCleanup(environment.stop)
        # Importing server ordinarily reads .env. Tests only use the fake,
        # in-memory configuration above, including when run on their own.
        with patch('career.ai.load_env'):
            self.server_module = importlib.import_module('server')
        self.directory = tempfile.TemporaryDirectory()
        self.addCleanup(self.directory.cleanup)
        write(self.directory.name)
        self.store = Store(self.directory.name, independent_demo=True)
        self.addCleanup(self.store.db.close)
        for name, value in [('STORE', self.store), ('SESSIONS', {}), ('LOGIN_ATTEMPTS', defaultdict(list))]:
            replacement = patch.object(self.server_module, name, value)
            replacement.start()
            self.addCleanup(replacement.stop)
        self.http = ThreadingHTTPServer(('127.0.0.1', 0), self.server_module.Handler)
        self.url = f'http://127.0.0.1:{self.http.server_port}'
        self.thread = threading.Thread(target=self.http.serve_forever, daemon=True)
        self.thread.start()
        self.addCleanup(self.stop_http)
        self.client = urllib.request.build_opener(urllib.request.HTTPCookieProcessor(http.cookiejar.CookieJar()))

    def stop_http(self):
        self.http.shutdown()
        self.http.server_close()
        self.thread.join()

    def call(self, path, payload=None):
        request = urllib.request.Request(self.url + path, headers={'Content-Type': 'application/json'},
                                         data=None if payload is None else json.dumps(payload).encode())
        try:
            response = self.client.open(request, timeout=5)
        except urllib.error.HTTPError as exc:
            response = exc
        with response:
            return response.status, json.loads(response.read())

    def login(self, role='employee'):
        status, _ = self.call('/api/login', {'role': role, 'employee_id': 'E0001',
                                            'password': 'hr-quest-demo' if role == 'hr' else 'quest-demo'})
        self.assertEqual(status, 200)

    def test_ai_import_and_reset_respect_current_profile_provenance(self):
        self.login()
        status, initial = self.call('/api/profile')
        self.assertEqual(status, 200)
        self.assertEqual(initial['data_mode'], 'independent_demo')
        self.assertTrue(initial['ai']['demo_data_allowed'])
        with patch('career.ai.CACHE', {}), patch('career.ai.request_model', return_value=['C1']) as model:
            status, ai = self.call('/api/ai', {})
            self.assertEqual((status, ai['mode']), (200, 'llm'))
            self.assertEqual(ai['recommendations'][0]['event_id'], 'DEMO_DESIGN')
            model.assert_called_once()
            self.assertTrue(model.call_args.args[0]['demo_data_allowed'])
            self.login('hr')
            self.assertEqual(self.call('/api/import', {'profiles': json.dumps([initial['employee']])})[0], 200)
            imported = self.call('/api/profile')[1]
            self.assertFalse(imported['ai']['configured'])
            self.assertFalse(imported['ai']['demo_data_allowed'])
            self.assertEqual(self.call('/api/ai', {})[1]['mode'], 'rules')
            model.assert_called_once()
            status, restored = self.call('/api/demo/reset', {})
            self.assertEqual(status, 200)
            self.assertTrue(restored['ai']['demo_data_allowed'])
            self.assertTrue(restored['ai']['configured'])
            self.assertEqual(self.call('/api/ai', {})[1]['mode'], 'llm')

    def test_reset_restores_progress_and_enforces_authentication_and_ownership(self):
        self.assertEqual(self.call('/api/demo/reset', {})[0], 401)
        self.login()
        before = self.call('/api/profile')[1]['progress']
        status, completed = self.call('/api/complete', {'event_id': 'DEMO_DESIGN'})
        self.assertEqual(status, 200)
        self.assertGreater(completed['progress'], before)
        self.assertEqual(self.call('/api/demo/reset', {'employee_id': 'DEMO2'})[0], 403)
        status, restored = self.call('/api/demo/reset', {})
        self.assertEqual(status, 200)
        self.assertEqual(restored['progress'], before)
        self.assertEqual(self.call('/api/profile')[1]['progress'], before)
        self.login('hr')
        self.assertEqual(self.call('/api/demo/reset', {'employee_id': 'DEMO2'})[0], 400)

    def test_demo_trajectory_unlocks_speaking_practice_and_reaches_complete_goal(self):
        self.login()
        initial = self.call('/api/profile')[1]
        self.assertEqual(initial['progress'], 50)
        self.assertNotIn('DEMO_SPEAK_PRACTICE', [r['event_id'] for r in initial['recommendations']])
        self.assertEqual(self.call('/api/complete', {'event_id': 'DEMO_SPEAK_PRACTICE'})[0], 400)
        for event_id, expected_progress in [('DEMO_DESIGN', 70), ('DEMO_CODE', 80), ('DEMO_SPEAK', 90)]:
            with self.subTest(event=event_id):
                status, current = self.call('/api/complete', {'event_id': event_id})
                self.assertEqual(status, 200)
                self.assertEqual(current['progress'], expected_progress)
        self.assertIn('DEMO_SPEAK_PRACTICE', [r['event_id'] for r in current['recommendations']])
        status, completed = self.call('/api/complete', {'event_id': 'DEMO_SPEAK_PRACTICE'})
        self.assertEqual(status, 200)
        self.assertEqual(completed['progress'], 100)
        self.assertEqual(completed['skills']['SPEAK'], 2)
        self.assertEqual(completed['recommendations'], [])
        self.assertEqual(self.call('/api/profile')[1]['progress'], 100)
        with patch('career.ai.request_model') as model:
            status, answer = self.call('/api/ai', {})
            self.assertEqual(status, 200)
            self.assertEqual(answer['mode'], 'rules')
            self.assertEqual(answer['recommendations'], [])
            self.assertIn('Требования цели выполнены', answer['message'])
            model.assert_not_called()

    def test_same_day_completions_keep_order_with_reverse_ids_and_reach_lead(self):
        self.login()
        self.assertEqual(self.call('/api/goal', {'role': 'Data Analyst', 'grade': 'Lead'})[0], 200)
        # Invalid imported metadata must not seed the integer completion counter.
        self.store.history[0]['completion_order'] = '99999'
        self.store.history[1]['completion_order'] = True
        descending_ids = [f'{1000 - index:016x}' for index in range(len(self.store.events))]
        chosen = []
        with patch.object(self.server_module.secrets, 'token_hex', side_effect=descending_ids):
            for event_id, expected in [('DEMO_ANALYSIS_BASE', 3), ('DEMO_ANALYSIS_ADV', 5)]:
                status, current = self.call('/api/complete', {'event_id': event_id})
                self.assertEqual(status, 200)
                self.assertEqual(current['skills']['ANALYSIS'], expected)
                chosen.append(event_id)
            for _ in range(len(self.store.events) - len(chosen)):
                if current['progress'] == 100:
                    break
                self.assertTrue(current['recommendations'], current['gaps'])
                step = current['recommendations'][0]
                status, current = self.call('/api/complete', {'event_id': step['event_id']})
                self.assertEqual(status, 200)
                self.assertEqual(current['progress'], step['projected_progress'])
                chosen.append(step['event_id'])
        self.assertEqual(current['progress'], 100)
        own = [row for row in self.store.history if row['employee_id'] == 'E0001' and row['status'] == 'completed']
        self.assertEqual([row['event_id'] for row in own], chosen)
        self.assertEqual([row['completion_order'] for row in own], list(range(1, len(own) + 1)))
        self.assertGreater(own[0]['record_id'], own[1]['record_id'])
        reopened = Store(self.directory.name, independent_demo=True)
        try:
            persisted = next(employee for employee in reopened.employees if employee['employee_id'] == 'E0001')
            replay = recommend(persisted, reopened.history, reopened.events, reopened.skills, reopened.profiles, reopened.today)
            self.assertEqual(replay['progress'], 100)
            self.assertEqual(replay['skills']['ANALYSIS'], 5)
            self.assertEqual([row['completion_order'] for row in reopened.history if row['employee_id'] == 'E0001' and row['status'] == 'completed'],
                             list(range(1, len(own) + 1)))
        finally:
            reopened.db.close()

    def test_original_mode_neither_resets_data_nor_calls_cloud_model(self):
        self.store.independent_demo = False
        self.login()
        before = copy.deepcopy(self.store.employees)
        history = copy.deepcopy(self.store.history)
        status, profile = self.call('/api/profile')
        self.assertEqual(status, 200)
        self.assertEqual(profile['data_mode'], 'dataset')
        self.assertFalse(profile['ai']['configured'])
        with patch('career.ai.request_model') as model:
            self.assertEqual(self.call('/api/ai', {})[1]['mode'], 'rules')
            model.assert_not_called()
        self.assertEqual(self.call('/api/demo/reset', {})[0], 400)
        self.assertEqual(self.store.employees, before)
        self.assertEqual(self.store.history, history)

    def test_sessions_on_two_ports_do_not_overwrite_or_log_out_each_other(self):
        second_http = ThreadingHTTPServer(('127.0.0.1', 0), self.server_module.Handler)
        second_thread = threading.Thread(target=second_http.serve_forever, daemon=True)
        second_thread.start()
        first_url = self.url
        second_url = f'http://127.0.0.1:{second_http.server_port}'
        try:
            # Both endpoints deliberately use the same opener/CookieJar, like
            # two localhost tabs in one browser, and distinct logged-in roles.
            with patch('career.ai.request_model') as model:
                self.login('employee')
                self.url = second_url
                self.login('hr')
                self.assertEqual(self.call('/api/session')[1]['role'], 'hr')
                self.url = first_url
                status, first_session = self.call('/api/session')
                self.assertEqual(status, 200)
                self.assertEqual(first_session['role'], 'employee')
                self.url = second_url
                self.assertEqual(self.call('/api/logout', {})[0], 200)
                self.assertEqual(self.call('/api/session')[0], 401)
                self.url = first_url
                status, first_session = self.call('/api/session')
                self.assertEqual(status, 200)
                self.assertEqual(first_session['role'], 'employee')
                model.assert_not_called()
        finally:
            self.url = first_url
            second_http.shutdown()
            second_http.server_close()
            second_thread.join()

    def test_untrusted_origin_or_host_is_rejected_before_json_parsing(self):
        before = copy.deepcopy(self.store.employees)
        for rejected_header in ({'Origin': 'https://untrusted.example'}, {'Host': 'untrusted.example'}):
            with self.subTest(header=next(iter(rejected_header))):
                request = urllib.request.Request(self.url + '/api/goal', data=b'{malformed-json',
                                                 headers={'Content-Type': 'application/json', **rejected_header})
                with self.assertRaises(urllib.error.HTTPError) as failure:
                    self.client.open(request, timeout=5)
                with failure.exception as response:
                    self.assertEqual(response.status, 403)
                    self.assertIn('error', json.loads(response.read()))
        self.assertEqual(self.store.employees, before)


if __name__ == '__main__':
    unittest.main()
