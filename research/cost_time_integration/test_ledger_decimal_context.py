"""Regression checks for caller Decimal precision and rounding isolation."""
import copy
from decimal import (
    Decimal, Inexact, InvalidOperation, Overflow, ROUND_CEILING, ROUND_DOWN, ROUND_FLOOR, ROUND_HALF_DOWN,
    ROUND_HALF_EVEN, ROUND_HALF_UP, ROUND_UP, ROUND_05UP, localcontext,
)
import json
from pathlib import Path
import unittest

from research.cost_time_integration.ledger import audit
from research.cost_time_integration.solver import solve


BASE = json.loads((Path(__file__).parent / 'fixtures_compact.json').read_text())['base']
Q = [0, 16, 0, 0]
ROUNDINGS = (ROUND_CEILING, ROUND_DOWN, ROUND_FLOOR, ROUND_HALF_DOWN,
             ROUND_HALF_EVEN, ROUND_HALF_UP, ROUND_UP, ROUND_05UP)


def reference(case, quantities=Q, precision=28):
    with localcontext() as ctx:
        ctx.prec = precision
        ctx.rounding = ROUND_HALF_EVEN
        return audit(case, quantities)


class LedgerDecimalContext(unittest.TestCase):
    def test_low_precision_cannot_accept_seventy_two_second_deadline_violation(self):
        case = copy.deepcopy(BASE)
        case['deadline_hours'] = 26.30
        with localcontext() as ctx:
            ctx.prec = 3
            actual = audit(case, Q)
        self.assertFalse(actual['valid'])
        self.assertIn('deadline', actual['errors'])
        self.assertEqual(actual['time_hours'], 26.32)

    def test_ledger_is_stable_across_caller_precision_and_rounding(self):
        case = copy.deepcopy(BASE)
        case['calls'][1]['transfer_hours_per_t'] = 0.12345678901234567
        quantities = [0, Decimal('16.00000000000000000000000001'), 0, 0]
        for precision in (1, 2, 3, 28, 50):
            expected = reference(case, quantities, max(28, precision))
            for rounding in ROUNDINGS:
                with self.subTest(precision=precision, rounding=rounding):
                    with localcontext() as ctx:
                        ctx.prec = precision
                        ctx.rounding = rounding
                        actual = audit(case, quantities)
                    self.assertEqual(actual, expected)

    def test_registered_deadline_tolerance_is_unchanged_under_low_precision(self):
        for deadline, valid in ((26.32, True), (26.32 - 5e-7, True),
                                (26.32 - 2e-6, False)):
            with self.subTest(deadline=deadline):
                case = copy.deepcopy(BASE)
                case['deadline_hours'] = deadline
                expected = reference(case)
                with localcontext() as ctx:
                    ctx.prec = 2
                    ctx.rounding = ROUND_DOWN
                    actual = audit(case, Q)
                self.assertIs(actual['valid'], valid)
                self.assertEqual(actual, expected)

    def test_solver_result_does_not_depend_on_caller_precision(self):
        expected = solve(copy.deepcopy(BASE))
        with localcontext() as ctx:
            ctx.prec = 3
            ctx.rounding = ROUND_UP
            actual = solve(copy.deepcopy(BASE))
        self.assertEqual(actual, expected)

    def test_caller_context_is_unchanged(self):
        case = copy.deepcopy(BASE)
        case['calls'][1]['transfer_hours_per_t'] = 0.12345678901234567
        quantities = [0, Decimal('16.00000000000000000000000001'), 0, 0]
        with localcontext() as ctx:
            ctx.prec = 3
            ctx.rounding = ROUND_DOWN
            ctx.clear_flags()
            ctx.flags[Inexact] = True
            before = (ctx.prec, ctx.rounding, ctx.Emin, ctx.Emax, ctx.capitals,
                      ctx.clamp, dict(ctx.traps), dict(ctx.flags))
            audit(case, quantities)
            after = (ctx.prec, ctx.rounding, ctx.Emin, ctx.Emax, ctx.capitals,
                     ctx.clamp, dict(ctx.traps), dict(ctx.flags))
        self.assertEqual(after, before)

    def test_higher_caller_precision_is_not_reduced(self):
        # The ledger has no general magnitude bound. Do not weaken callers that
        # intentionally provide enough precision to retain the 40-tonne demand.
        for huge in (Decimal('1e30'), 1e30):
            with self.subTest(huge_type=type(huge).__name__):
                case = copy.deepcopy(BASE)
                for field in ('capacity_t', 'initial_inventory_t', 'terminal_inventory_exact_t'):
                    case[field] = huge
                with localcontext() as ctx:
                    ctx.prec = 50
                    actual = audit(case, [0, 0, 0, 0])
                self.assertFalse(actual['valid'])
                self.assertIn('terminal', actual['errors'])

    def test_caller_context_is_unchanged_on_error_paths(self):
        def broken_quantities():
            raise RuntimeError('iterator failed')
            yield 0

        for mode in ('invalid_input', 'trapped_overflow', 'untrapped_overflow', 'iterator_error'):
            with self.subTest(mode=mode):
                case = copy.deepcopy(BASE)
                with localcontext() as ctx:
                    ctx.prec = 3
                    ctx.rounding = ROUND_UP
                    if 'overflow' in mode:
                        ctx.Emax = 10
                        case['prices_usd_per_t'][1] = Decimal('1e20')
                    if mode == 'untrapped_overflow':
                        ctx.traps[Overflow] = False
                        ctx.traps[InvalidOperation] = False
                    if mode == 'invalid_input':
                        case['prices_usd_per_t'][1] = float('nan')
                    ctx.clear_flags()
                    before = str(ctx)
                    if mode == 'iterator_error':
                        with self.assertRaisesRegex(RuntimeError, 'iterator failed'):
                            audit(case, broken_quantities())
                    else:
                        self.assertFalse(audit(case, Q)['valid'])
                    self.assertEqual(str(ctx), before)


if __name__ == '__main__':
    unittest.main(verbosity=2)
