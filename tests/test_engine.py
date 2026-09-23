import copy
import json
import tempfile
import unittest
from unittest.mock import patch

from career.engine import apply_gain, current_skills, recommend, history_sort_key
from career.store import Store
from career.ai import rerank
from examples.demo import dataset, write


class EngineTests(unittest.TestCase):
    def setUp(self):
        d = dataset()
        self.employee = d['employees']['employees'][0]
        self.events = {e['event_id']: e for e in d['events']['events']}
        self.skills = {s['skill_id']: s for s in d['skills']['skills']}
        self.profiles = d['skills']['role_profiles']
        self.history = d['history']

    def run_recommend(self):
        return recommend(self.employee, self.history, self.events, self.skills, self.profiles, '2026-10-01')

    def test_critical_skill_beats_lowest_skill_with_three_no_shows(self):
        result = self.run_recommend()
        self.assertEqual(result['recommendations'][0]['event_id'], 'DEMO_DESIGN')
        self.assertEqual(len(result['recommendations'][0]['reasons']), 3)
        self.assertGreater(result['recommendations'][0]['projected_progress'], result['progress'])

    def test_mandatory_completed_prerequisites_and_expired_are_excluded(self):
        self.events['DEMO_SPEAK']['format'] = 'online'
        self.events['DEMO_SPEAK']['upcoming_sessions'] = ['2026-09-01']
        self.history.append({**self.history[0], 'record_id': 'DONE', 'event_id': 'DEMO_CODE', 'status': 'completed'})
        ids = {e['event_id'] for e in self.run_recommend()['candidates']}
        self.assertEqual(ids, {'DEMO_DESIGN'})

    def test_only_post_review_completions_change_levels(self):
        row = {**self.history[0], 'event_id': 'DEMO_DESIGN', 'status': 'completed'}
        self.history = [{**row, 'record_id': 'OLD', 'date': '2026-08-01'}, {**row, 'record_id': 'NEW', 'date': '2026-09-20'}, {**row, 'record_id': 'FUTURE', 'date': '2026-12-01'}]
        levels = current_skills(self.employee, self.history, self.events, '2026-10-01')
        self.assertEqual(levels['DESIGN'], 4)

    def test_cap_never_reduces_existing_skill(self):
        self.assertEqual(apply_gain({'DESIGN': 5}, self.events['DEMO_DESIGN'])['DESIGN'], 5)

    def test_same_day_completion_sequence_preserves_courses_with_different_caps(self):
        first = {'record_id': 'Z_FIRST', 'employee_id': 'E0001', 'event_id': 'DEMO_ANALYSIS_BASE',
                 'date': '2026-10-01', 'status': 'completed', 'completion_pct': 100, 'completion_order': 1}
        second = {**first, 'record_id': 'A_SECOND', 'event_id': 'DEMO_ANALYSIS_ADV', 'completion_order': 2}
        self.history.extend([first, second])
        expected = apply_gain(apply_gain(self.employee['skills'], self.events['DEMO_ANALYSIS_BASE']), self.events['DEMO_ANALYSIS_ADV'])
        self.assertEqual(expected['ANALYSIS'], 5)
        self.assertEqual(current_skills(self.employee, self.history, self.events, '2026-10-01'), expected)
        result = self.run_recommend()
        self.assertEqual(result['skills']['ANALYSIS'], 5)
        self.assertEqual([row['record_id'] for row in result['history'][-2:]], ['Z_FIRST', 'A_SECOND'])

    def test_legacy_history_order_is_preserved_and_invalid_sequences_are_ignored(self):
        rows = [{'date': '2026-10-01', 'record_id': 'Z', 'completion_order': 1},
                {'date': '2026-10-01', 'record_id': 'B'},
                {'date': '2026-09-30', 'record_id': 'EARLIER', 'completion_order': 100},
                {'date': '2026-10-01', 'record_id': 'A'}]
        self.assertEqual([row['record_id'] for row in sorted(rows, key=history_sort_key)], ['EARLIER', 'A', 'B', 'Z'])
        for invalid in (None, True, False, '2000', 2.5, 0, -1):
            with self.subTest(order=invalid):
                self.assertEqual(history_sort_key({'date': '2026-10-01', 'record_id': 'A', 'completion_order': invalid}),
                                 ('2026-10-01', 0, 'A'))

    def test_unknown_goal_is_not_silently_used(self):
        with tempfile.TemporaryDirectory() as path:
            write(path); store = Store(path)
            invalid = copy.deepcopy(self.employee); invalid['career_goal']['target_grade'] = 'Unknown'
            before = copy.deepcopy(store.employees)
            with self.assertRaises(ValueError):
                store.merge(json.dumps([invalid]), '')
            self.assertEqual(store.employees, before)
            store.db.close()

    def test_import_is_atomic_persistent_and_supports_new_ids(self):
        with tempfile.TemporaryDirectory() as path:
            write(path); store = Store(path)
            new = copy.deepcopy(self.employee); new['employee_id'] = 'JURY1'
            self.assertEqual(store.merge(json.dumps({'employees': [new]}), '')['profiles'], 1)
            with self.assertRaises(ValueError):
                store.merge('', 'record_id,employee_id,event_id,date,status,completion_pct\nBAD,JURY1,INVALID,2026-09-01,completed,100')
            self.assertEqual(len(store.history), len(dataset()['history']))
            store.db.close(); reopened = Store(path)
            self.assertEqual(len(reopened.employees), len(dataset()['employees']['employees']) + 1)
            reopened.db.close()

    def test_imported_history_updates_new_profile_skills(self):
        with tempfile.TemporaryDirectory() as path:
            write(path); store = Store(path)
            new = copy.deepcopy(self.employee); new['employee_id'] = 'JURY_HISTORY'
            history_csv = ('record_id,employee_id,event_id,date,due_date,status,completion_pct,score,feedback_rating,assigned_by\n'
                           'JH1,JURY_HISTORY,DEMO_DESIGN,2026-09-20,,completed,100,90,5,self\n')
            imported = store.merge(json.dumps([new]), history_csv)
            self.assertEqual(imported, {'profiles': 1, 'records': 1})
            result = recommend(new, store.history, store.events, store.skills, store.profiles, store.today)
            self.assertEqual(result['skills']['DESIGN'], 4)
            self.assertNotIn('DEMO_DESIGN', [r['event_id'] for r in result['recommendations']])
            store.db.close()

    def test_empty_recommendations_when_goal_is_satisfied(self):
        self.employee['skills'] = {'DESIGN': 5, 'CODE': 5, 'SPEAK': 5}
        result = self.run_recommend()
        self.assertEqual(result['progress'], 100)
        self.assertEqual(result['recommendations'], [])

    def test_rounding_does_not_hide_small_remaining_gap(self):
        self.employee['skills'] = {'DESIGN': 4, 'CODE': 4, 'SPEAK': 1.99}
        result = self.run_recommend()
        self.assertEqual(result['progress'], 99)
        self.assertNotIn('Требования цели выполнены', result['empty_reason'])
        self.assertTrue(any(g['current'] < g['required'] for g in result['gaps']))

    def test_llm_cannot_invent_event(self):
        with patch('career.ai.configuration', return_value={'configured': True, 'provider': 'ollama', 'model': 'test'}), patch('career.ai.request_model', return_value=['INVENTED']):
            self.assertEqual(rerank(self.run_recommend())['mode'], 'fallback')

    def test_llm_receives_anonymous_features(self):
        def model(config, context):
            text = json.dumps(context)
            self.assertNotIn(self.employee['full_name'], text)
            self.assertNotIn(self.employee['employee_id'], text)
            self.assertNotIn('DEMO_DESIGN', text)
            return ['C1']
        with patch('career.ai.configuration', return_value={'configured': True, 'provider': 'ollama', 'model': 'test-private'}), patch('career.ai.request_model', side_effect=model):
            result = rerank(self.run_recommend())
            self.assertEqual(result['mode'], 'llm')
            self.assertEqual(result['ids'], ['DEMO_DESIGN'])

    def test_cached_choice_is_remapped_to_current_catalog(self):
        result = self.run_recommend()
        changed = copy.deepcopy(result)
        changed['candidates'][0]['event_id'] = 'NEW_CATALOG_EVENT'
        with patch('career.ai.CACHE', {}), patch('career.ai.configuration', return_value={'configured': True, 'provider': 'ollama', 'model': 'cache-test'}), patch('career.ai.request_model', return_value=['C1']) as model:
            self.assertEqual(rerank(result)['ids'], ['DEMO_DESIGN'])
            cached = rerank(changed)
            self.assertTrue(cached['cached'])
            self.assertEqual(cached['ids'], ['NEW_CATALOG_EVENT'])
            model.assert_called_once()


if __name__ == '__main__':
    unittest.main()
