"""
LangGraph Quick Start - Part 5: 상태(State)를 수동으로 업데이트하기

체크포인터가 있는 그래프에서 update_state()로 노드를 실행하지 않고
상태만 갱신한다. get_state()로 현재 상태를 조회할 수 있다.

사용 방법:
  1. .env에 OPENAI_API_KEY 설정
  2. 가상환경 활성화 후: python quickstart_part5_manual_state_update.py

update_state(config, values, as_node="__input__") 로 입력과 동일한 형식으로 상태 추가.
"""

from typing import Annotated

from dotenv import load_dotenv
from langchain_openai import ChatOpenAI
from typing_extensions import TypedDict

from langgraph.checkpoint.memory import MemorySaver
from langgraph.graph import StateGraph, START, END
from langgraph.graph.message import add_messages

load_dotenv()

# as_node에 사용. 입력으로 상태를 넣을 때의 노드 식별자.
INPUT_NODE = "__input__"


# ---------------------------------------------------------------------------
# State 및 그래프 (Part 1 스타일, 단순 챗봇 + 체크포인터)
# ---------------------------------------------------------------------------

class State(TypedDict):
    """그래프 상태."""

    messages: Annotated[list, add_messages]


def create_graph():
    """기본 챗봇 그래프(체크포인터 포함)를 만든다."""
    llm = ChatOpenAI(model="gpt-3.5-turbo")

    def chatbot(state: State):
        return {"messages": [llm.invoke(state["messages"])]}

    memory = MemorySaver()
    builder = StateGraph(State)
    builder.add_node("chatbot", chatbot)
    builder.add_edge(START, "chatbot")
    builder.add_edge("chatbot", END)
    return builder.compile(checkpointer=memory)


def get_last_message_content(messages: list) -> str:
    """메시지 목록에서 마지막 메시지의 content를 반환한다."""
    if not messages:
        return ""
    last = messages[-1]
    return getattr(last, "content", str(last))


def try_draw_graph(graph, output_path: str = "chatbot_part5.png") -> None:
    """그래프를 PNG로 저장한다."""
    try:
        graph.get_graph().draw_mermaid_png(output_file_path=output_path)
        print(f"그래프 시각화 저장: {output_path}")
    except Exception:
        pass


if __name__ == "__main__":
    graph = create_graph()
    try_draw_graph(graph)

    thread_id = "manual-update-session"
    config = {"configurable": {"thread_id": thread_id}}

    print("--- Part 5: 상태 수동 업데이트 (update_state / get_state) ---\n")

    # 1) 수동으로 메시지만 상태에 추가 (노드 실행 없음)
    print("1) update_state로 메시지만 추가 (chatbot 노드 미실행)")
    config = graph.update_state(
        config,
        {"messages": [("user", "안녕, 나는 주승현이야. 기억해줘.")]},
        as_node=INPUT_NODE,
    )
    state = graph.get_state(config)
    messages = state.values.get("messages", [])
    count = len(messages) if isinstance(messages, list) else 0
    print(f"   현재 메시지 수: {count}")
    if count:
        print(f"   마지막 메시지: {get_last_message_content(messages)}")
    print("   (update_state로 입력만 반영, 노드는 아직 미실행)\n")

    # 2) 그래프 실행 (챗봇이 위 메시지에 대해 응답)
    print("2) invoke로 챗봇 실행 (방금 넣은 메시지에 대해 응답)")
    final = graph.invoke(None, config=config)
    last = get_last_message_content(final.get("messages", []))
    print(f"   챗봇 응답: {last}\n")

    # 3) 다시 수동으로 메시지 추가 후 상태 확인
    print("3) 다시 update_state로 메시지 추가")
    config = graph.update_state(
        config,
        {"messages": [("user", "내 이름이 뭐였지?")]},
        as_node=INPUT_NODE,
    )
    state = graph.get_state(config)
    messages = state.values.get("messages", [])
    count = len(messages) if isinstance(messages, list) else 0
    print(f"   현재 메시지 수: {count}")
    print("   (이후 invoke 시 챗봇이 전체 대화 맥락을 보고 답함)")
