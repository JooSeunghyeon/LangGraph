"""
LangGraph Quick Start - Part 4: Human-in-the-loop

챗봇 노드 실행 후 중단(interrupt_after)하여 사람이 응답을 검토한 뒤
재개할 수 있게 한다. 체크포인터 필수.

사용 방법:
  1. .env에 OPENAI_API_KEY 설정
  2. 가상환경 활성화 후: python quickstart_part4_human_in_the_loop.py

동일 config(thread_id)로 다시 invoke하면 중단 지점부터 재개된다.
"""

from typing import Annotated

from dotenv import load_dotenv
from langchain_core.tools import tool
from langchain_openai import ChatOpenAI
from typing_extensions import TypedDict

from langgraph.checkpoint.memory import MemorySaver
from langgraph.graph import StateGraph, START, END
from langgraph.graph.message import add_messages
from langgraph.prebuilt import ToolNode, tools_condition

load_dotenv()


# ---------------------------------------------------------------------------
# 도구 정의 (Part 2/3와 동일)
# ---------------------------------------------------------------------------

@tool
def get_weather(location: str) -> str:
    """현재 날씨를 조회한다. location은 도시 이름(예: 서울, 인천)이다."""
    if location in ["서울", "인천"]:
        return "현재 기온은 20도이고 구름이 많아."
    return "현재 기온은 30도이며 맑아."


@tool
def get_coolest_cities() -> str:
    """가장 시원한 도시 목록을 반환한다."""
    return "서울, 인천"


# ---------------------------------------------------------------------------
# State 및 그래프 (Part 3 + interrupt_after)
# ---------------------------------------------------------------------------

class State(TypedDict):
    """그래프 상태. add_messages 리듀서로 메시지를 덮어쓰지 않고 추가한다."""

    messages: Annotated[list, add_messages]


def create_chatbot_with_human_review_graph():
    """챗봇 응답 후 인간 검토를 위해 중단하는 그래프를 만든다."""
    tools = [get_weather, get_coolest_cities]
    llm = ChatOpenAI(model="gpt-3.5-turbo", temperature=0)
    model_with_tools = llm.bind_tools(tools)

    def call_model(state: State):
        response = model_with_tools.invoke(state["messages"])
        return {"messages": [response]}

    tool_node = ToolNode(tools)
    memory = MemorySaver()
    graph_builder = StateGraph(State)
    graph_builder.add_node("chatbot", call_model)
    graph_builder.add_node("tools", tool_node)
    graph_builder.add_edge(START, "chatbot")
    graph_builder.add_conditional_edges(
        "chatbot",
        tools_condition,
        {"tools": "tools", "__end__": "__end__"},
    )
    graph_builder.add_edge("tools", "chatbot")
    return graph_builder.compile(
        checkpointer=memory,
        interrupt_after=["chatbot"],
    )


def get_last_ai_content(messages: list) -> str:
    """메시지 목록에서 마지막 AI 메시지의 content를 반환한다."""
    for m in reversed(messages):
        if hasattr(m, "content") and m.content and getattr(m, "type", None) == "ai":
            return m.content
    return ""


def try_draw_graph(graph, output_path: str = "chatbot_part4.png") -> None:
    """그래프를 PNG로 저장한다. 의존성 없으면 무시한다."""
    try:
        graph.get_graph().draw_mermaid_png(output_file_path=output_path)
        print(f"그래프 시각화 저장: {output_path}")
    except Exception:
        pass


if __name__ == "__main__":
    graph = create_chatbot_with_human_review_graph()
    try_draw_graph(graph)

    thread_id = "human-review-session"
    config = {"configurable": {"thread_id": thread_id}}

    print("--- Human-in-the-loop: 챗봇 응답 후 중단 → 검토 후 재개 ---\n")

    # 1) 사용자 질문 전달 → chatbot 노드 실행 → interrupt_after 로 중단
    print("1) 사용자 질문 전달 (chatbot 실행 후 자동 중단)")
    for state in graph.stream(
        {"messages": [("user", "서울 날씨 어때?")]},
        config=config,
        stream_mode="values",
    ):
        msg_list = state.get("messages", [])
        if msg_list:
            last = get_last_ai_content(msg_list)
            if last:
                print(f"   [중단 시점] 챗봇 응답: {last[:60]}...")
    print("   (interrupt_after 적용: 여기서 사람이 검토 후 재개 가능)")

    # 2) 중단 지점에서 재개 (같은 config 로 다시 호출)
    print("\n2) 재개 (동일 thread_id 로 invoke)")
    final = graph.invoke(None, config=config)
    last = get_last_ai_content(final.get("messages", []))
    if last:
        print(f"   최종 응답: {last}")
    else:
        print("   (이미 END 상태이거나 추가 응답 없음)")
