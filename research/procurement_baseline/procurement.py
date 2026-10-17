"""Synthetic STATIC_KNOWN fixed-route, one-grade purchasing; t and USD only."""
from dataclasses import dataclass
from itertools import product
import math
import numpy as np
from scipy.optimize import linprog, milp, Bounds, LinearConstraint

class NotReady(ValueError):
    pass

def number(x, name):
    if x is None or (isinstance(x, str) and x.lower() in ('unknown', '')):
        raise NotReady(name)
    if isinstance(x, (bool, np.bool_)) or not isinstance(x, (int, float, np.integer, np.floating)):
        raise ValueError(name + ': numeric scalar required')
    if not math.isfinite(float(x)) or x < 0:
        raise ValueError(name + ': finite nonnegative number required')
    return float(x)

def price_to_usd_t(value, unit, fx_to_usd=1., fx_direction='USD/source'):
    """Explicit direction; no implicit inverse FX, volume, or energy conversion."""
    value = number(value, 'price'); fx = number(fx_to_usd, 'fx')
    if fx_direction != 'USD/source' or fx <= 0 or unit not in ('currency/t', 'currency/kg'):
        raise ValueError('Unsupported price unit or FX direction')
    answer = value * fx * (1000 if unit == 'currency/kg' else 1)
    return number(answer, 'converted price')

@dataclass(frozen=True)
class Case:
    case_id: str
    d: tuple
    p: tuple
    available: tuple
    supply: tuple
    minimum: tuple
    fixed: tuple
    variable: tuple
    reserve: tuple
    capacity: float = 100.
    initial: float = 20.
    terminal: float = 10.
    mass_unit: str = 't'
    currency: str = 'USD'
    fuel_grade: str = 'MGO'
    data_kind: str = 'synthetic'
    information_tier: str = 'STATIC_KNOWN'
    mass_input_precision_t: float = 0.001

    def validate(self):
        if (self.mass_unit, self.currency, self.data_kind, self.information_tier) != ('t','USD','synthetic','STATIC_KNOWN'):
            raise ValueError('Only synthetic STATIC_KNOWN t/USD supported')
        if not self.case_id or not self.fuel_grade:
            raise ValueError('case_id and one fuel grade required')
        n = len(self.d)
        if not n or any(len(getattr(self, k)) != n for k in ('p','available','supply','minimum','fixed','variable','reserve')):
            raise ValueError('Exactly one decision per leg; final arrival purchase unsupported')
        for k in ('capacity','initial','terminal'):
            number(getattr(self,k),k)
        if type(self.mass_input_precision_t) is not float or self.mass_input_precision_t != .001:
            raise ValueError('v1 mass input precision must be 0.001 t')
        if self.capacity > 1000:
            raise ValueError('v1 supports capacity <= 1000 t only')
        if self.capacity <= 0 or self.initial > self.capacity or self.terminal > self.capacity:
            raise ValueError('Inventory outside capacity')
        for k in ('d','supply','minimum','fixed','variable','reserve'):
            for v in getattr(self,k): number(v,k)
        # Restrict input precision, not continuous decision variables. Tiny residual
        # requirements can evade binary fees under solver feasibility tolerance.
        masses=[self.capacity,self.initial,self.terminal]+[v for k in ('d','supply','minimum','reserve') for v in getattr(self,k)]
        if any(abs(float(v)/.001-round(float(v)/.001)) > 1e-7 for v in masses):
            raise ValueError('Mass inputs must be multiples of 0.001 t; sub-precision inputs unsupported')
        if any(v > self.capacity for v in self.reserve) or self.terminal < self.reserve[-1]:
            raise ValueError('Invalid reserve or terminal below reserve')
        for a,p in zip(self.available,self.p):
            if a is None or a == 'unknown': raise NotReady('availability')
            if type(a) is not bool: raise ValueError('availability must be bool')
            if a or p is not None: number(p,'price')
        return self

    @property
    def mass_tol(self): return max(1e-6, 1e-8*self.capacity)
    @property
    def prices(self): return np.array([p if a else 0. for a,p in zip(self.available,self.p)],float)


