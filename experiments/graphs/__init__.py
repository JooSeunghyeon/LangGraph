"""
Graph registry for experiments.

Each builder accepts model name and returns a compiled LangGraph.
"""

from typing import Any, Callable

from experiments.graphs.builders import (
    build_part1,
    build_part2,
    build_part3,
    build_part4,
    build_part5,
    build_part6_part7,
)

GRAPH_REGISTRY: dict[str, Callable[[str], Any]] = {
    "part1": build_part1,
    "part2": build_part2,
    "part3": build_part3,
    "part4": build_part4,
    "part5": build_part5,
    "part6_part7": build_part6_part7,
}


def get_graph(graph_name: str, model: str = "gpt-3.5-turbo") -> Any:
    """Return a compiled graph for the given name and model."""
    if graph_name not in GRAPH_REGISTRY:
        raise ValueError(f"Unknown graph: {graph_name}. Choose from {list(GRAPH_REGISTRY.keys())}")
    return GRAPH_REGISTRY[graph_name](model)
