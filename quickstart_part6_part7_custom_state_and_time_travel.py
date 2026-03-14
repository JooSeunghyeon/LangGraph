"""
LangGraph Quick Start - Part 6 & 7

Part 6: 상태 커스터마이징
  - State에 여러 키 + 서로 다른 리듀서 사용 (messages는 add_messages, llm_calls는 operator.add)
  - 리듀서 없으면 덮어쓰기, Annotated[타입, reducer]로 누적/병합 방식 지정

Part 7: 시간 여행 (Time Travel)
  - get_state_history(config, limit=N) 로 과거 체크포인트 목록 조회
  - 특정 시점 상태 확인·디버깅·되감기 시나리오에 활용

사용 방법:
  1. .env에 OPENAI_API_KEY 설정
  2. 가상환경 활성화 후: python quickstart_part6_part7_custom_state_and_time_travel.py
"""

import operator
from typing import Annotated

from dotenv import load_dotenv
from langchain_openai import ChatOpenAI
from typing_extensions import TypedDict

from langgraph.checkpoint.memory import MemorySaver
from langgraph.graph import StateGraph, START, END
from langgraph.graph.message import add_messages

load_dotenv()


# ---------------------------------------------------------------------------
# Part 6: 상태 커스터마이징 - 여러 키 + 리듀서
# ---------------------------------------------------------------------------

class State(TypedDict):
    """커스텀 상태: messages는 추가만, llm_calls는 누적 합."""

    messages: Annotated[list, add_messages]
    llm_calls: Annotated[int, operator.add]


def create_graph():
    """llm_calls를 증가시키는 챗봇 그래프 (체크포인터 + 커스텀 상태)."""
    llm = ChatOpenAI(model="gpt-3.5-turbo")

    def chatbot(state: State):
        response = llm.invoke(state["messages"])
        return {
            "messages": [response],
            "llm_calls": 1,
        }

    memory = MemorySaver()
    builder = StateGraph(State)
    builder.add_node("chatbot", chatbot)
    builder.add_edge(START, "chatbot")
    builder.add_edge("chatbot", END)
    return builder.compile(checkpointer=memory)


def get_last_content(messages: list) -> str:
    """마지막 메시지 content."""
    if not messages:
        return ""
    last = messages[-1]
    return getattr(last, "content", str(last)) or ""


def run_part6(graph, config: dict) -> None:
    """Part 6: 커스텀 상태(리듀서) 동작 확인."""
    print("--- Part 6: 상태 커스터마이징 (리듀서) ---\n")

    for i, question in enumerate(["첫 질문이야.", "두 번째 질문이야."], start=1):
        graph.invoke(
            {"messages": [("user", question)], "llm_calls": 0},
            config=config,
        )
        state = graph.get_state(config)
        vals = state.values
        calls = vals.get("llm_calls", 0)
        msgs = vals.get("messages", [])
        print(f"  턴 {i} 후 - llm_calls: {calls}, 메시지 수: {len(msgs) if isinstance(msgs, list) else 0}")

    print("  (llm_calls는 operator.add 리듀서로 1씩 누적됨)\n")


def run_part7(graph, config: dict) -> None:
    """Part 7: 시간 여행 - 체크포인트 이력 조회."""
    print("--- Part 7: 시간 여행 (get_state_history) ---\n")

    history = list(graph.get_state_history(config, limit=5))
    print(f"  최근 체크포인트 수: {len(history)}")

    for i, snap in enumerate(reversed(history), start=1):
        cid = snap.config.get("configurable", {}).get("checkpoint_id", "")[:8]
        vals = snap.values
        msgs = vals.get("messages", [])
        count = len(msgs) if isinstance(msgs, list) else 0
        calls = vals.get("llm_calls", 0)
        print(f"  스냅샷 {i}: checkpoint_id={cid}..., messages={count}, llm_calls={calls}")

    print("  (과거 시점 상태로 분석·되감기 등에 활용)\n")


def try_draw_graph(graph, output_path: str = "chatbot_part6_part7.png") -> None:
    """그래프 시각화 저장."""
    try:
        graph.get_graph().draw_mermaid_png(output_file_path=output_path)
        print(f"그래프 시각화 저장: {output_path}\n")
    except Exception:
        pass


if __name__ == "__main__":
    graph = create_graph()
    try_draw_graph(graph)

    thread_id = "part6-part7-demo"
    config = {"configurable": {"thread_id": thread_id}}

    run_part6(graph, config)
    run_part7(graph, config)
