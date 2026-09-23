"""Public goal and learning views must agree with the recommendation engine."""
import importlib
import tempfile
import unittest
from unittest.mock import patch

from career.engine import apply_gain, eligible, progress
from career.store import Store
from examples.demo import write


class CatalogViewTests(unittest.TestCase):
    def setUp(self):
        directory = tempfile.TemporaryDirectory()
        self.addCleanup(directory.cleanup)
        write(directory.name)
        self.store = Store(directory.name, independent_demo=True)
        self.addCleanup(self.store.db.close)
        with patch('career.ai.load_env'):
            self.server = importlib.import_module('server')
        replacement = patch.object(self.server, 'STORE', self.store)
        replacement.start()
        self.addCleanup(replacement.stop)

    def test_each_goal_preview_matches_its_actual_requirements(self):
        view = self.server.public_profile(self.server.profile('E0001'))
        by_goal = {(target['role'], target['grade']): target for target in self.store.profiles}
        self.assertEqual({(goal['role'], goal['grade']) for goal in view['goal_options']}, set(by_goal))
        for goal in view['goal_options']:
            target = by_goal[(goal['role'], goal['grade'])]
            self.assertEqual(goal['progress'], progress(view['skills'], target))
            self.assertEqual(goal['skill_count'], len(target['required_skills']))
            self.assertEqual(goal['gaps_count'], sum(skill['current'] < skill['required'] for skill in goal['skills']))
            self.assertEqual(goal['critical_gaps'], sum(skill['current'] < skill['required'] and skill['critical'] for skill in goal['skills']))

    def test_catalog_availability_and_projections_match_engine(self):
        view = self.server.public_profile(self.server.profile('E0001'))
        self.assertEqual({event['event_id'] for event in view['catalog']}, set(self.store.events))
        for event in view['catalog']:
            source = self.store.events[event['event_id']]
            self.assertEqual(event['available'], eligible(source, view['employee'], view['skills'], view['history'], view['today']))
            self.assertEqual(event['projected_progress'], progress(apply_gain(view['skills'], source), view['target']))
        by_id = {event['event_id']: event for event in view['catalog']}
        self.assertFalse(by_id['DEMO_SPEAK_PRACTICE']['available'])
        self.assertEqual(by_id['DEMO_SPEAK_PRACTICE']['requirements'][0]['current'], 0)
        self.assertFalse(by_id['DEMO_MANDATORY']['available'])

    def test_completed_activity_remains_visible_without_being_completable_again(self):
        self.store.history.append({'record_id': 'VIEW_DONE', 'employee_id': 'E0001', 'event_id': 'DEMO_DESIGN',
                                   'date': self.store.today, 'status': 'completed', 'completion_pct': 100})
        view = self.server.public_profile(self.server.profile('E0001'))
        event = next(row for row in view['catalog'] if row['event_id'] == 'DEMO_DESIGN')
        self.assertTrue(event['completed'])
        self.assertFalse(event['available'])
        self.assertEqual(event['skill_effects'][0]['before'], 4)


if __name__ == '__main__':
    unittest.main()
