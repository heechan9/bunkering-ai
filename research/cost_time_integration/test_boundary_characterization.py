"""Characterize current reserve/deadline behavior; do not redefine policy."""
import copy
import json
from pathlib import Path
import unittest
from research.cost_time_integration.solver import solve
from research.cost_time_integration.ledger import audit
# Use imported source's fixture so this file also runs against the untouched base.
from research.cost_time_integration import solver
BASE=json.loads((Path(solver.__file__).parent/'fixtures_compact.json').read_text())['base']
class BoundaryCharacterization(unittest.TestCase):
    def test_initial_reserve_is_required_even_if_purchase_could_repair(self):
        c=copy.deepcopy(BASE);c['initial_inventory_t']=10;c['arrival_reserves_t']=[12,6,6,6];c['deadline_hours']=1000
        self.assertEqual(solve(c)['status'],'INFEASIBLE')
        self.assertIn('initial reserve',audit(c,[12,24,0,0])['errors'])
    def test_nonuniform_arrival_indices_match_post_leg_inventory(self):
        c=copy.deepcopy(BASE);c['arrival_reserves_t']=[20,26,16,6]
        self.assertTrue(audit(c,[0,16,0,0])['valid'])
        self.assertEqual(solve(c)['status'],'FEASIBLE_OPTIMAL')
    def test_second_arrival_not_shifted_to_next_leg(self):
        c=copy.deepcopy(BASE);c['arrival_reserves_t']=[20,27,16,6]
        r=audit(c,[0,16,0,0]);self.assertFalse(r['valid']);self.assertIn('1:arrival reserve',r['errors'])
    def test_initial_guard_not_removed_for_nonuniform_first_reserve(self):
        c=copy.deepcopy(BASE);c['arrival_reserves_t']=[31,6,6,6]
        self.assertEqual(solve(c)['status'],'INFEASIBLE')
        self.assertIn('initial reserve',audit(c,[16,0,0,0])['errors'])

for name,deadline,solver_status,ledger_valid in [
    ('exact',26.32,'FEASIBLE_OPTIMAL',True),
    ('inside_audit_tolerance',26.32-5e-7,'INFEASIBLE',True),
    ('outside_audit_tolerance',26.32-2e-6,'INFEASIBLE',False),
    ('positive_slack',26.32+5e-7,'FEASIBLE_OPTIMAL',True),
]:
    def test(self,deadline=deadline,solver_status=solver_status,ledger_valid=ledger_valid):
        c=copy.deepcopy(BASE);c['deadline_hours']=deadline
        self.assertEqual(solve(c)['status'],solver_status)
        self.assertIs(audit(c,[0,16,0,0])['valid'],ledger_valid)
    setattr(BoundaryCharacterization,'test_deadline_'+name,test)

# Generated functions are registered on the TestCase, not standalone pytest tests.
del test

if __name__=='__main__':unittest.main(verbosity=2)
