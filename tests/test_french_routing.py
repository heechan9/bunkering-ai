import importlib.util
import itertools
from pathlib import Path

spec = importlib.util.spec_from_file_location('routing', Path(__file__).resolve().parents[1]/'research/french_routing/experiment.py')
r = importlib.util.module_from_spec(spec)
spec.loader.exec_module(r)


def test_time_state_solver_matches_exhaustive_paths():
    layers = [[(0,0)],[(20,-15),(20,0),(20,15)],[(60,-20),(60,0),(60,20)],[(100,0)]]
    for case in ('calm','stationary','moving'):
        routes = []
        for path in itertools.product(*layers):
            tick, fuel = 0, 0
            for a,b in zip(path,path[1:]):
                duration,cost = r.edge(a,b,tick,case)
                tick += duration; fuel += cost
            if tick*r.DT <= r.DEADLINE:
                routes.append(dict(ticks=tick,fuel=fuel,path=list(path)))
        expected = [(x['ticks'], x['fuel']) for x in r.frontier(routes)]
        actual = [(x['ticks'], x['fuel']) for x in r.solve(layers,case)]
        assert actual == expected


def test_deadline_and_infeasible():
    assert r.solve(r.grid(),'moving',deadline=1) == []
    assert all(x['ticks']*r.DT <= r.DEADLINE for x in r.solve(r.grid(),'moving'))


def test_refinement_determinism_and_incumbent():
    import random
    anchor = min(r.solve(r.grid(),'stationary'),key=lambda x:x['fuel'])
    a = r.refine(anchor,'stationary',random.Random(7))
    assert a == r.refine(anchor,'stationary',random.Random(7))
    assert min(x['fuel'] for x in a) <= anchor['fuel']


def test_calm_straight_line_reference():
    route = min(r.solve(r.grid(),'calm'),key=lambda x:x['fuel'])
    assert route['fuel'] == 100
    assert route['ticks']*r.DT == 10
