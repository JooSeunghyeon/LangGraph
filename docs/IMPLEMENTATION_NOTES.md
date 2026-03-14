# LangGraph 실험 구현 경험 정리

**실험 구현·지표 기록** 소스 위치: [https://github.com/JooSeunghyeon/LangGraph](https://github.com/JooSeunghyeon/LangGraph) (`experiments/`)

---

## 1. 설계 선택: 상태 vs 콜백

### 상태에 지표 넣기 (Part 6/7)

- **방식**: `State`에 `llm_calls: Annotated[int, operator.add]`처럼 리듀서를 두고, 각 노드에서 `return {"llm_calls": 1}` 등으로 갱신.
- **장점**: 그래프 실행 결과만으로 지표를 읽을 수 있음. 별도 콜백 없이 `invoke` 반환값에서 `state["llm_calls"]` 추출 가능.
- **단점**: 그래프 정의와 State 스키마를 실험용으로 수정해야 함. Part 1~5처럼 기존 그래프를 그대로 쓰려면 콜백/후처리가 필요.

### 콜백만 쓰기

- **방식**: `BaseCallbackHandler`로 `on_llm_start`/`on_llm_end`에서 호출 횟수·토큰 수 집계.
- **장점**: 기존 Quick Start 스크립트를 수정하지 않고도 모든 Part에 공통 적용 가능.
- **단점**: 토큰 수는 LLM 응답 메타데이터에 의존하며, 환경에 따라 `response_metadata` 또는 `usage_metadata`만 채워질 수 있음. 이 경우 0으로 남을 수 있음.

### 본 프로젝트에서의 선택

- **둘 다 사용**: 콜백으로 LLM 호출 수·토큰 수를 수집하고, Part 6/7처럼 State에 `llm_calls`가 있으면 최종값은 State를 우선해 채움. 도구 호출 수는 실행 후 `messages`에서 `tool_calls` 개수를 세어 기록.

---

## 2. Part별 지표 수집 방법

| Part | LLM 호출 수 | 토큰 수 | 도구 호출 수 | 비고 |
|------|-------------|---------|--------------|------|
| Part 1 | 콜백 또는 1로 고정 | 콜백 | 0 | 체크포인터 없음 |
| Part 2 | 콜백 | 콜백 | messages에서 tool_calls 카운트 | 도구 사용 시 1회 이상 |
| Part 3 | 콜백 | 콜백 | messages에서 tool_calls 카운트 | 체크포인터 사용 |
| Part 4 | 콜백 | 콜백 | messages에서 tool_calls 카운트 | interrupt_after 사용 |
| Part 5 | 콜백 | 콜백 | 0 | update_state/get_state용 |
| Part 6/7 | State의 `llm_calls` 또는 콜백 | 콜백 | 0 | 커스텀 리듀서로 llm_calls 누적 |

- **지연 시간**: 모든 Part 공통으로 `invoke` 전후 `time.perf_counter()`로 측정.
- **성공/실패**: `invoke` 예외 시 `success=False`, `error_message`에 예외 메시지 저장.

---

## 3. 실험 러너 설계

### 그래프 추상화

- Quick Start 스크립트(Part 1~7)는 그대로 두고, `experiments/graphs/builders.py`에서 **모델명을 인자로 받는** 그래프 빌드 함수를 별도 정의.
- `experiments/graphs/__init__.py`의 `GRAPH_REGISTRY`에 `part1`~`part6_part7`를 등록하고, `get_graph(name, model)`로 컴파일된 그래프를 반환.

### 설정 포맷

- **CLI**: `--graph`, `--model`, `--repeat`, `--seed`, `--output`, `--prompts`, `--config`.
- **YAML 설정**: `--config`로 파일 경로 지정 시 `graph`/`model`/`repeat`/`seed` 적용.  
  `graphs`(리스트), `models`(리스트)가 있으면 해당 조합 모두 실행해 지표 기록.

### 입력 시나리오

- 기본값은 `DEFAULT_PROMPTS`(고정 질문 5개). `--prompts "질문1" "질문2"`로 덮어쓰기 가능.
- 재현성을 위해 시드 고정 시 `--seed 42`, 설정 파일에 `seed: 42` 지정.

### 결과 저장

- 한 줄에 한 런씩 JSON으로 기록하는 JSONL. 필드: `experiment_id`, `graph_name`, `input_summary`, `latency_seconds`, `input_tokens`, `output_tokens`, `llm_calls`, `tool_calls`, `success`, `error_message`, `timestamp`.

---

## 4. 이슈 및 우회

### 스트리밍 시 토큰 수 집계

- 현재 실험 러너는 `invoke`만 사용. `stream`으로 돌릴 경우 이벤트 단위로 콜백이 호출되므로, 동일 콜백으로 토큰을 누적할 수 있으나, “한 턴” 단위로 끊어서 집계하려면 스트리밍 종료 시점에 한 번만 읽도록 설계하는 것이 좋음.

### 토큰 수가 0으로 나오는 경우

- OpenAI 등 일부 모델은 `on_llm_end`에 넘어오는 `response_metadata`/`usage_metadata` 구조가 다르거나 비어 있을 수 있음. 이 경우 토큰 수는 0으로 남고, 지연 시간과 `llm_calls`만 활용할 수 있음.

### Part 4 (Human-in-the-loop)

- `interrupt_after`로 중단된 뒤 재개할 때까지가 “한 번의 실험 런”이 아니라, 실험 러너는 “첫 번째 invoke까지”를 한 런으로 두고 지표를 기록함. 재개 시나리오까지 포함한 지표가 필요하면 별도 스크립트나 시나리오 플래그를 두어 처리하는 것이 좋음.

### 체크포인터 사용 그래프(Part 3~7)

- 매 런마다 서로 다른 `thread_id`(예: `exp-{run_id}`)를 사용해 세션을 격리하고, 이전 런의 상태가 다음 런에 영향을 주지 않도록 함.
