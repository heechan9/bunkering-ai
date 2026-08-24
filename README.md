# bunkering-ai

선박 벙커시유 의사결정을 위한 강화학습 프로젝트입니다. 합성 항해 환경에서 rule-based baseline을 평가하고 Double DQN 학습 파이프라인을 검증합니다. Rule-based와 DQN의 공식 동일조건 성능비교는 아직 수행하지 않았습니다.

## 팀 구성

- 강화학습/모델 개발: 환경, baseline, DQN 학습 파이프라인
- 데이터·도메인 분석: 연료 가격, 환율, 항로, 규제 및 공공데이터 검토
- 서비스·문서화: 실험 결과 정리와 프로젝트 산출물 관리

## 공공데이터 활용

공공데이터포털의 울산항만공사 `벙커링정박지 신청현황` 6,028건을 분석하여
총톤수·벙커량·예정 시작일·종료일 등 실제 업무변수의 구조와 분포를 확인했습니다.
이 분석은 향후 시나리오 설계와 실증 범위 검토를 위한 도메인 참고자료입니다.

현재 Rule-based 공식 평가와 Double DQN smoke test는 합성 데이터 기반입니다.
공공데이터를 DQN 학습 입력이나 공식 성능평가 데이터로 사용하지 않았으며, 실시간 API
연동도 아직 구현하지 않았습니다. 출처·기초통계·한계는
[`docs/data/upa_bunkering_anchorage.md`](docs/data/upa_bunkering_anchorage.md)에 기록했습니다.

```bash
python scripts/analyze_upa_public_data.py
pytest tests/test_upa_public_data.py -q
```

## 폴더 구조

```text
agents/       DQN 에이전트와 신경망 구현
configs/      학습 하이퍼파라미터 YAML
data/public/  출처와 해시를 기록한 공공데이터 사본
docs/         기술 설계·데이터 출처·제출 문서
envs/         Gymnasium 기반 BunkeringEnv
scripts/      baseline·DQN·공공데이터 분석 스크립트
tests/        환경·에이전트·공공데이터 단위 테스트
```

## 빠른 시작

```bash
pip install -r requirements.txt
python scripts/baseline.py
python scripts/train.py --episodes 20
pytest tests -q
```

`runs/`, 일반 `results/`, `handoff_notes/`는 생성 산출물 또는 검토 자료이므로 Git에서
제외됩니다. 제출 근거로 버전 관리하는 공공데이터 요약 산출물은
`results/public_data/`에 한정합니다.
