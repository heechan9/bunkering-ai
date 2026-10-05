"""Numerical and split-integrity checks, independent of DQN fit quality."""
import json
import numpy as np
import pandas as pd
from retrain import OUT, quantity, rollout, solve

def main():
    # Analytic two-price arbitrage with terminal reserve: buy at the cheap port.
    q=solve([1,2],[.4,.4],1,.1,.1,[True,True]);np.testing.assert_allclose(q,[.8,0],atol=1e-7)
    assert solve([1],[1],1,.5,.1,[True]) is None
    c={'d':np.array([.2,.3,.1,.1]),'p':np.array([.1,.2,.15,.12]),'cap':1000,'sailing':10,'limit':100,'fixed':np.ones(4),'variable':np.zeros(4)}
    c['lp']=solve(c['p'],c['d'],1,.5,.1,[True]*4)
    for i in range(4):
        for inv in [.1,.3,.7,1.]:
            for a in range(5):
                q=quantity(c,i,inv,a)
                assert q>=-1e-9 and inv+q<=1+1e-9 and inv+q-c['d'][i]>=.1-1e-9
    assert rollout(c,rule='minimum')['cost']>=rollout(c,rule='lp')['cost']-1e-7
    manifest=json.loads((OUT/'route_manifest.json').read_text());seen=set()
    for r in manifest:
        key=(r['id'].split(':')[0],tuple(r['signature']));assert key not in seen;seen.add(key)
    df=pd.read_csv(OUT/'episodes.csv');assert df.safe.all()
    assert np.isfinite(df.cost).all()
    expected={'minimum','cheaper_port','lp','dqn_42','dqn_43','dqn_44'}
    assert all(set(g.policy)==expected for _,g in df.groupby('id'))
    for _,g in df.groupby('id'):
        lower=float(g[g.policy=='lp'].cost.iloc[0]);assert (g.cost>=lower-1e-5).all()
    print('PASS: analytic LP, impossible leg, guard balance, unique routes, complete paired policies, finite costs, LP lower bound')
if __name__=='__main__':main()
