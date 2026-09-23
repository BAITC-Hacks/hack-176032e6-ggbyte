"""Exercise complete learning routes in the independent synthetic demonstration."""
import copy
import tempfile
import unittest

from career.engine import apply_gain, recommend
from career.store import Store, validate
from examples.demo import dataset, write


class DemoContentTests(unittest.TestCase):
    def setUp(self):
        fixture = dataset()
        self.employees = fixture['employees']['employees']
        self.history = fixture['history']
        self.events = {event['event_id']: event for event in fixture['events']['events']}
        self.skills = {skill['skill_id']: skill for skill in fixture['skills']['skills']}
        self.profiles = fixture['skills']['role_profiles']
        self.today = fixture['employees']['meta']['as_of_date']

    def result(self, employee, history):
        return recommend(employee, history, self.events, self.skills, self.profiles, self.today)

    def finish_route(self, employee, goal=None):
        employee = copy.deepcopy(employee)
        history = copy.deepcopy(self.history)
        if goal:
            employee['career_goal'] = {'target_role': goal[0], 'target_grade': goal[1]}
        result = self.result(employee, history)
        used = []
        for _ in range(len(self.events)):
            if result['progress'] == 100:
                self.assertTrue(all(gap['current'] >= gap['required'] for gap in result['gaps']))
                self.assertEqual(result['recommendations'], [])
                return used
            self.assertTrue(result['recommendations'], f"Route blocked for {employee['employee_id']}, {employee['career_goal']}: {result['gaps']}")
            event = result['recommendations'][0]
            self.assertNotIn(event['event_id'], used)
            self.assertFalse(event['mandatory'])
            self.assertTrue(all(result['skills'].get(skill, 0) >= needed for skill, needed in event['prerequisites'].items()))
            self.assertGreaterEqual(len(event['reasons']), 3)
            expected = apply_gain(result['skills'], event)
            before = result['progress']
            history.append({'record_id': f'ROUTE_{len(used):03}', 'employee_id': employee['employee_id'],
                            'event_id': event['event_id'], 'date': self.today, 'status': 'completed', 'completion_pct': 100})
            used.append(event['event_id'])
            result = self.result(employee, history)
            self.assertEqual(result['skills'], expected)
            self.assertGreaterEqual(result['progress'], before)
        self.fail(f"Route did not reach its goal after {len(self.events)} distinct activities")

    def test_catalog_is_valid_and_describes_real_learning_tasks(self):
        validate(self.employees, self.history, self.events, self.skills, self.profiles)
        self.assertTrue(dataset()['employees']['meta']['synthetic'])
        self.assertEqual(dataset()['employees']['meta']['content_version'], 2)
        self.assertEqual({skill['type'] for skill in self.skills.values()}, {'hard', 'soft'})
        for skill in self.skills.values():
            self.assertGreater(len(skill['description']), 40)
        for event in self.events.values():
            self.assertGreater(len(event['description']), 70, event['event_id'])
            self.assertGreater(event['duration_hours'], 0)
            self.assertTrue(set(event['prerequisites']) <= self.skills.keys())
            self.assertTrue(all(gain['skill_id'] in self.skills for gain in event['develops_skills']))
            if not event['mandatory']:
                self.assertTrue(event['develops_skills'])
                self.assertTrue(all(0 < gain['gain'] <= 5 and 0 < gain['max_level'] <= 5 for gain in event['develops_skills']))
        for profile in self.profiles:
            self.assertTrue(set(profile['critical_skills']) <= profile['required_skills'].keys())
            self.assertTrue(set(profile['required_skills']) <= self.skills.keys())
            self.assertTrue(all(0 < value <= 5 for value in profile['required_skills'].values()))

    def test_all_seeded_employee_goals_have_complete_routes(self):
        for employee in self.employees:
            with self.subTest(employee=employee['employee_id']):
                self.finish_route(employee)
        self.assertEqual(self.result(self.employees[1], self.history)['progress'], 100)
        self.assertLess(self.result(self.employees[2], self.history)['progress'], 100)

    def test_e0001_can_reach_senior_and_lead_in_all_three_roles(self):
        for role in {profile['role'] for profile in self.profiles}:
            for grade in ('Middle', 'Senior', 'Lead'):
                with self.subTest(role=role, grade=grade):
                    self.finish_route(self.employees[0], (role, grade))

    def test_existing_senior_demo_keeps_its_exact_progress_and_history(self):
        employee = copy.deepcopy(self.employees[0])
        history = copy.deepcopy(self.history)
        own = [row for row in history if row['employee_id'] == 'E0001']
        self.assertEqual([row['record_id'] for row in own], ['FIX0', 'FIX1', 'FIX2'])
        self.assertTrue(all(row['event_id'] == 'DEMO_SPEAK' and row['status'] == 'no_show' for row in own))
        self.assertEqual(self.result(employee, history)['progress'], 50)
        for number, (event_id, expected) in enumerate([
            ('DEMO_DESIGN', 70), ('DEMO_CODE', 80), ('DEMO_SPEAK', 90), ('DEMO_SPEAK_PRACTICE', 100),
        ]):
            result = self.result(employee, history)
            self.assertIn(event_id, {candidate['event_id'] for candidate in result['candidates']})
            history.append({'record_id': f'COMPAT{number}', 'employee_id': 'E0001', 'event_id': event_id,
                            'date': self.today, 'status': 'completed', 'completion_pct': 100})
            self.assertEqual(self.result(employee, history)['progress'], expected)

    def test_hr_history_has_statuses_and_every_record_has_a_valid_subject(self):
        self.assertEqual({row['status'] for row in self.history},
                         {'completed', 'in_progress', 'dropped', 'no_show', 'declined', 'overdue'})
        for employee in self.employees:
            own = [row for row in self.history if row['employee_id'] == employee['employee_id']]
            self.assertTrue(own, employee['employee_id'])
            self.assertTrue(all(row['date'] <= self.today for row in own))
        # A future laboratory remains available to demonstrate HR's zero-participation filter.
        self.assertFalse(any(row['event_id'] == 'DEMO_FUTURE' for row in self.history))
        with tempfile.TemporaryDirectory() as root:
            write(root)
            store = Store(root, independent_demo=True)
            try:
                self.assertEqual(set(store.skills), set(self.skills))
                self.assertEqual({employee['employee_id'] for employee in store.employees},
                                 {employee['employee_id'] for employee in self.employees})
                self.assertTrue(all(store.demo_data_allowed(employee['employee_id']) for employee in self.employees))
            finally:
                store.db.close()


if __name__ == '__main__':
    unittest.main()
