"""UK sensitivity simulator copied with explicit deadline parameter only."""
N=8
INITIAL, CAPACITY, RESERVE=50.,120.,15.

def simulate(data, policy, speed_policy, deadline=112.):
    fuel, clock, cost, bought, consumed = INITIAL, 0., 0., 0., 0.
    shortage, reserve_violation, stops = False, False, 0
    trace = []
    for i in range(N):
        clock += data['service'][i]  # observed only after port service finishes
        # All policies have speeds 10/12. Adaptive uses observed elapsed time only.
        speed = 12. if speed_policy == 'adaptive' and clock+10*(N-i)+4*(N-i-1)>deadline else 10.
        expected = 20*(speed/10)**2
        floor = RESERVE + expected*(1.3 if policy == 'buffer' else 1.)
        target = floor if policy == 'baseline' else (CAPACITY if data['prices'][i]<100 else floor)
        amount = max(0., min(CAPACITY,target)-fuel)
        fuel += amount; bought += amount; cost += amount*data['prices'][i]; stops += amount>1e-9
        demand = data['fuel'][i]*(speed/10)**2
        before = fuel
        if demand>fuel:
            shortage=True
            consumed+=fuel; fuel=0.
            trace.append(dict(leg=i,inventory=before,purchase=amount,demand=demand,remaining=fuel,speed=speed))
            break
        fuel-=demand; consumed+=demand; clock+=100/speed
        reserve_violation |= fuel<RESERVE-1e-9
        trace.append(dict(leg=i,inventory=before,purchase=amount,demand=demand,remaining=fuel,speed=speed))
    return dict(arrived=not shortage, safe=not(shortage or reserve_violation), shortage=shortage,
                reserve_violation=reserve_violation, purchase=bought, consumed=consumed,
                remaining=fuel, cost=cost, adjusted_cost=cost+100*(INITIAL-fuel),
                purchase_cost_per_consumed_unit=cost/consumed if consumed else None, stops=stops, hours=clock,
                late=(clock>deadline) if not shortage else None,
                late_hours=max(0.,clock-deadline) if not shortage else None, trace=trace)
