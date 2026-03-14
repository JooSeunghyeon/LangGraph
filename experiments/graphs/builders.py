"""
Build Part 1–7 graphs with configurable model name for experiments.

Logic is aligned with quickstart_part*.py; model is passed into ChatOpenAI.
"""

import operator
from typing import Annotated, Any

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
# Shared tools (Part 2, 3, 4)
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
# Part 1: Basic chatbot
# ---------------------------------------------------------------------------

class StatePart1(TypedDict):
    messages: Annotated[list, add_messages]


def build_part1(model: str = "gpt-3.5-turbo") -> Any:
    """Part 1: basic chatbot, no checkpointer."""
    llm = ChatOpenAI(model=model)

    def chatbot(state: StatePart1) -> dict:
        return {"messages": [llm.invoke(state["messages"])]}

    builder = StateGraph(StatePart1)
    builder.add_node("chatbot", chatbot)
    builder.add_edge(START, "chatbot")
    builder.add_edge("chatbot", END)
    return builder.compile()


# ---------------------------------------------------------------------------
# Part 2: Chatbot with tools
# ---------------------------------------------------------------------------

class StatePart2(TypedDict):
    messages: Annotated[list, add_messages]


def build_part2(model: str = "gpt-3.5-turbo") -> Any:
    """Part 2: chatbot with tools, no checkpointer."""
    tools = [get_weather, get_coolest_cities]
    llm = ChatOpenAI(model=model, temperature=0)
    model_with_tools = llm.bind_tools(tools)

    def call_model(state: StatePart2) -> dict:
        response = model_with_tools.invoke(state["messages"])
        return {"messages": [response]}

    tool_node = ToolNode(tools)
    builder = StateGraph(StatePart2)
    builder.add_node("chatbot", call_model)
    builder.add_node("tools", tool_node)
    builder.add_edge(START, "chatbot")
    builder.add_conditional_edges(
        "chatbot",
        tools_condition,
        {"tools": "tools", "__end__": "__end__"},
    )
    builder.add_edge("tools", "chatbot")
    return builder.compile()


# ---------------------------------------------------------------------------
# Part 3: Chatbot with memory
# ---------------------------------------------------------------------------

def build_part3(model: str = "gpt-3.5-turbo") -> Any:
    """Part 3: tools + MemorySaver checkpointer."""
    tools = [get_weather, get_coolest_cities]
    llm = ChatOpenAI(model=model, temperature=0)
    model_with_tools = llm.bind_tools(tools)

    def call_model(state: StatePart2) -> dict:
        response = model_with_tools.invoke(state["messages"])
        return {"messages": [response]}

    tool_node = ToolNode(tools)
    memory = MemorySaver()
    builder = StateGraph(StatePart2)
    builder.add_node("chatbot", call_model)
    builder.add_node("tools", tool_node)
    builder.add_edge(START, "chatbot")
    builder.add_conditional_edges(
        "chatbot",
        tools_condition,
        {"tools": "tools", "__end__": "__end__"},
    )
    builder.add_edge("tools", "chatbot")
    return builder.compile(checkpointer=memory)


# ---------------------------------------------------------------------------
# Part 4: Human-in-the-loop
# ---------------------------------------------------------------------------

def build_part4(model: str = "gpt-3.5-turbo") -> Any:
    """Part 4: tools + checkpointer + interrupt_after chatbot."""
    tools = [get_weather, get_coolest_cities]
    llm = ChatOpenAI(model=model, temperature=0)
    model_with_tools = llm.bind_tools(tools)

    def call_model(state: StatePart2) -> dict:
        response = model_with_tools.invoke(state["messages"])
        return {"messages": [response]}

    tool_node = ToolNode(tools)
    memory = MemorySaver()
    builder = StateGraph(StatePart2)
    builder.add_node("chatbot", call_model)
    builder.add_node("tools", tool_node)
    builder.add_edge(START, "chatbot")
    builder.add_conditional_edges(
        "chatbot",
        tools_condition,
        {"tools": "tools", "__end__": "__end__"},
    )
    builder.add_edge("tools", "chatbot")
    return builder.compile(
        checkpointer=memory,
        interrupt_after=["chatbot"],
    )


# ---------------------------------------------------------------------------
# Part 5: Manual state update (checkpointer, no tools)
# ---------------------------------------------------------------------------

def build_part5(model: str = "gpt-3.5-turbo") -> Any:
    """Part 5: basic chatbot with checkpointer for update_state/get_state."""
    llm = ChatOpenAI(model=model)

    def chatbot(state: StatePart1) -> dict:
        return {"messages": [llm.invoke(state["messages"])]}

    memory = MemorySaver()
    builder = StateGraph(StatePart1)
    builder.add_node("chatbot", chatbot)
    builder.add_edge(START, "chatbot")
    builder.add_edge("chatbot", END)
    return builder.compile(checkpointer=memory)


# ---------------------------------------------------------------------------
# Part 6 & 7: Custom state (llm_calls) + time travel
# ---------------------------------------------------------------------------

class StatePart67(TypedDict):
    messages: Annotated[list, add_messages]
    llm_calls: Annotated[int, operator.add]


def build_part6_part7(model: str = "gpt-3.5-turbo") -> Any:
    """Part 6/7: custom state with llm_calls reducer, checkpointer."""
    llm = ChatOpenAI(model=model)

    def chatbot(state: StatePart67) -> dict:
        response = llm.invoke(state["messages"])
        return {"messages": [response], "llm_calls": 1}

    memory = MemorySaver()
    builder = StateGraph(StatePart67)
    builder.add_node("chatbot", chatbot)
    builder.add_edge(START, "chatbot")
    builder.add_edge("chatbot", END)
    return builder.compile(checkpointer=memory)
