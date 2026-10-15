import pytest
from .model import existing_call, dedicated_call, arrival, Delay, NOT_MODELED
import csv
from pathlib import Path
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


# --- departure readiness: time that can only start after ALL cargo and bunker work has finished (hand calculated) ---
# departure = max(baseline, max(cargo end, bunker end) + readiness); extra = departure - baseline


def test_readiness_counterexample_late_cargo_end():
    # baseline 12 (= original cargo end 10 + readiness 2). cargo now ends 13, fuel ends 10 -> 13 + 2 = 15 -> 3 h (was 1)
    c = existing(baseline_departure=12, cargo_end_with_bunkering=13, bunker_ready=0, preparation=0, transfer=10, cleanup=0, departure_readiness=2)
    assert c.extra_hours == 3
    assert existing(baseline_departure=12, cargo_end_with_bunkering=13, bunker_ready=0, preparation=0, transfer=10, cleanup=0).extra_hours == 1


def test_readiness_counterexample_late_fuel_end():
    # cargo ends 10 (baseline 12), fuel ends 14 -> 14 + 2 = 16 -> 4 h (was 2)
    c = existing(baseline_departure=12, cargo_end_with_bunkering=10, bunker_ready=14, preparation=0, transfer=0, cleanup=0, departure_readiness=2)
    assert c.extra_hours == 4
    assert existing(baseline_departure=12, cargo_end_with_bunkering=10, bunker_ready=14, preparation=0, transfer=0, cleanup=0).extra_hours == 2


def test_readiness_interrupted_cargo_late_fuel():
    # baseline 12 (cargo end 10 + 2). cargo interrupted, ends 15; fuel 8+1+6+1 = 16 -> work end 16 -> 18 -> 6 h (legacy 4)
    c = existing(baseline_departure=12, cargo_end_with_bunkering=15, bunker_ready=8, preparation=1, transfer=6, cleanup=1, departure_readiness=2)
    assert c.extra_hours == 6


def test_readiness_is_absorbed_by_the_baseline_slack():
    # work ends 10, readiness 2 -> 12 <= baseline 12 -> no delay (overlapping work is not charged twice)
    assert existing(baseline_departure=12, cargo_end_with_bunkering=10, bunker_ready=0, preparation=1, transfer=7, cleanup=1, departure_readiness=2).extra_hours == 0
    # work ends 11 -> 13 -> 1 h
    assert existing(baseline_departure=12, cargo_end_with_bunkering=11, bunker_ready=0, preparation=1, transfer=7, cleanup=1, departure_readiness=2).extra_hours == 1


def test_readiness_zero_equals_legacy_and_omission_is_flagged():
    base = dict(baseline_departure=12, cargo_end_with_bunkering=13, bunker_ready=4, preparation=1, transfer=8, cleanup=1)
    explicit, legacy = existing_call(**base, departure_readiness=0), existing_call(**base)
    assert explicit == legacy and explicit.extra_hours == 2   # 4+1+8+1 = 14 -> 14 - 12
    assert explicit.readiness_modeled is True and legacy.readiness_modeled is False
    assert existing_call(**base, departure_readiness=NOT_MODELED).readiness_modeled is False


def test_readiness_unknown_is_not_zero():
    c = existing(departure_readiness=None)
    assert c.status == 'UNKNOWN' and c.extra_hours is None and c.missing == ('departure_readiness',)
    c = existing(departure_readiness=None, transfer=None)
    assert c.missing == ('transfer', 'departure_readiness')
    assert arrival(baseline_hours=720, calls=[c], deadline_hours=760)['on_time'] is None


@pytest.mark.parametrize('bad', [-1, float('nan'), float('inf'), True, '2', 10 ** 400])
def test_readiness_invalid_values_raise(bad):
    with pytest.raises(ValueError):
        existing(departure_readiness=bad)


def test_readiness_invalid_even_if_another_field_missing():
    with pytest.raises(ValueError):
        existing(transfer=None, departure_readiness=-1)


def test_readiness_overflow():
    with pytest.raises(ValueError, match='overflow'):
        existing(departure_readiness=1e308, transfer=1e308)


def test_readiness_cannot_hide_inside_cleanup_or_cargo_work():
    # Work that overlaps cargo is absorbed (cleanup 3: fuel ends 10 = cargo end 10 -> 0 h), but readiness may only start
    # after ALL work, so the same 2 h as readiness is charged: max(10, max(10, 8) + 2) - 10 = 2 h.
    # Hence readiness must not be put into cleanup, and what is parallel work must not be entered as readiness.
    absorbed = existing(baseline_departure=10, cargo_end_with_bunkering=10, bunker_ready=0, preparation=1, transfer=6, cleanup=3, departure_readiness=0)
    after_all_work = existing(baseline_departure=10, cargo_end_with_bunkering=10, bunker_ready=0, preparation=1, transfer=6, cleanup=1, departure_readiness=2)
    assert (absorbed.extra_hours, after_all_work.extra_hours) == (0.0, 2.0)


def test_committed_sensitivity_csv_is_regenerated_exactly_with_zero_readiness():
    # the 63 synthetic rows keep departure readiness 0; compare values, not line endings
    with Path(__file__).with_name('sensitivity.csv').open(newline='', encoding='utf-8') as stream:
        committed = list(csv.DictReader(stream))
    regenerated = [{k: str(v) for k, v in row.items()} for row in scenarios()]
    assert len(committed) == len(regenerated) == 63
    assert committed == regenerated
