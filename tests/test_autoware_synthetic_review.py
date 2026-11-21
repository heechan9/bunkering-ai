import unittest
from research.decision_review.autoware_synthetic import (
    alert_window, corroboration, coverage, deadlines, display_recovery, paired_cases,
)


class TestSyntheticDecisionReview(unittest.TestCase):
    def test_five_paired_failures(self):
        for name, (naive, revised, expected) in paired_cases().items():
            with self.subTest(name=name):
                self.assertEqual(revised, expected)
                self.assertNotEqual(naive, expected)

    def test_coverage_causes_and_duplicate(self):
        self.assertEqual(coverage(('a','b','c','d'),
                         [('a','READY'),('a','READY'),('b','REJECTED'),('c','STALE')]),
                         {'a':'AMBIGUOUS','b':'REJECTED','c':'STALE','d':'MISSING'})

    def test_independent_units_and_tolerance(self):
        self.assertEqual(corroboration([('x','t',10),('y','t',11)],1),'AGREE')
        self.assertEqual(corroboration([('x','t',10),('y','t',12)],1),'DISAGREE')
        self.assertEqual(corroboration([('x','t',10),('y','kg',10)],1),'INCOMPARABLE')

    def test_budget_boundary_and_missing(self):
        self.assertEqual(deadlines({'a':3,'b':3,'c':3},{'a':3,'b':4}),
                         {'a':'WITHIN','b':'OVERRUN','c':'UNMEASURED'})

    def test_immediate_warning_and_two_sample_clear(self):
        self.assertEqual(display_recovery(('OK','HOLD','OK','HOLD','OK','OK'),2),
                         ('OK','HOLD','RECHECK','HOLD','RECHECK','OK'))

    def test_window_reason_and_inclusive_edges(self):
        for time in (3,4):
            self.assertEqual(alert_window([(time,'reserve')],3,4,'reserve'),'ON_TIME')
        self.assertEqual(alert_window([(5,'reserve')],3,4,'reserve'),'WRONG_TIME')
        self.assertEqual(alert_window([(3,'other')],3,4,'reserve'),'MISSING')
