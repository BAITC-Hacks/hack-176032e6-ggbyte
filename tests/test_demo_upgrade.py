"""Enrichment of our demo must never replace user progress or imported data."""
import copy
import json
import tempfile
import unittest

from career.store import Store
from examples.demo import dataset, write


class DemoUpgradeTests(unittest.TestCase):
    def setUp(self):
        self.directory = tempfile.TemporaryDirectory()
        self.addCleanup(self.directory.cleanup)
        write(self.directory.name)
        self.store = Store(self.directory.name, independent_demo=True)
        self.addCleanup(lambda: self.store.db.close())

    def reopen(self, independent_demo=True):
        self.store.db.close()
        self.store = Store(self.directory.name, independent_demo=independent_demo)

    def make_older_state(self):
        self.store.employees = self.store.employees[:3]
        for employee in self.store.employees:
            employee['skills'] = {key: value for key, value in employee['skills'].items()
                                  if key in {'DESIGN', 'SPEAK', 'CODE'}}
        self.store.history = [row for row in self.store.history if row['employee_id'] == 'E0001']
        self.store.demo_content_version = 1

    def test_upgrade_preserves_goal_levels_and_completed_history_and_is_idempotent(self):
        self.make_older_state()
        employee = self.store.employees[0]
        employee['skills']['DESIGN'] = 5
        employee['career_goal']['target_grade'] = 'Middle'
        self.store.history.append({'record_id': 'USER_COMPLETION', 'employee_id': 'E0001',
                                   'event_id': 'DEMO_CODE', 'date': '2026-10-01',
                                   'status': 'completed', 'completion_pct': 100})
        history = copy.deepcopy(self.store.history)
        self.store.save()
        self.reopen()
        upgraded = self.store.employees[0]
        self.assertEqual(upgraded['skills']['DESIGN'], 5)
        self.assertEqual(upgraded['career_goal']['target_grade'], 'Middle')
        self.assertEqual([r for r in self.store.history if r['employee_id'] == 'E0001'], history)
        seed = dataset()['employees']['employees'][0]
        self.assertTrue(set(seed['skills']).issubset(upgraded['skills']))
        self.assertEqual(len(self.store.employees), len(dataset()['employees']['employees']))
        before = copy.deepcopy((self.store.employees, self.store.history))
        self.reopen()
        self.assertEqual((self.store.employees, self.store.history), before)

    def test_upgrade_skips_imported_profile_and_keeps_it_untrusted(self):
        self.make_older_state()
        self.store.employees[1]['full_name'] = 'Imported record stays unchanged'
        imported = copy.deepcopy(self.store.employees[1])
        self.store.untrusted_employee_ids.add(imported['employee_id'])
        self.store.save()
        self.reopen()
        self.assertEqual(self.store.employees[1], imported)
        self.assertFalse(self.store.demo_data_allowed(imported['employee_id']))
        self.assertFalse(any(r['employee_id'] == imported['employee_id'] for r in self.store.history))

    def test_dataset_mode_never_enriches_saved_employees(self):
        self.make_older_state()
        before = copy.deepcopy((self.store.employees, self.store.history))
        self.store.save()
        self.reopen(independent_demo=False)
        self.assertEqual((self.store.employees, self.store.history), before)
        self.assertFalse(self.store.demo_data_allowed('E0001'))

    def test_legacy_state_without_provenance_is_not_enriched_or_trusted(self):
        self.make_older_state()
        before = copy.deepcopy((self.store.employees, self.store.history))
        with self.store.db:
            self.store.db.execute('UPDATE state SET content=? WHERE id=1',
                                  (json.dumps({'employees': self.store.employees, 'history': self.store.history}),))
        self.reopen()
        self.assertEqual((self.store.employees, self.store.history), before)
        self.assertFalse(self.store.demo_data_allowed('E0001'))


if __name__ == '__main__':
    unittest.main()
