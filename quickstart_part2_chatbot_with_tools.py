"""
LangGraph Quick Start - Part 2: 도구(Tool)로 챗봇 강화

도구를 바인딩한 LLM이 필요 시 도구를 호출하고, ToolNode가 실행한 뒤
다시 LLM으로 돌아가는 ReAct 스타일 흐름이다.

사용 방법:
  1. .env에 OPENAI_API_KEY 설정
  2. 가상환경 활성화 후: python quickstart_part2_chatbot_with_tools.py

실행 흐름: START -> chatbot -> (도구 호출 있으면) tools -> chatbot -> ... -> END
"""

from typing import Annotated

from dotenv import load_dotenv
from langchain_core.tools import tool
from langchain_openai import ChatOpenAI
from typing_extensions import TypedDict

from langgraph.graph import StateGraph, START, END
from langgraph.graph.message import add_messages
from langgraph.prebuilt import ToolNode, tools_condition

load_dotenv()


# ---------------------------------------------------------------------------
# 도구 정의 (외부 API 없이 동작하는 예시)
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
# State 및 그래프
# ---------------------------------------------------------------------------

class State(TypedDict):
    """그래프 상태. add_messages 리듀서로 메시지를 덮어쓰지 않고 추가한다."""

    messages: Annotated[list, add_messages]


def create_chatbot_with_tools_graph():
    """도구를 사용하는 챗봇 그래프를 만들고 컴파일해 반환한다."""
    tools = [get_weather, get_coolest_cities]
    llm = ChatOpenAI(model="gpt-3.5-turbo", temperature=0)
    model_with_tools = llm.bind_tools(tools)

    def call_model(state: State):
        response = model_with_tools.invoke(state["messages"])
        return {"messages": [response]}

    tool_node = ToolNode(tools)
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
    return graph_builder.compile()


def stream_graph_updates(graph, user_input: str) -> str:
    """스트리밍으로 그래프를 실행하고, 마지막 AI 응답 텍스트를 반환한다."""
    last_content = ""
    for state in graph.stream({"messages": [("user", user_input)]}, stream_mode="values"):
        msg_list = state.get("messages", [])
        if msg_list and hasattr(msg_list[-1], "content") and msg_list[-1].content:
            last_content = msg_list[-1].content
    return last_content


def try_draw_graph(graph, output_path: str = "chatbot_part2.png") -> None:
    """그래프를 PNG로 저장한다. 의존성 없으면 무시한다."""
    try:
        graph.get_graph().draw_mermaid_png(output_file_path=output_path)
        print(f"그래프 시각화 저장: {output_path}")
    except Exception:
        pass


if __name__ == "__main__":
    graph = create_chatbot_with_tools_graph()
    try_draw_graph(graph)

    question = "서울 날씨 어때?"
    print(f"질문: {question}")
    result = stream_graph_updates(graph, question)
    print(f"응답: {result}")
