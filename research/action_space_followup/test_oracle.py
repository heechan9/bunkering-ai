import importlib.util
import itertools
from pathlib import Path
import unittest
import numpy as np

spec=importlib.util.spec_from_file_location('followup_runner',Path(__file__).with_name('run.py'))
m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)

class OracleTests(unittest.TestCase):
    def test_vectorized_matches_scalar_with_time_penalty(self):
        c=dict(d=np.array([.24,.29,.13,.24]),p=np.array([1.13,.9,1.27,.72]),cap=1000.,sailing=10.,limit=10.5,fixed=np.array([.2,.4,.3,.5]),variable=np.ones(4))
        result=m.oracles(c,None)
        for n,(cost_best,obj_best) in zip([5,6],result):
            costs=[];objs=[]
            for actions in itertools.product(range(n),repeat=4):
                inv=.5;cost=0.;h=c['sailing']
                for i,a in enumerate(actions):
                    if a==5:
                        j=next((j for j in range(i+1,4) if c['p'][j]<c['p'][i]),4)
                        q=max(0,min(1,.1+sum(c['d'][i:j]))-inv)
                    else:
                        lo=max(0,c['d'][i]+.1-inv);hi=max(0,min(1,.1+sum(c['d'][i:]))-inv)
                        q=min(max(0,1-inv),lo+(hi-lo)*a/4)
                    inv+=q-c['d'][i];cost+=q*c['p'][i]
                    if q>1e-9:h+=c['fixed'][i]+q*c['variable'][i]
                    self.assertGreaterEqual(inv,.1-1e-9)
                value=(cost+min(c['p'])*(.5-inv))*c['cap']
                costs.append(value);objs.append(value/(c['cap']*.1)+5*max(0,h/c['limit']-1))
            self.assertAlmostEqual(cost_best,min(costs));self.assertAlmostEqual(obj_best,min(objs))

if __name__=='__main__':unittest.main()
