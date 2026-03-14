# 부록: 실험 설정 및 지표 정의

**실험 구현·지표 기록** 코드: [https://github.com/JooSeunghyeon/LangGraph](https://github.com/JooSeunghyeon/LangGraph) (`experiments/`)

---

## A.1 실험 설정 요약

| 항목 | 설명 | 기본값 / 예시 |
|------|------|----------------|
| 그래프 | Part 1~7 대응 그래프 ID | `part1`, `part2`, `part3`, `part4`, `part5`, `part6_part7` |
| 모델 | OpenAI 채팅 모델명 | `gpt-3.5-turbo` |
| 입력 개수 | 프롬프트(질문) 개수 | 기본 5개 (`DEFAULT_PROMPTS`) |
| 반복 수 | 동일 설정당 반복 실행 횟수 | 1 |
| 시드 | 재현용 랜덤 시드 | 없음(미지정 시) 또는 `42` |

- **단일 실험**: `--graph part1 --model gpt-3.5-turbo`
- **변경/확장 실험**: `--config experiments/configs/variants.yaml` (여러 `graphs` 또는 `models` 조합)

---

## A.2 지표 정의

| 지표 | 단위/타입 | 설명 |
|------|-----------|------|
| `latency_seconds` | 초 (float) | 한 번의 `invoke` 호출에 걸린 시간 |
| `input_tokens` | 정수 | 해당 런에서 소비된 입력(프롬프트) 토큰 수. 콜백/메타데이터에서 수집 |
| `output_tokens` | 정수 | 해당 런에서 생성된 출력 토큰 수 |
| `llm_calls` | 정수 | 해당 런에서 LLM이 호출된 횟수. 콜백 또는 State의 `llm_calls` |
| `tool_calls` | 정수 | 해당 런에서 도구가 호출된 횟수. 메시지 내 `tool_calls` 개수 |
| `success` | bool | `invoke`가 예외 없이 완료되면 `true` |
| `error_message` | 문자열 또는 null | 실패 시 예외 메시지 |

- **experiment_id**: 런 식별자 (예: `part1_gpt-3.5-turbo_0`).
- **input_summary**: 입력 프롬프트 요약(최대 80자).
- **timestamp**: UTC 기준 기록 시각 (ISO 8601).

---

## A.3 결과 요약 (예시)

실험 실행 후 `experiments/results/metrics.jsonl`에서 라인별로 한 런씩 기록된다.  
아래는 Part 1 기준 5개 프롬프트 1회 실행 시 기대되는 형태의 요약 예시이다.

| graph_name | 런 수 | 평균 지연(초) | 평균 llm_calls | success 비율 |
|------------|-------|----------------|----------------|--------------|
| part1      | 5     | (실행 결과에 따라 채움) | 1 | 100% |

- 실제 수치는 `python experiments/run_experiments.py --graph part1` 실행 후 생성된 JSONL을 집계하여 채운다.
- 여러 그래프/모델 조합 실험은 `--config experiments/configs/variants.yaml` 실행 후 동일 형식으로 표를 확장할 수 있다.

---

## A.4 그래프 구조 요약

- **Part 1**: START → chatbot → END. 상태: `messages`만.
- **Part 2**: START → chatbot ⇄ tools → END. 조건부: 도구 호출 시 tools 노드 경유.
- **Part 3**: Part 2와 동일 구조 + MemorySaver 체크포인터.
- **Part 4**: Part 3 + `interrupt_after=["chatbot"]`.
- **Part 5**: Part 1과 동일 단순 구조 + MemorySaver (update_state/get_state용).
- **Part 6/7**: Part 1과 유사 + State에 `llm_calls`(리듀서), MemorySaver. 시간 여행은 `get_state_history`로 별도 활용.

자세한 설명은 [README.md](../README.md)의 Part별 요약을 참고한다.
