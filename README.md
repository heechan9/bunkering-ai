# bunkering-ai

선박 벙커시유 의사결정을 위한 강화학습 프로젝트입니다. 합성 항해 환경에서 rule-based baseline과 Double DQN 에이전트를 비교합니다.

## 팀 구성

- 강화학습/모델 개발: 환경, baseline, DQN 학습 파이프라인
- 데이터·도메인 분석: 연료 가격, 환율, 항로 및 규제 데이터 검토
- 서비스·문서화: 실험 결과 정리와 프로젝트 산출물 관리

## 폴더 구조

```text
agents/     DQN 에이전트와 신경망 구현
configs/    학습 하이퍼파라미터 YAML
docs/       기술 설계 문서
envs/       Gymnasium 기반 BunkeringEnv
scripts/    baseline 실행 및 DQN 학습 스크립트
tests/      환경·에이전트 단위 테스트
```

## 빠른 시작

```bash
pip install -r requirements.txt
python scripts/baseline.py
python scripts/train.py --episodes 20
pytest tests -q
```

`runs/`, `results/`, `handoff_notes/`는 생성 산출물 또는 검토 자료이므로 Git에서 제외됩니다.
