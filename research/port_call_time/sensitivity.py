"""Synthetic fixed-trace timing sensitivity, not a policy performance test."""
import csv
import sys
from .model import existing_call, dedicated_call, arrival


def scenarios():
    for cargo in (8, 12, 16):
        for ready in (0, 4):
            for work in (8, 10, 14):
                for deadline in (728, 736, 760):
                    call = existing_call(baseline_departure=cargo,
                        cargo_end_with_bunkering=cargo, bunker_ready=ready,
                        preparation=1, transfer=work-2, cleanup=1)
                    # Baseline includes existing cargo call, unlike legacy 720h.
                    result = arrival(baseline_hours=720+cargo, calls=[call], deadline_hours=deadline)
                    yield dict(kind='existing',cargo_hours=cargo,ready_hours=ready,
                        work_hours=work,deadline_hours=deadline,extra_hours=call.extra_hours,**result)
    for work in (8, 10, 14):
        for deadline in (728, 736, 760):
            call = dedicated_call(detour=2,port_transit=1,waiting=1,
                                  preparation=1,transfer=work-2,cleanup=1)
            result = arrival(baseline_hours=720,calls=[call],deadline_hours=deadline)
            yield dict(kind='dedicated',cargo_hours=0,ready_hours=0,
                       work_hours=work,deadline_hours=deadline,extra_hours=call.extra_hours,**result)


if __name__ == '__main__':
    rows = list(scenarios())
    writer = csv.DictWriter(sys.stdout, fieldnames=list(rows[0]))
    writer.writeheader()
    writer.writerows(rows)
