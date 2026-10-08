import pytest
from .model import existing_call, dedicated_call, arrival, Delay
from .sensitivity import scenarios


def existing(**kw):
    args=dict(baseline_departure=12,cargo_end_with_bunkering=12,bunker_ready=0,
              preparation=1,transfer=8,cleanup=1)
    return existing_call(**(args|kw))


def test_overlap_and_late_start():
    assert existing().extra_hours == 0
    assert existing(transfer=12).extra_hours == 2
    assert existing(bunker_ready=4).extra_hours == 2


def test_interrupted_cargo_and_departure_floor():
    assert existing(cargo_end_with_bunkering=18).extra_hours == 6
    assert existing(baseline_departure=20).extra_hours == 0


def test_dedicated_all_phases_count_once():
    assert dedicated_call(detour=2,port_transit=1,waiting=3,preparation=1,transfer=8,cleanup=1).extra_hours == 16


def test_missing_is_not_zero():
    c=existing(preparation=None)
    assert c.extra_hours is None and c.missing == ('preparation',)
    assert dedicated_call().status == 'UNKNOWN'
    assert arrival(baseline_hours=720,calls=[c],deadline_hours=760)['on_time'] is None


@pytest.mark.parametrize('value', [-1,float('nan'),float('inf'),True,'8',[],10**1000])
def test_invalid(value):
    with pytest.raises(ValueError): existing(transfer=value)
    with pytest.raises(ValueError): dedicated_call(transfer=value)


def test_invalid_even_if_another_field_missing():
    with pytest.raises(ValueError): existing(preparation=None,transfer=-1)


def test_zero_deadline_and_multiple_calls():
    c=existing(transfer=12)
    assert arrival(baseline_hours=720,calls=[c,c],deadline_hours=724)['on_time']
    assert not arrival(baseline_hours=720,calls=[c,c],deadline_hours=723)['on_time']
    assert arrival(baseline_hours=0,calls=[],deadline_hours=0)['on_time']
    assert arrival(baseline_hours=None,calls=[],deadline_hours=0)['status']=='UNKNOWN'


def test_overflow():
    with pytest.raises(ValueError): existing(bunker_ready=1e308,transfer=1e308)
    with pytest.raises(ValueError): dedicated_call(detour=1e308,port_transit=1e308,waiting=0,preparation=0,transfer=0,cleanup=0)
    with pytest.raises(ValueError): arrival(baseline_hours=1e308,calls=[Delay('KNOWN',1e308)],deadline_hours=1e308)


@pytest.mark.parametrize('c',[Delay('KNOWN',None),Delay('KNOWN',-1),Delay('UNKNOWN',1),Delay('BAD',0)])
def test_malformed_delay(c):
    with pytest.raises(ValueError): arrival(baseline_hours=0,calls=[c],deadline_hours=0)


def test_sensitivity_monotonicity_and_scope():
    rows=list(scenarios())
    assert len(rows)==63
    for a in rows:
        assert a['arrival_hours']==720+a['cargo_hours']+a['extra_hours']
        for b in rows:
            if all(a[k]==b[k] for k in ('kind','cargo_hours','ready_hours','deadline_hours')) and a['work_hours']<=b['work_hours']:
                assert a['arrival_hours']<=b['arrival_hours']