def audit(c, q, z, objective=None):
    """Independent sequential physical ledger, no constraint-matrix reuse or clipping."""
    c.validate(); n=len(c.d); errors=[]; rows=[]
    if len(q)!=n or len(z)!=n: return {'valid':False,'errors':['shape']}
    if not all(math.isfinite(float(x)) for x in list(q)+list(z)):
        return {'valid':False,'errors':['nonfinite solution']}
    inv=float(c.initial); cost=0.; tol=c.mass_tol
    for i in range(n):
        qty=float(q[i]); stop=float(z[i]); dep=inv+qty; after=dep-c.d[i]
        if min(abs(stop),abs(stop-1))>1e-7: errors.append(f'{i}:binary')
        if qty < -tol or qty > min(c.supply[i],c.capacity)*stop+tol: errors.append(f'{i}:supply/link')
        if not c.available[i] and (qty>tol or stop>1e-7): errors.append(f'{i}:unavailable')
        if qty < c.minimum[i]*stop-tol: errors.append(f'{i}:minimum')
        if qty<=tol and stop>0.5: errors.append(f'{i}:ghost stop')
        if min(inv,dep,after)<-tol or max(inv,dep,after)>c.capacity+tol: errors.append(f'{i}:inventory')
        if after<c.reserve[i]-tol: errors.append(f'{i}:reserve')
        fuel=qty*c.prices[i]; var=qty*c.variable[i]; fixed=stop*c.fixed[i]
        subtotal=fuel+var+fixed;cost+=subtotal
        rows.append(dict(call_index=i,I_before_t=inv,q_t=qty,D_after_t=dep,consumption_t=c.d[i],I_next_t=after,reserve_t=c.reserve[i],z=stop,fuel_cost_usd=fuel,variable_fee_usd=var,fixed_fee_usd=fixed,total_usd=subtotal))
        inv=after
    if abs(inv-c.terminal)>tol: errors.append('terminal')
    residual=c.initial+sum(q)-sum(c.d)-inv
    if abs(residual)>tol: errors.append('mass balance')
    if objective is not None and abs(cost-objective)>max(.01,1e-8*max(1,abs(cost))): errors.append('objective')
    return dict(valid=not errors,errors=errors,ledger=rows,total_usd=cost,terminal_t=inv,mass_residual_t=float(residual))


def solver_status(r):
    # SciPy status 1 includes iteration OR time limit, not proof of infeasibility.
    return {0:'OPTIMAL',1:'LIMIT_REACHED',2:'INFEASIBLE',3:'UNBOUNDED',4:'SOLVER_ERROR'}.get(r.status,'SOLVER_ERROR')


