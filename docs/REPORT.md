# LangGraph 기반 챗봇 변형 실험 및 지표 기록

기술 보고서 초안. 실험 방법·지표 정의·재현성은 [APPENDIX.md](APPENDIX.md), [REPRODUCIBILITY.md](REPRODUCIBILITY.md)와 일치하도록 유지한다.

---

## 제목

LangGraph를 이용한 챗봇 아키텍처 변형 실험 및 성능 지표 수집

---

## 초록

본 보고서는 LangGraph 공식 Quick Start에서 다루는 Part 1~7 챗봇 변형을 대상으로, 실험 러너와 지표 수집 파이프라인을 구현하고 기본 실험을 수행한 결과를 정리한다. 지연 시간, LLM 호출 수, 도구 호출 수, 성공 여부 등을 JSONL로 기록하며, 설정 파일을 통한 그래프·모델 조합 실험과 재현을 지원한다.

---

## 1. 서론

LangGraph는 상태 기반 에이전트/챗봇을 그래프(노드·엣지·상태)로 설계하고 실행하는 프레임워크이다. 튜토리얼에서는 기본 챗봇(Part 1), 도구 사용(Part 2), 메모리·Human-in-the-loop·상태 수동 조작·커스텀 상태·시간 여행(Part 3~7)을 단계별로 소개한다. 본 작업은 이 변형들에 대해 (1) 동일한 인터페이스로 실행하고 (2) 지표를 자동 수집하며 (3) 변경·확장 실험(여러 그래프/모델 조합)과 재현이 가능하도록 실험 인프라를 구축하고, 그 구현 경험과 결과를 문서화하는 것을 목표로 한다.

---

## 2. 방법

### 2.1 그래프 구성

- **Part 1**: 단일 노드(챗봇), 메시지 리스트 상태, 체크포인터 없음.
- **Part 2**: 챗봇 + 도구 노드, 조건부 엣지(도구 호출 시 tools 경유), 체크포인터 없음.
- **Part 3**: Part 2와 동일 구조 + MemorySaver 체크포인터.
- **Part 4**: Part 3 + `interrupt_after=["chatbot"]` (Human-in-the-loop).
- **Part 5**: Part 1과 유사 + MemorySaver (update_state/get_state 활용).
- **Part 6/7**: Part 1과 유사 + State에 `llm_calls` 리듀서, MemorySaver.

각 그래프는 실험용 빌더에서 **모델명을 인자로 받아** 동일 인터페이스로 생성되며, `invoke` 한 번을 한 런으로 기록한다.

### 2.2 실험 설계

- **입력**: 고정 질문 목록(기본 5문장) 또는 CLI/설정으로 지정한 프롬프트.
- **변인**: 그래프 종류(part1~part6_part7), 모델명(예: gpt-3.5-turbo), 반복 횟수, 시드(선택).
- **출력**: 런별 지표를 담은 JSONL (experiment_id, graph_name, latency_seconds, input_tokens, output_tokens, llm_calls, tool_calls, success, error_message, timestamp 등).

지표 정의와 설정 요약은 [APPENDIX.md](APPENDIX.md)를 참고한다.

---

## 3. 실험 설정

- **환경**: Python 3.9+, `requirements.txt` 기준 의존성, `.env`에 `OPENAI_API_KEY` 설정.
- **재현**: `--seed 42` 또는 설정 파일의 `seed: 42`, 동일 명령으로 재실행. 상세 절차는 [REPRODUCIBILITY.md](REPRODUCIBILITY.md)에 기술한다.

---

## 4. 결과 요약

- Part 1 기준 5개 프롬프트 1회 실행 시, 런당 1회 LLM 호출, 지연 시간은 질문에 따라 수 초 내외로 관찰된다.
- 토큰 수는 LLM 응답 메타데이터에 따라 콜백에서 채워지며, 환경에 따라 0으로 남을 수 있다. 이 경우에도 지연 시간과 `llm_calls`는 활용 가능하다.
- Part 2 등 도구 사용 그래프에서는 `tool_calls`가 0 이상으로 기록되며, Part 6/7에서는 State의 `llm_calls`가 누적되어 반영된다.

구체적인 수치는 `python experiments/run_experiments.py --graph part1` (및 variants 설정) 실행 후 생성된 JSONL을 집계하여 [APPENDIX.md](APPENDIX.md) A.3 결과 요약 표에 채울 수 있다.

---

## 5. 결론

LangGraph Quick Start Part 1~7에 대응하는 실험 러너와 지표 수집을 구현했고, 설정 파일을 통한 그래프·모델 조합 실험과 재현 절차를 문서화했다. 구현 시 고려한 설계 선택(상태 vs 콜백, Part별 지표 수집 방식)과 이슈·우회는 [IMPLEMENTATION_NOTES.md](IMPLEMENTATION_NOTES.md)에 정리되어 있다. 향후 토큰 메타데이터 수집 안정화, 스트리밍·재개 시나리오까지 포함한 지표 확장, 추가 모델/그래프 변형 실험이 가능하다.

---

## 참고문헌

- LangGraph Overview. https://docs.langchain.com/oss/python/langgraph/overview
- LangChain Python Documentation. https://python.langchain.com/
- 본 프로젝트 README: [../README.md](../README.md)

---

## 검토 및 보완 체크리스트

실험·문서 일관성 확인용이다.

- [ ] **실험 방법**: REPORT §2와 IMPLEMENTATION_NOTES의 그래프·실험 설계가 일치하는가?
- [ ] **지표 정의**: REPORT·APPENDIX의 지표 설명이 동일한가? (latency_seconds, llm_calls, tool_calls, success 등)
- [ ] **재현성**: REPRODUCIBILITY의 환경·시드·명령으로 동일 실험이 재현 가능한가?
- [ ] **결과**: APPENDIX A.3 표에 실제 실행 결과를 채웠는가?
- [ ] **참고문헌**: 누락된 공식 문서·논문이 있으면 추가한다.
