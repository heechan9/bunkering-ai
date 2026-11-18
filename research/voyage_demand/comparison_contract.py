"""Synthetic declared-context comparison only; no optimizer, metrics or approval."""
import hashlib
import json
import re
import math
from research.voyage_demand.validation import timestamp, available_feature

FIELDS={'schema','data_role','voyage_id','decision_at','departure_at','arrival_deadline',
        'origin_id','destination_id','constraints_sha256','forecast_snapshot_sha256',
        'objective_sha256','features'}
TEXT=('voyage_id','origin_id','destination_id')
HASH=('constraints_sha256','forecast_snapshot_sha256','objective_sha256')

def require_json_native(value, active=None):
    """Reject Python-only containers/types and key coercion before normalization."""
    if active is None:
        active = set()
    kind = type(value)
    if kind is str:
        if any(0xD800 <= ord(char) <= 0xDFFF for char in value):
            raise ValueError('surrogate code points are not supported')
        return
    if kind in (bool, int) or value is None:
        return
    if kind is float:
        if not math.isfinite(value):
            raise ValueError('nonfinite JSON number')
        return
    if kind not in (dict, list):
        raise ValueError('JSON-native types required')
    identity = id(value)
    if identity in active:
        raise ValueError('cyclic JSON input')
    active.add(identity)
    try:
        if kind is dict:
            for key, item in value.items():
                if type(key) is not str:
                    raise ValueError('JSON object keys must be strings')
                require_json_native(key, active)
                require_json_native(item, active)
        else:
            for item in value:
                require_json_native(item, active)
    finally:
        active.remove(identity)

def lossless_timestamp(value):
    """Reject fractional digits that datetime would silently truncate."""
    zone = re.search(r'(Z|([+-])([0-9]{2}):([0-9]{2}))$', value) if isinstance(value, str) else None
    if zone is None or (zone.group(1) != 'Z' and (int(zone.group(3)) > 23 or int(zone.group(4)) > 59)):
        raise ValueError('timezone must be Z or a whole-minute +/-HH:MM offset')
    for fraction in re.findall(r'[.,]([0-9]+)', value):
        if any(digit != '0' for digit in fraction[6:]):
            raise ValueError('timestamp precision exceeds microseconds')
    return timestamp(value)

def checked(raw):
    require_json_native(raw)
    if not isinstance(raw,dict) or set(raw)!=FIELDS:
        raise ValueError('exact context fields required')
    if raw['schema']!='paired-context/v1' or raw['data_role']!='synthetic':
        raise ValueError('only synthetic context supported')
    for k in TEXT:
        if not isinstance(raw[k],str) or not raw[k].strip() or raw[k]!=raw[k].strip():
            raise ValueError('invalid context text')
    for k in HASH:
        if not isinstance(raw[k],str) or not re.fullmatch('[0-9a-f]{64}',raw[k]):
            raise ValueError('invalid declared hash')
    times={k:lossless_timestamp(raw[k]) for k in ('decision_at','departure_at','arrival_deadline')}
    if not times['decision_at']<=times['departure_at']<times['arrival_deadline']:
        raise ValueError('invalid time order')
    features=raw['features']
    if not isinstance(features,list) or not features:
        raise ValueError('nonempty information set required')
    names=set(); normalized=[]
    for f in features:
        if not isinstance(f,dict): raise ValueError('invalid feature')
        feature_times = {k:lossless_timestamp(f.get(k)) for k in ('issued_at','target_at','received_at')}
        available_feature(f, times['decision_at'])
        if f['name'] in names: raise ValueError('duplicate feature')
        names.add(f['name'])
        g=dict(f)
        for k in ('issued_at','target_at','received_at'): g[k]=feature_times[k].isoformat()
        normalized.append(g)
    value=dict(raw)
    value.update({k:v.isoformat() for k,v in times.items()})
    value['features']=sorted(normalized,key=lambda f:f['name'])
    # Reject non-JSON or nonfinite hidden metadata rather than silently ignoring it.
    return json.loads(json.dumps(value,sort_keys=True,allow_nan=False))

def canonical(value):
    """Exact JSON declaration after time/order normalization; no numeric coercion."""
    return json.dumps(value,sort_keys=True,separators=(',',':'),allow_nan=False)

def compare_contexts(left,right):
    a,b=checked(left),checked(right)
    differences=sorted(k for k in FIELDS if canonical(a[k])!=canonical(b[k]))
    digest=lambda v:hashlib.sha256(canonical(v).encode()).hexdigest()
    return {'status':'HOLD' if differences else 'DECLARED_CONTEXTS_MATCH',
            'differences':differences,'left_context_sha256':digest(a),
            'right_context_sha256':digest(b),'operational_approval':False,
            'scope':'SYNTHETIC_DECLARATIONS_ONLY'}