def solve(c, mode='auto'):
    try: c.validate()
    except NotReady as e: return {'status':'NOT_READY','message':str(e)}
    except (ValueError,TypeError) as e: return {'status':'INVALID_INPUT','message':str(e)}
    if mode not in ('auto','lp','milp'): raise ValueError('mode')
    n=len(c.d); C=c.capacity
    is_mip=mode=='milp' or (mode=='auto' and (any(c.fixed) or any(c.minimum)))
    if mode=='lp' and (any(c.fixed) or any(c.minimum)):
        return {'status':'INVALID_INPUT','message':'LP cannot silently relax fixed fees/minimum lift'}
    # Scale q to tank fractions, while the objective remains USD.
    lower=np.tril(np.ones((n,n))); prior=np.r_[0,np.cumsum(c.d)[:-1]]
    lo=(np.cumsum(c.d)+c.reserve-c.initial)/C
    hi=(C-c.initial+prior)/C
    target=(sum(c.d)+c.terminal-c.initial)/C
    upper=np.array([min(u,C)/C if a else 0 for u,a in zip(c.supply,c.available)])
    price=(c.prices+np.array(c.variable))*C
    try:
        if not is_mip:
            r=linprog(price,A_ub=np.r_[lower,-lower],b_ub=np.r_[hi,-lo],A_eq=np.ones((1,n)),b_eq=[target],bounds=list(zip(np.zeros(n),upper)),method='highs')
            status=solver_status(r)
            if status!='OPTIMAL':return {'status':status,'message':r.message}
            q=r.x*C; z=(q>c.mass_tol).astype(float)
        else:
            A=np.vstack([np.c_[lower,np.zeros((n,n))],np.r_[np.ones(n),np.zeros(n)],np.c_[np.eye(n),-np.diag(upper)],np.c_[np.eye(n),-np.diag(np.array(c.minimum)/C)]])
            low=np.r_[lo,target,np.full(n,-np.inf),np.zeros(n)]
            high=np.r_[hi,target,np.zeros(n),np.full(n,np.inf)]
            objective=np.r_[price,c.fixed]
            bounds=Bounds(np.zeros(2*n),np.r_[upper,np.array(c.available,dtype=float)])
            integ=np.r_[np.zeros(n),np.ones(n)]
            r=milp(objective,integrality=integ,bounds=bounds,constraints=LinearConstraint(A,low,high),options={'mip_rel_gap':0.,'presolve':False})
            status=solver_status(r)
            if status!='OPTIMAL':return {'status':status,'message':r.message}
            # Lexicographic solve: exact optimum equality, no epsilon cost tradeoff.
            second=milp(np.r_[np.zeros(n),np.ones(n)],integrality=integ,bounds=bounds,constraints=LinearConstraint(np.vstack([A,objective]),np.r_[low,r.fun],np.r_[high,r.fun]),options={'mip_rel_gap':0.,'presolve':False})
            if solver_status(second)!='OPTIMAL': return {'status':'LEXICOGRAPHIC_FAILED','primary_status':'OPTIMAL','secondary_status':solver_status(second),'message':second.message}
            q=second.x[:n]*C;z=second.x[n:]
        checked=audit(c,q,z,float(r.fun))
        return dict(status='OPTIMAL' if checked['valid'] else 'AUDIT_FAILED',mode='MILP' if is_mip else 'LP',q_t=q.tolist(),z=z.tolist(),objective_usd=float(r.fun),solver_message=r.message,mip_gap=getattr(r,'mip_gap',None),mip_dual_bound=getattr(r,'mip_dual_bound',None),audit=checked)
    except Exception as e:
        return {'status':'SOLVER_ERROR','message':type(e).__name__+': '+str(e)}


def enumerate_stops(c):
    """Independent reference: enumerate z and use explicit inventory variables (not cumulative rows)."""
    c.validate();n=len(c.d);best=None; feasible=0
    for bits in product((0,1),repeat=n):
        if any(z and not a for z,a in zip(bits,c.available)):continue
        bounds=[(c.minimum[i]*bits[i],min(c.supply[i],c.capacity)*bits[i]) for i in range(n)]+[(c.reserve[i],c.capacity) for i in range(n)]
        if any(a>b for a,b in bounds):continue
        eq=np.zeros((n+1,2*n));rhs=np.zeros(n+1)
        ub=np.zeros((n,2*n));br=np.full(n,c.capacity)
        for i in range(n):
            eq[i,i]=-1;eq[i,n+i]=1;rhs[i]=-c.d[i]
            ub[i,i]=1
            if i: eq[i,n+i-1]=-1;ub[i,n+i-1]=1
            else:rhs[i]+=c.initial;br[i]-=c.initial
        eq[n,-1]=1;rhs[n]=c.terminal
        r=linprog(np.r_[c.prices+np.array(c.variable),np.zeros(n)],A_eq=eq,b_eq=rhs,A_ub=ub,b_ub=br,bounds=bounds,method='highs')
        if r.status==2:continue
        if r.status!=0:raise RuntimeError('Enumeration LP failed: '+r.message)
        feasible+=1; value=float(r.fun+np.dot(c.fixed,bits))
        if best is None or value<best['objective_usd']:best={'objective_usd':value,'q_t':r.x[:n].tolist(),'z':list(bits)}
    return dict(status='OPTIMAL' if best else 'INFEASIBLE',best=best,feasible_patterns=feasible,patterns=2**n)
