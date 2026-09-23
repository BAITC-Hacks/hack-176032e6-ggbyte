import copy
import json
import tempfile
import unittest

from career.store import Store
from examples.demo import write


class ImportValidationTests(unittest.TestCase):
    def setUp(self):
        self.directory = tempfile.TemporaryDirectory()
        self.addCleanup(self.directory.cleanup)
        write(self.directory.name)
        self.store = Store(self.directory.name)
        self.addCleanup(self.store.db.close)

    def test_utf8_bom_profile_is_imported(self):
        employee = copy.deepcopy(self.store.employees[0])
        employee['employee_id'] = 'BOM_PROFILE'
        result = self.store.merge('\ufeff' + json.dumps([employee]), '')
        self.assertEqual(result['profiles'], 1)
        self.assertIn('BOM_PROFILE', [e['employee_id'] for e in self.store.employees])

    def test_missing_csv_columns_are_reported_before_mutation(self):
        before = copy.deepcopy(self.store.history)
        with self.assertRaisesRegex(ValueError, 'completion_pct'):
            self.store.merge('', 'record_id,employee_id,event_id,date,status\n'
                             'BAD,E0001,DEMO_DESIGN,2026-09-20,completed\n')
        self.assertEqual(self.store.history, before)

    def test_duplicate_csv_headers_are_rejected(self):
        before = copy.deepcopy(self.store.history)
        with self.assertRaisesRegex(ValueError, 'Повторяющиеся'):
            self.store.merge('', 'record_id,employee_id,event_id,date,status,completion_pct,status\n'
                             'BAD,E0001,DEMO_DESIGN,2026-09-20,completed,100,no_show\n')
        self.assertEqual(self.store.history, before)


if __name__ == '__main__':
    unittest.main()
