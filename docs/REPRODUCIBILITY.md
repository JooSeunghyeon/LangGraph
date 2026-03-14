# 재현성 (Reproducibility)

동일 실험을 재현하기 위한 환경, 명령, 데이터를 정리한 문서이다.

**저장소 (실험 구현·지표 기록)**: [https://github.com/JooSeunghyeon/LangGraph](https://github.com/JooSeunghyeon/LangGraph)

---

## 1. 환경

- **Python**: 3.9 이상 권장. 프로젝트는 3.9에서 실행 검증됨.
- **OS**: macOS / Linux (Windows에서도 동작 가능하나 미검증).
- **의존성**: 프로젝트 루트의 `requirements.txt` 사용.

```bash
cd /path/to/lang_graph
pip install -r requirements.txt
```

- **고정 버전으로 재현할 때**: 다음으로 전체 스냅샷을 남길 수 있다.

```bash
pip freeze > pip_freeze_snapshot.txt
```

---

## 2. 환경 변수

- **필수**: `.env`에 `OPENAI_API_KEY` 설정.
- **참고**: `.env.example`에 필요한 키 목록과 주석이 있음. 복사 후 값을 채운다.

```bash
cp .env.example .env
# .env 편집: OPENAI_API_KEY=sk-...
```

---

## 3. 시드

- 실험 러너에서 난수를 쓰는 부분은 현재 제한적이다. 재현 시에는 **고정 시드**를 쓰는 것을 권장한다.
- **CLI**: `--seed 42`
- **YAML 설정**: `seed: 42` (예: `experiments/configs/baseline.yaml`, `experiments/configs/variants.yaml`).

---

## 4. 실행 순서

### 단일 그래프, 기본 프롬프트 5개

```bash
cd /path/to/lang_graph
python experiments/run_experiments.py --graph part1 --model gpt-3.5-turbo --seed 42 --output experiments/results/metrics.jsonl
```

### 설정 파일로 실행 (baseline)

```bash
python experiments/run_experiments.py --config experiments/configs/baseline.yaml --output experiments/results/baseline.jsonl
```

### 변경/확장 실험 (여러 그래프)

```bash
python experiments/run_experiments.py --config experiments/configs/variants.yaml --output experiments/results/variants.jsonl
```

### 동일 실험 반복 2회

```bash
python experiments/run_experiments.py --graph part1 --repeat 2 --seed 42 --output experiments/results/repeat2.jsonl
```

---

## 5. 데이터 (입력 질문 목록)

- **기본값**: `experiments/run_experiments.py` 내부의 `DEFAULT_PROMPTS` (한국어 질문 5개).
  - "한국의 수도는 어디야?"
  - "서울 날씨 어때?"
  - "가장 시원한 도시 알려줘"
  - "안녕하세요."
  - "1+1은?"
- **직접 지정**: `--prompts "질문1" "질문2" "질문3"` 형태로 덮어쓸 수 있다.
- 고정된 질문 목록을 파일로 두고 싶다면, 해당 파일을 프로젝트에 포함한 뒤 스크립트에서 읽도록 확장하면 된다.

---

## 6. 결과 파일

- **위치**: 기본값 `experiments/results/metrics.jsonl`. `--output`으로 변경 가능.
- **형식**: 한 줄에 한 런의 JSON. 필드 설명은 [APPENDIX.md](APPENDIX.md)의 지표 정의 참고.
- **재현 확인**: 동일 환경·시드·설정으로 위 명령을 다시 실행한 뒤, 생성된 JSONL의 `latency_seconds`·`llm_calls`·`success` 등을 비교하면 된다. (API 응답은 비결정적일 수 있어 지연 시간 등은 완전 일치하지 않을 수 있음.)
