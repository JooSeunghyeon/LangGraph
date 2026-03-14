# LangGraph Quick Start 정리

## LangGraph를 왜 쓰는가?

**LangGraph**는 **상태를 가진 에이전트/챗봇**을 **그래프**로 설계하고 실행하기 위한 프레임워크다.

- **LLM만 쓰면**: 한 번 호출 → 한 번 응답. 대화 이력·도구 호출·중단·재개를 직접 다 설계해야 함.
- **LangGraph를 쓰면**: “노드(작업) + 엣지(흐름) + 상태”를 정의해 두면, **대화 유지**, **도구 사용**, **사람 개입**, **상태 조회/수정**, **과거 시점 복원** 등을 프레임워크가 지원한다.

그래서 **여러 턴이 이어지는 챗봇**, **도구를 쓰는 에이전트**, **검토·승인 절차가 있는 플로우**를 만들 때 LangGraph를 쓰고, **그걸 위해** 이 튜토리얼처럼 단계별로 익히는 것이다.

---

## 왜 써야 하는가? (쓰는 이유 정리)

| 필요하다고 느끼는 것 | LangGraph 없이 | LangGraph로 |
|----------------------|----------------|------------|
| 대화 이력 유지 | 서버/DB에 메시지 저장·로드 직접 구현 | 체크포인터 + `thread_id`로 세션별 상태 자동 유지 |
| LLM + 도구(검색·API) | if/else·루프로 “도구 쓸지 말지” 직접 분기 | `ToolNode` + `tools_condition`으로 “도구 호출 → 결과 반영 → 다시 LLM” 흐름 한 번에 정의 |
| 사람 검토 후 재개 | 플래그·DB·큐로 “멈춤/재개” 직접 구현 | `interrupt_after` + 같은 `thread_id`로 `invoke` 재호출만 하면 재개 |
| 상태를 코드에서 수정 | 내부 변수/DB 스키마 직접 다룸 | `update_state` / `get_state`로 “지금 상태 조회·수동 수정” API 사용 |
| 과거 시점 보기/되감기 | 로그·DB 쿼리 직접 설계 | `get_state_history`로 체크포인트 이력 조회 |

정리하면, **“대화·도구·사람·상태·이력”을 한 구조(그래프 + 상태)로 다루고 싶을 때** LangGraph를 쓰는 것이고, 그걸 **표준 방식**으로 하기 위해 이 튜토리얼을 진행한 것이다.

---

## 프로젝트 구조와 Part별 역할

```
LangGraph/
├── README.md                    # 이 정리 문서
├── requirements.txt
├── .env.example / .env
├── quickstart_part1_chatbot.py                      # 기본 챗봇
├── quickstart_part2_chatbot_with_tools.py           # 도구 추가
├── quickstart_part3_chatbot_with_memory.py          # 메모리(세션 유지)
├── quickstart_part4_human_in_the_loop.py            # Human-in-the-loop
├── quickstart_part5_manual_state_update.py          # 상태 수동 업데이트
├── quickstart_part6_part7_custom_state_and_time_travel.py  # 상태 커스터마이징 + 시간 여행
└── chatbot*.png                 # 그래프 시각화
```

---

## Part별 요약: 뭘 배우고, 왜 쓰는지

### Part 1: 기본 챗봇
- **하는 일**: 사용자 메시지 → 한 노드(챗봇) → LLM 한 번 호출 → 응답.
- **개념**: `StateGraph`, `State`(메시지 리스트), `add_messages` 리듀서, `compile()`.
- **왜**: “그래프 = 상태 + 노드 + 엣지”라는 기본 패턴을 익히기 위해. 이후 Part는 전부 이걸 확장한 것.

### Part 2: 도구(Tool)로 챗봇 강화
- **하는 일**: 챗봇이 “도구 쓸지” 결정 → 도구 실행 → 결과를 다시 챗봇에 넘겨 최종 답 생성.
- **개념**: `@tool`, `bind_tools`, `ToolNode`, `tools_condition`, 조건부 엣지(챗봇 → 도구 or 종료).
- **왜**: 날씨·검색·API 같은 **도구를 쓰는 에이전트**가 필요할 때, “언제 도구를 부르고, 결과를 어떻게 이어갈지”를 그래프로 명확히 정의하기 위해.

