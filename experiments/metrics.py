"""
Experiment metrics collection for LangGraph runs.

Collects latency, token counts, LLM call count, tool call count,
and success/failure via callback and state inspection.
"""

import time
from dataclasses import dataclass
from typing import Any, Optional

from langchain_core.callbacks import BaseCallbackHandler
from langchain_core.outputs import LLMResult


@dataclass
class RunMetrics:
    """Metrics for a single graph invoke/stream run."""

    experiment_id: str = ""
    graph_name: str = ""
    input_summary: str = ""
    latency_seconds: float = 0.0
    input_tokens: int = 0
    output_tokens: int = 0
    llm_calls: int = 0
    tool_calls: int = 0
    success: bool = True
    error_message: Optional[str] = None
    timestamp: str = ""

    def to_dict(self) -> dict[str, Any]:
        """Export as dictionary for JSON serialization."""
        return {
            "experiment_id": self.experiment_id,
            "graph_name": self.graph_name,
            "input_summary": self.input_summary,
            "latency_seconds": round(self.latency_seconds, 4),
            "input_tokens": self.input_tokens,
            "output_tokens": self.output_tokens,
            "llm_calls": self.llm_calls,
            "tool_calls": self.tool_calls,
            "success": self.success,
            "error_message": self.error_message,
            "timestamp": self.timestamp,
        }


class MetricsCallbackHandler(BaseCallbackHandler):
    """Callback handler that counts LLM calls and token usage."""

    def __init__(self) -> None:
        super().__init__()
        self.llm_calls = 0
        self.input_tokens = 0
        self.output_tokens = 0

    def on_llm_start(
        self,
        serialized: dict[str, Any],
        prompts: list[str],
        **kwargs: Any,
    ) -> None:
        """Count each LLM start as one call."""
        self.llm_calls += 1

    def on_llm_end(self, response: LLMResult, **kwargs: Any) -> None:
        """Aggregate token usage from response metadata."""
        for generation_list in response.generations:
            for gen in generation_list:
                if gen.message.response_metadata:
                    usage = gen.message.response_metadata.get("usage", {})
                    self.input_tokens += usage.get("input_tokens", 0)
                    self.output_tokens += usage.get("output_tokens", 0)
                if hasattr(gen.message, "usage_metadata") and gen.message.usage_metadata:
                    um = gen.message.usage_metadata
                    self.input_tokens += getattr(um, "input_tokens", 0) or 0
                    self.output_tokens += getattr(um, "output_tokens", 0) or 0

    def reset(self) -> None:
        """Reset counts for a new run."""
        self.llm_calls = 0
        self.input_tokens = 0
        self.output_tokens = 0


def count_tool_calls_from_messages(messages: list[Any]) -> int:
    """Count tool_calls in a list of messages (AI messages may have tool_calls)."""
    count = 0
    for msg in messages:
        if hasattr(msg, "tool_calls") and msg.tool_calls:
            count += len(msg.tool_calls)
    return count


def extract_llm_calls_from_state(state_values: dict[str, Any]) -> int:
    """Extract llm_calls from graph state if present (e.g. Part 6/7)."""
    return int(state_values.get("llm_calls", 0) or 0)


def measure_invoke(
    graph: Any,
    input_state: dict[str, Any],
    config: Optional[dict[str, Any]] = None,
    callback: Optional[MetricsCallbackHandler] = None,
) -> tuple[dict[str, Any], RunMetrics]:
    """
    Run graph.invoke with timing and optional callback.
    Returns (final_state, metrics). State may be partial on exception.
    """
    config = config or {}
    metrics = RunMetrics()
    start = time.perf_counter()
    run_config = dict(config)
    if callback:
        run_config["callbacks"] = [callback]
    try:
        result = graph.invoke(input_state, config=run_config)
    except Exception as e:
        metrics.latency_seconds = time.perf_counter() - start
        metrics.success = False
        metrics.error_message = str(e)
        return {}, metrics
    metrics.latency_seconds = time.perf_counter() - start
    metrics.success = True
    if callback:
        metrics.llm_calls = callback.llm_calls
        metrics.input_tokens = callback.input_tokens
        metrics.output_tokens = callback.output_tokens
    metrics.llm_calls = metrics.llm_calls or extract_llm_calls_from_state(result)
    messages = result.get("messages", [])
    if isinstance(messages, list):
        metrics.tool_calls = count_tool_calls_from_messages(messages)
    return result, metrics
