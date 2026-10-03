"""Independent synthetic, layered/time-discrete WRM-inspired routing experiment."""
import csv
import hashlib
import json
import math
from pathlib import Path
import random
import time

DT = 0.25  # synthetic hours; conservative rounded travel time, no free waiting
DEADLINE = 16.0
SPEED = 10.0


def edge(a, b, tick, case):
    distance = math.dist(a, b)
    x, y = (a[0]+b[0])/2, (a[1]+b[1])/2
    # Synthetic weather sampled at segment midpoint and departure, not real physics.
    center = 0 if case == 'stationary' else 13*math.sin(tick*DT/3)
    severity = 0 if case == 'calm' else 2.5*math.exp(-((x-50)/24)**2-((y-center)/12)**2)
    hours = distance / SPEED * (1 + 0.25*severity)
    ticks = max(1, math.ceil(hours/DT - 1e-12))
    fuel = distance * (1 + severity)
    return ticks, fuel


def frontier(routes):
    ordered = sorted(routes, key=lambda r: (r['ticks'], r['fuel'], r['path']))
    result, best = [], math.inf
    for route in ordered:
        if route['fuel'] < best - 1e-9:
            result.append(route)
            best = route['fuel']
    return result


def solve(layers, case, deadline=DEADLINE):
    # Keep minimum fuel only at identical node AND time; never prune by earlier arrival.
    states = {(0, 0): (0., [layers[0][0]])}
    for layer_index in range(1, len(layers)):
        following = {}
        for (node, tick), (fuel, path) in states.items():
            for nxt, point in enumerate(layers[layer_index]):
                duration, cost = edge(layers[layer_index-1][node], point, tick, case)
                arrival = tick + duration
                if arrival*DT > deadline:
                    continue
                key = (nxt, arrival)
                if key not in following or fuel+cost < following[key][0]:
                    following[key] = (fuel+cost, path+[point])
        states = following
    return frontier([{'ticks': tick, 'fuel': fuel, 'path': path}
                     for (_, tick), (fuel, path) in states.items()])


def grid():
    return [[(0., 0.)]] + [[(float(x), float(y)) for y in (-30,-15,0,15,30)]
                           for x in range(20,100,20)] + [[(100.,0.)]]


def diverse(routes, k=3):
    if len(routes) <= k:
        return routes
    return [routes[round(i*(len(routes)-1)/(k-1))] for i in range(k)]


def refine(route, case, rng):
    candidates = [route]
    for width in (15., 7.5, 3.75):
        anchor = min(candidates, key=lambda r: r['fuel'])
        layers = [[anchor['path'][0]]]
        for x, y in anchor['path'][1:-1]:
            layers.append([(x,y)]+[(x,max(-40.,min(40.,y+rng.uniform(-width,width))))
                                   for _ in range(5)])
        layers.append([anchor['path'][-1]])
        candidates = frontier(candidates + solve(layers, case))
    return candidates


def run(output):
    output.mkdir(parents=True, exist_ok=True)
    rows, raw = [], []
    for case in ('calm','stationary','moving'):
        for seed in range(10):
            start = time.perf_counter()
            coarse = solve(grid(), case)
            coarse_seconds = time.perf_counter()-start
            for method in ('coarse', 'wrm_fuel', 'diverse_refinement'):
                start = time.perf_counter()
                routes = coarse
                # All methods retain the common coarse front. Extra search budgets differ.
                if method != 'coarse':
                    anchors = ([min(coarse,key=lambda r:r['fuel'])] if method == 'wrm_fuel'
                               else diverse(coarse))
                    for index, anchor in enumerate(anchors):
                        routes = frontier(routes + refine(anchor, case, random.Random(seed*100+index)))
                best = min(routes, key=lambda r:r['fuel'])
                row = dict(case=case, seed=seed, method=method, fuel=best['fuel'],
                           hours=best['ticks']*DT, pareto_count=len(routes),
                           seconds=coarse_seconds+time.perf_counter()-start)
                rows.append(row)
                raw.append(dict(**row, routes=routes))
    with (output/'comparison.csv').open('w', newline='') as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0]))
        writer.writeheader(); writer.writerows(rows)
    (output/'routes.json').write_text(json.dumps({'synthetic':True,'dt_hours':DT,
        'deadline_hours':DEADLINE,'source_sha256':hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
        'runs':raw},ensure_ascii=False,indent=2)+'\n')
    return rows


if __name__ == '__main__':
    run(Path(__file__).parent/'results')
