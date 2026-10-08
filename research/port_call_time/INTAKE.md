# 급유 시간 자료 입력·검증 도구

[`model.py`](model.py)(PR #114)에 넣을 시간 자료를 받기 전에 형식·단위·시간 순서를 검사하고, 입력이 충분할 때만 기존 계산 함수를 호출한다. 계산 규칙은 바꾸지 않는다.

이 도구는 **입력 검사기**다. 실선 자료를 받았다는 뜻도, 정책 성능을 비교한다는 뜻도, 운영 연결도 아니다. 결과는 입력자가 제공한 값과 근거 수준을 그대로 반영한 계산이며, 기존 공식 평가의 24h/8h 가정과 무관하다.

## 명령 (입력 → 검증 → 계산)

저장소 루트에서 실행한다. 표준 라이브러리만 사용하며 네트워크에 접속하지 않는다.

```sh
# 1) 빈 양식 만들기 (모든 값이 UNKNOWN, 확인 항목은 false)
python -m research.port_call_time.intake template --call-type existing_cargo_call > my_case.json
python -m research.port_call_time.intake template --call-type existing_cargo_call --time-mode absolute --unit minutes
python -m research.port_call_time.intake template --call-type dedicated_bunker_call

# 2) 검증만 (계산 없음). 오류가 있으면 종료 코드 2
python -m research.port_call_time.intake validate my_case.json

# 3) 검증 후 계산. 입력이 부족한 사례는 NOT_COMPUTED와 사유를 출력
python -m research.port_call_time.intake compute my_case.json
python -m research.port_call_time.intake compute research/port_call_time/examples/*.json
```

종료 코드: `0` = 검증 오류 없음(NOT_COMPUTED는 오류가 아님), `2` = 검증 오류·읽을 수 없는 파일·출력 거부.

## 입력 파일

최상위는 `{"schema_version": 1, "cases": [...]}`이다. 알 수 없는 키, 중복 키, `NaN`/`Infinity`는 거부한다.

| 사례 필드 | 설명 |
|---|---|
| `case_id` | 1–64자의 영문·숫자·`_.-`. 이름·이메일·경로는 쓸 수 없다 |
| `call_type` | `existing_cargo_call`(기존 화물 기항에서 급유) 또는 `dedicated_bunker_call`(급유 전용 기항) |
| `unit` | `hours` 또는 `minutes`. 사례 하나에서 단위를 섞지 않는다 |
| `time_mode`, `reference_time` | 기존 기항만. `offset`(기준점으로부터의 시간) 또는 `absolute`(절대시각 + 기준 시각) |
| `source` | `kind` 필수, `reference`·`description`·`obtained_on`(날짜) 선택 |
| `disclosure` | `scope`: `public_ok`·`project_internal`·`private_do_not_publish`·`unknown`. `public_ok`는 `permission_basis` 필수 |
| `confirmations` | 입력자가 직접 확인하는 true/false 항목(아래). 모두 true여야 계산한다 |
| `values` | 값마다 `{"value": 숫자, "basis": 근거}` 또는 `{"at": 시각, "basis": 근거}` |

### 값과 근거

모든 값은 근거(`basis`)를 가져야 한다. 숫자만 쓰면 거부한다.

| `basis` | 뜻 |
|---|---|
| `observed` | 직접 관측·기록된 값 |
| `stakeholder_statement` | 관계자 설명 |
| `estimate` | 추정 |
| `synthetic_assumption` | 합성 가정 |

결과의 `evidence_level`은 사용한 입력 중 **가장 약한 근거**다(observed > stakeholder_statement > estimate > synthetic_assumption). 급유가 없었을 때의 출항 시각(`baseline_departure`)이 관측값이 아니면 결과 `warnings`에 그 사실이 표시된다(추정이면 "ESTIMATE").

### 누락은 UNKNOWN

값이 없으면 `null`, `"UNKNOWN"`, `{"value": null}`, 키 생략 중 아무거나 쓴다. 모두 UNKNOWN이며 **0으로 채우지 않는다**. 0은 `{"value": 0, "basis": ...}`로 명시해야 한다. 빈 문자열·`"0"` 같은 텍스트는 오류다.

### 기존 화물 기항 (`existing_cargo_call`)

| 필드 | 뜻 |
|---|---|
| `baseline_departure` | 급유가 **없었을 때** 출항 시각 |
| `cargo_end_with_bunkering` | 급유 영향(중단 포함)을 반영한 하역 종료 시각 |
| `bunker_ready` | 급유 준비를 시작할 수 있는 시각. 접안 후 대기·접근 제한을 포함 |
| `preparation`, `transfer`, `cleanup` | 준비·이송·마무리 시간(순차). 마무리는 출항 전 남은 급유 관련 작업 전부 |
| `berth_arrival`, `cargo_start` | 선택. **시간 순서 검사에만** 사용한다 |

추가 지연 = max(급유 없는 출항, 급유 반영 하역 종료, 급유 작업 종료) − 급유 없는 출항. 작업 시간이 하역 시간 안에 들어가면 0이다. 따라서 **보도된 급유 작업시간(예: 10시간)을 추가 지연으로 입력하지 않는다.** `work_hours`, `extra_delay_hours` 같은 필드는 거부한다.

### 급유 전용 기항 (`dedicated_bunker_call`)

`detour`(우회), `port_transit`(입출항), `waiting`(대기), `preparation`, `transfer`, `cleanup`을 모두 입력한다. 우회에는 입출항을 넣지 않고, 대기에는 작업 구간을 넣지 않으며, 기준은 "이 기항이 없는 항로"다.

### 입력자 확인 항목 (`confirmations`)

중복 계산을 막기 위해 입력자가 직접 true로 바꾼다. 하나라도 false이거나 없으면 `NOT_COMPUTED`다.

- 기존 기항: `baseline_departure_is_departure_without_bunkering`, `cargo_end_includes_bunkering_interruption`, `bunker_ready_includes_waiting_and_access_restrictions`, `cleanup_includes_all_remaining_bunker_work`
- 전용 기항: `baseline_is_route_without_this_call`, `detour_excludes_port_transit`, `waiting_excludes_work_phases`, `no_phase_counted_twice`

## 시간

- `offset`: 기준점(예: 접안 시각)을 0으로 하는 시간. 모든 시각이 같은 기준점을 쓴다.
- `absolute`: 시각을 `{"at": "2030-03-02T00:30:00+09:00"}`처럼 쓴다. **UTC 오프셋(또는 `Z`)이 없으면 거부**한다. `reference_time`도 같은 형식이며 모든 시각은 그보다 늦거나 같아야 한다. 서로 다른 시간대를 섞어 써도 되고, 자정을 넘겨도 정확히 계산한다. 시간 길이(`preparation` 등)는 항상 `value`로 쓴다.
- 시각 순서(입력된 것만 검사): `berth_arrival` ≤ `cargo_start` ≤ `cargo_end_with_bunkering`, `cargo_start` ≤ `baseline_departure`, `berth_arrival` ≤ `bunker_ready`·`baseline_departure`·`cargo_end_with_bunkering`.
- `minutes`로 입력하면 시간으로 환산해 계산하며 결과 단위는 항상 hours다. 값 하나에 다른 단위를 붙이면 `mixed_units` 오류다. 72시간을 넘는 길이는 단위 확인 경고를 낸다.

## 결과

사례마다 `status`는 `COMPUTED`, `NOT_COMPUTED`, `INVALID` 중 하나다.

- `COMPUTED`: `extra_delay_hours`(hours), `evidence_level`, `input_basis`, `warnings`. 기존 기항은 `breakdown_hours`와 어떤 제약이 결정했는지(`binding_constraint`)도 준다.
- `NOT_COMPUTED`: `missing_fields`와 `reasons`(누락 필드, 미확인 항목). `extra_delay_hours`는 `null`이다.
- `INVALID`: `errors`(코드·필드·설명). 다른 사례는 계속 처리한다.

주요 오류 코드: `bare_value`, `bad_basis`, `bad_number`, `mixed_units`, `naive_time`, `before_reference`, `missing_reference`, `time_order`, `wrong_value_key`, `unknown_field`, `personal_data`, `bad_case_id`, `no_permission_basis`, `duplicate_case_id`.

## 공개 범위와 비공개 자료

- 도구는 업로드·전송을 하지 않는다(네트워크 코드 없음). 결과는 표준출력에 나오고, `--out`을 줄 때만 파일로 쓴다.
- `disclosure.scope`가 `public_ok`(+허락 근거)가 아니면 결과의 `publication_allowed`는 `false`이고, 비공개 자료는 공개 저장소에 넣지 않는다는 경고가 붙는다.
- 그런 결과는 `private/`라는 이름의 폴더 아래에만 `--out`으로 쓸 수 있다. `research/port_call_time/private/`는 `.gitignore`에 들어 있다.
- 자유 서술 칸(`notes`, `source`, `permission_basis`, 값의 `note`)에 이메일 주소·전화번호처럼 보이는 문자열이 있으면 거부한다(보수적 검사이며 ISO 날짜는 제외). 실제 메일 본문·연락처·비공개 자료는 입력 파일에 넣지 않는다.

## 합성 예시와 손계산

[`examples/`](examples/)의 6개 파일은 모두 합성 값이다(`synthetic_assumption`, `public_ok`). 기대값은 `model.py`로 다시 계산하지 않고 아래처럼 손으로 구해 [`test_intake.py`](test_intake.py)에 상수로 넣었다(시간 단위, 기준점 = 접안).

| 예시 | 설명 | 손계산 | 추가 지연 |
|---|---|---|---|
| `01_simultaneous` | 동시 급유 | 준비 가능 0 + 1 + 8 + 1 = 10 ≤ 12 → max(12, 12, 10) − 12 | **0 h** |
| `02_late_start` | 늦게 시작 | 준비 가능 6 + 1 + 8 + 1 = 16 → max(12, 12, 16) − 12 | **4 h** |
| `03_cargo_interrupted` | 하역 중단 | 하역 종료 15, 급유 종료 0 + 1 + 6 + 1 = 8 → max(12, 15, 8) − 12 | **3 h** |
| `04_dedicated` | 전용 기항 | 2 + 1 + 1 + 1 + 8 + 1 | **14 h** |
| `05_insufficient` | 정보 부족 | `transfer`·`cleanup` UNKNOWN | 계산 안 함 |
| `06_absolute_midnight` | 절대시각·자정·혼합 시간대 | 기준 20:00+09:00. 급유 가능 15:30Z = 다음 날 00:30+09:00 = 기준 후 4.5 h. 출항·하역 종료 08:00+09:00 = 12 h. 급유 종료 4.5 + 1 + 8 + 1 = 14.5 → 14.5 − 12 | **2.5 h** |

## 하지 않는 것

- 새 웹 UI, 모델 학습, 정책 성능평가, `arrival()`(마감 판정) 연결은 이번 범위가 아니다.
- DAYTONA 10시간·VISBY 14시간은 동시 작업 보도 시간이며 추가 지연의 실측값이 아니다. 이 도구에 그대로 입력하지 않는다(필요한 필드는 PR #113의 국내 사례 검토 문서 `docs/audits/domestic_lng_time_review_20261008.md`에 있으며, 그 문서는 #113 병합 후 존재한다).
- 기존 공식 평가의 24h/8h 가정·결과·모델은 바꾸지 않는다.
- 입력의 진위는 검증하지 못한다. 근거 구분은 입력자의 자기 신고이며, 형식·순서·단위·범위만 검사한다.
