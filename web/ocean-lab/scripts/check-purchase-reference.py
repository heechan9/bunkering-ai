"""Generate independent fixtures using the frozen canonical Python environment.

Run from repository root with --env-source ., or supply a source directory
containing envs/bunkering_env.py. Generated fixture is used by the JS check.
"""
import argparse,sys,json,random,hashlib
from pathlib import Path
p=argparse.ArgumentParser();p.add_argument('--env-source',required=True);args=p.parse_args()
source=Path(args.env_source).resolve();sys.path.insert(0,str(source))
from envs.bunkering_env import BunkeringEnv
rng=random.Random(20260925)
fuels=[0,.01,.049,.05,.15,.2,.8,.95,1]+[rng.random() for _ in range(128)]
cases=[]
for fuel in fuels:
 for actions in [[0,0],[0,1],[1,0],[1,1]]:
  price=rng.uniform(250,850);fx=rng.uniform(1000,1600)
  env=BunkeringEnv();env.reset(seed=102);env._fuel_remaining=fuel;steps=[]
  for action in actions:
   env._raw_fuel_price=price;env._raw_fx_rate=fx;env._state=env._observation()
   previous=env._fuel_remaining
   _,_,term,_,info=env.step(action)
   steps.append({'fuelAfter':env._fuel_remaining,'amount':info['actual_bunker_amount'],'cost':info['step_cost_index'],'unmet':max(0,.05-previous),'depleted':info['end_reason']=='fuel_depleted'})
   if term:break
  cases.append({'fuel':fuel,'price':price,'fx':fx,'actions':actions,'steps':steps})
out=Path(__file__).parent/'fixtures/purchase-reference.json';out.parent.mkdir(exist_ok=True)
out.write_text(json.dumps({'base_commit':'66ae9dec2f8ea13a8f4e11b656bc0a011f238929','environment_sha256':hashlib.sha256((source/'envs/bunkering_env.py').read_bytes()).hexdigest(),'cases':cases},separators=(',',':')))
print(len(cases),'canonical reference paths')
