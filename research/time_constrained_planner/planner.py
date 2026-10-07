"""Exact mixed-integer planner for the fixed-price, known-demand research model."""
import numpy as np
from scipy.optimize import milp, Bounds, LinearConstraint


def plan(c):
    d,p,f,v=(np.asarray(c[k],dtype=float) for k in ('d','p','fixed','variable'))
    n=len(d)
    if n==0 or any(x.shape!=(n,) for x in (p,f,v)):
        raise ValueError('Equal nonempty vectors required')
    if not all(np.isfinite(x).all() for x in (d,p,f,v)) or any((x<0).any() for x in (d,p,f,v)):
        raise ValueError('Finite nonnegative inputs required')
    if not all(np.isfinite(c[k]) for k in ('sailing','limit','cap')) or c['cap']<=0 or c['sailing']<0 or c['limit']<=0:
        raise ValueError('Invalid capacity or time')
    # q purchases (tank fractions), z binary stop indicators. q<=z.
    lower=np.tril(np.ones((n,n)));zero=np.zeros((n,n))
    A=np.vstack([np.c_[lower,zero],np.c_[np.eye(n),-np.eye(n)],np.r_[v,f][None,:]])
    lo=np.r_[np.cumsum(d)+.1-.5,np.full(n,-np.inf),-np.inf]
    hi=np.r_[1-.5+np.r_[0,np.cumsum(d)[:-1]],np.zeros(n),c['limit']-c['sailing']]
    result=milp(np.r_[p-min(p),np.zeros(n)],integrality=np.r_[np.zeros(n),np.ones(n)],
                bounds=Bounds(np.zeros(2*n),np.ones(2*n)),constraints=LinearConstraint(A,lo,hi),
                options={'mip_rel_gap':0.0})
    if result.status==2:return None
    if not result.success:raise RuntimeError(result.message)
    q=np.maximum(0,result.x[:n]);inv=.5+np.cumsum(q-d)
    hours=float(c['sailing']+v@q+f@(q>1e-9))
    assert np.all(inv>=.1-1e-7) and np.all(inv+d<=1+1e-7)
    assert hours<=c['limit']+1e-6
    cost=float((q@p+min(p)*(.5-inv[-1]))*c['cap'])
    return dict(q=q,cost=cost,hours=hours,safe=True,feasible=True)