### Part 3: 챗봇에 메모리 추가
- **하는 일**: 같은 `thread_id`로 계속 호출하면 이전 대화가 유지됨. “거기”처럼 지시대명사로 이어서 말해도 맥락 유지.
- **개념**: `MemorySaver`(체크포인터), `compile(checkpointer=...)`, `config={"configurable": {"thread_id": "..."}}`.
- **왜**: **세션/대화 단위로 상태를 유지**해야 할 때. 매 호출을 “처음부터 새 대화”가 아니라 “이어지는 대화”로 만들기 위해.

### Part 4: Human-in-the-loop
- **하는 일**: 특정 노드(예: 챗봇) **다음에** 실행을 멈추고, 사람이 확인한 뒤 **같은 thread_id로 다시 invoke**하면 그 시점부터 재개.
- **개념**: `interrupt_after=["chatbot"]`, 체크포인터 필수.
- **왜**: **응답 검토·승인·수정**이 필요한 플로우(고객 대응, 내부 검수 등)에서 “한 번 멈추고, 사람이 보고, 이어가기”를 표준 방식으로 하기 위해.

### Part 5: 상태(State)를 수동으로 업데이트
- **하는 일**: 노드를 실행하지 않고, `update_state(config, values, as_node="__input__")`로 상태(예: 메시지)만 넣고, `get_state(config)`로 현재 상태 조회.
- **개념**: `update_state`, `get_state`, `as_node="__input__"`.
- **왜**: **시스템/다른 서비스가 메시지를 주입**하거나, **현재 상태만 조회**해 UI·로깅에 쓰거나, 테스트 시 상태를 직접 세팅할 때 필요하기 위해.

### Part 6: 상태 커스터마이징
- **하는 일**: State에 `messages`(추가만), `llm_calls`(숫자 누적)처럼 **키마다 다른 리듀서** 지정. 기본은 “덮어쓰기”, `Annotated[타입, reducer]`로 “누적/병합” 제어.
- **개념**: `Annotated[list, add_messages]`, `Annotated[int, operator.add]`.
- **왜**: “메시지는 append, 통계/카운트는 더하기”처럼 **상태 필드별로 갱신 규칙을 다르게** 두기 위해.

### Part 7: 시간 여행(Time Travel)
- **하는 일**: `get_state_history(config, limit=N)`으로 **과거 체크포인트 목록**을 가져와, 그 시점의 메시지 수·상태 등을 확인.
- **개념**: `get_state_history`, 체크포인터.
- **왜**: **디버깅**, “그 시점으로 되감기”, **실행 이력 분석**을 할 때, 로그를 직접 파지 않고 그래프가 저장한 체크포인트를 활용하기 위해.

---

## 한 줄로 정리

- **Part 1**: 그래프로 “말하면 답하는” 기본 챗봇.
- **Part 2**: 그 챗봇이 **도구**를 골라 쓰게 함.
- **Part 3**: **대화가 이어지게** (메모리/세션).
- **Part 4**: **한 번 멈췄다가 사람 확인 후** 이어가기.
- **Part 5**: **상태만 넣고/조회** (노드 안 돌리고).
- **Part 6**: 상태 **필드마다 갱신 방식** 다르게 (리듀서).
- **Part 7**: **과거 시점 상태** 보기 (시간 여행).

---

## 실행 방법 (공통)

```bash
cd /Users/juseunghyeon/Document/LangGraph
source venv/bin/activate
# .env 에 OPENAI_API_KEY 설정 필수

python quickstart_part1_chatbot.py
python quickstart_part2_chatbot_with_tools.py
python quickstart_part3_chatbot_with_memory.py
python quickstart_part4_human_in_the_loop.py
python quickstart_part5_manual_state_update.py
python quickstart_part6_part7_custom_state_and_time_travel.py
```

---

## 참고 링크

- [LangGraph 공식 개요](https://docs.langchain.com/oss/python/langgraph/overview)
- [Quick Start Part 1 번역 (루닥스 블로그)](https://rudaks.tistory.com/entry/%EB%B2%88%EC%97%ADlanggraph-tutorial-Quick-Start-Part-1-%EA%B8%B0%EB%B3%B8-%EC%B1%97%EB%B4%87-%EB%A7%8C%EB%93%A4%EA%B8%B0)
