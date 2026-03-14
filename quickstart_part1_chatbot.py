"""
LangGraph Quick Start - Part 1: 기본 챗봇

사용 방법:
  1. .env에 OPENAI_API_KEY 설정
  2. 실행 (둘 중 하나):
     - 가상환경 활성화 후: python quickstart_part1_chatbot.py
     - 또는: python3 quickstart_part1_chatbot.py  (macOS 등에서 python 대신 python3 사용)

스트리밍: graph.stream({"messages": [("user", "질문")]})
한 번에 결과: graph.invoke({"messages": [("user", "질문")]})
"""

from typing import Annotated

from dotenv import load_dotenv
from langchain_openai import ChatOpenAI
from typing_extensions import TypedDict

from langgraph.graph import StateGraph, START, END
from langgraph.graph.message import add_messages

load_dotenv()


class State(TypedDict):
    """그래프 상태. add_messages 리듀서로 메시지를 덮어쓰지 않고 추가한다."""

    messages: Annotated[list, add_messages]


def create_chatbot_graph():
    """StateGraph로 기본 챗봇 그래프를 만들고 컴파일해 반환한다."""
    llm = ChatOpenAI(model="gpt-3.5-turbo")

    def chatbot(state: State):
        return {"messages": [llm.invoke(state["messages"])]}

    graph_builder = StateGraph(State)
    graph_builder.add_node("chatbot", chatbot)
    graph_builder.add_edge(START, "chatbot")
    graph_builder.add_edge("chatbot", END)
    return graph_builder.compile()


def stream_graph_updates(graph, user_input: str) -> str:
    """스트리밍으로 그래프를 실행하고, AI 응답 텍스트를 모아 반환한다."""
    messages = []
    for event in graph.stream({"messages": [("user", user_input)]}):
        for value in event.values():
            messages.append(value["messages"][-1].content)
    return "\n".join(messages)


def try_draw_graph(graph, output_path: str = "chatbot.png") -> None:
    """그래프를 PNG로 저장한다. 의존성 없으면 무시한다."""
    try:
        graph.get_graph().draw_mermaid_png(output_file_path=output_path)
        print(f"그래프 시각화 저장: {output_path}")
    except Exception:
        pass


if __name__ == "__main__":
    graph = create_chatbot_graph()
    try_draw_graph(graph)

    question = "한국의 수도는 어디야?"
    print(f"질문: {question}")
    result = stream_graph_updates(graph, question)
    print(f"응답: {result}")

    # 한 번에 결과만 받기:
    # final = graph.invoke({"messages": [("user", question)]})
    # print(final["messages"][-1].content)
