"""Check development paths whose first step has no immediate target gain."""
import copy
import unittest

from career.engine import recommend
from examples.demo import dataset


class PrerequisitePathTests(unittest.TestCase):
    def setUp(self):
        demo = dataset()
        self.employee = demo['employees']['employees'][0]
        self.employee['skills'] = {'DESIGN': 2, 'SPEAK': 2, 'CODE': 4}
        self.skills = {s['skill_id']: s for s in demo['skills']['skills']}
        self.profiles = demo['skills']['role_profiles']
        advanced = copy.deepcopy(demo['events']['events'][0])
        advanced['prerequisites'] = {'SPEAK': 3}
        preparation = copy.deepcopy(advanced)
        preparation.update({
            'event_id': 'DEMO_PREPARATION',
            'title': 'Architecture presentation preparation',
            'prerequisites': {},
            'develops_skills': [{'skill_id': 'SPEAK', 'gain': 1, 'max_level': 3}],
        })
        self.events = {e['event_id']: e for e in (preparation, advanced)}

    def recommend(self, history=()):
        return recommend(self.employee, history, self.events, self.skills,
                         self.profiles, '2026-10-01')

    def test_preparation_unlocks_target_course_after_completion(self):
        before = self.recommend()
        self.assertEqual([r['event_id'] for r in before['recommendations']],
                         ['DEMO_PREPARATION'])
        step = before['recommendations'][0]
        self.assertEqual(step['gains'], [])
        self.assertEqual(step['unlocks'], [self.events['DEMO_DESIGN']['title']])
        self.assertEqual(step['projected_progress'], before['progress'])

        history = [{
            'record_id': 'PREPARATION_DONE',
            'employee_id': self.employee['employee_id'],
            'event_id': 'DEMO_PREPARATION',
            'date': '2026-10-01',
            'status': 'completed',
        }]
        after = self.recommend(history)
        self.assertEqual(after['skills']['SPEAK'], 3)
        self.assertEqual(after['progress'], before['progress'])
        self.assertEqual([r['event_id'] for r in after['recommendations']],
                         ['DEMO_DESIGN'])
        self.assertEqual(after['recommendations'][0]['projected_progress'], 100)

    def test_preparation_is_not_suggested_for_unavailable_target_course(self):
        self.events['DEMO_DESIGN']['target_grades'] = ['Lead']
        result = self.recommend()
        self.assertEqual(result['candidates'], [])
        self.assertEqual(result['recommendations'], [])


if __name__ == '__main__':
    unittest.main()
