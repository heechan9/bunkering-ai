import copy
import json
import unittest
from decimal import Decimal
from scripts.compare_ab_log import INPUT, compare


class ComparisonTests(unittest.TestCase):
    def setUp(self):
        self.data = json.loads(INPUT.read_text())

    def test_same_unit_window_differences(self):
        r = compare(self.data)
        self.assertAlmostEqual(float(r['volume_window_differences_kl']['days_01_05_selected']), 2.7)
        self.assertAlmostEqual(float(r['volume_window_differences_kl']['day_31_selected']), 19.7)
        self.assertLess(abs(Decimal(r['rob_identity_residual_t'])), Decimal('1e-6'))

    def test_hypothetical_conversion_arithmetic(self):
        r = compare(self.data)
        scenario = next(s for s in r['density_scenarios'] if s['window'] == 'days_01_31' and s['assumed_density_t_per_kl'] == '0.850')
        self.assertAlmostEqual(float(scenario['hypothetical_mass_t']), 194.565)
        self.assertAlmostEqual(float(scenario['residual_t']), -0.635)
        self.assertEqual(len(r['density_scenarios']), 15)

    def test_no_validation_from_fitted_ratio(self):
        r = compare(self.data)
        self.assertIsNone(r['measured_density'])
        self.assertFalse(r['policy_validation'])
        self.assertFalse(r['sheet1_used'])
        self.assertTrue(all(not w['aligned_voyage_period'] for w in r['windows']))

    def test_bad_identity_units_values(self):
        for kind in ('identity', 'unit', 'nan', 'negative', 'zero'):
            with self.subTest(kind=kind):
                d = copy.deepcopy(self.data)
                if kind == 'identity': d['source_sha256'] = 'wrong'
                elif kind == 'unit': d['units']['daily'] = 'M/T'
                elif kind == 'zero': d['consumption'] = '0'
                else: d['windows'][0]['engines']['ME']['sum'] = 'NaN' if kind == 'nan' else '-1'
                with self.assertRaises(ValueError): compare(d)


if __name__ == '__main__': unittest.main()
