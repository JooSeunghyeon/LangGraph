"""
Run LangGraph experiments and record metrics to JSONL.

Usage:
  python experiments/run_experiments.py --graph part1 --model gpt-3.5-turbo
  python experiments/run_experiments.py --config experiments/configs/baseline.yaml
  python experiments/run_experiments.py --graph part2 --repeat 2 --output experiments/results/out.jsonl
"""

import argparse
import json
import random
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

# Ensure project root is on path when running as script
_PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(_PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(_PROJECT_ROOT))

from experiments.metrics import MetricsCallbackHandler, RunMetrics, measure_invoke
from experiments.graphs import get_graph, GRAPH_REGISTRY

# Default prompts for reproducibility
DEFAULT_PROMPTS = [
    "한국의 수도는 어디야?",
    "서울 날씨 어때?",
    "가장 시원한 도시 알려줘",
    "안녕하세요.",
    "1+1은?",
]


def build_input_state(prompt: str, graph_name: str) -> dict:
    """Build initial state for invoke. Part 6/7 need llm_calls."""
    state: dict = {"messages": [("user", prompt)]}
    if graph_name == "part6_part7":
        state["llm_calls"] = 0
    return state


def get_config(graph_name: str, thread_id: str) -> dict:
    """Config with thread_id for graphs that use checkpointer."""
    return {"configurable": {"thread_id": thread_id}}


def run_single(
    graph_name: str,
    model: str,
    prompt: str,
    run_id: str,
    seed: Optional[int] = None,
) -> RunMetrics:
    """Run one invoke and return metrics."""
    graph = get_graph(graph_name, model=model)
    callback = MetricsCallbackHandler()
    input_state = build_input_state(prompt, graph_name)
    thread_id = f"exp-{run_id}"
    config = get_config(graph_name, thread_id)
    if seed is not None:
        random.seed(seed)
    result, metrics = measure_invoke(graph, input_state, config=config, callback=callback)
    metrics.experiment_id = run_id
    metrics.graph_name = graph_name
    metrics.input_summary = prompt[:80] + ("..." if len(prompt) > 80 else "")
    metrics.timestamp = datetime.now(timezone.utc).isoformat()
    return metrics


def load_config_yaml(path: Path) -> dict:
    """Load YAML config; may contain graph, model, graphs[], models[], repeat, seed."""
    try:
        import yaml
    except ImportError:
        return {}
    with open(path, encoding="utf-8") as f:
        data = yaml.safe_load(f) or {}
    return data


def main() -> None:
    parser = argparse.ArgumentParser(description="Run LangGraph experiments and record metrics")
    parser.add_argument("--config", type=str, default=None, help="Path to YAML config (sets graph, model, repeat, seed)")
    parser.add_argument("--graph", type=str, default="part1", choices=list(GRAPH_REGISTRY.keys()), help="Graph to run")
    parser.add_argument("--model", type=str, default="gpt-3.5-turbo", help="OpenAI model name")
    parser.add_argument("--prompts", type=str, nargs="*", default=None, help="Prompt list; default uses built-in list")
    parser.add_argument("--repeat", type=int, default=1, help="Repeat each prompt this many times")
    parser.add_argument("--seed", type=int, default=None, help="Random seed for reproducibility")
    parser.add_argument("--output", type=str, default="experiments/results/metrics.jsonl", help="Output JSONL path")
    args = parser.parse_args()
    if args.config:
        cfg = load_config_yaml(Path(args.config))
        if cfg.get("graph"):
            args.graph = cfg["graph"]
        if cfg.get("model"):
            args.model = cfg["model"]
        if cfg.get("repeat") is not None:
            args.repeat = cfg["repeat"]
        if cfg.get("seed") is not None:
            args.seed = cfg["seed"]
    prompts = args.prompts if args.prompts else DEFAULT_PROMPTS
    graphs = [args.graph]
    models = [args.model]
    if args.config:
        cfg = load_config_yaml(Path(args.config))
        if cfg.get("graphs"):
            graphs = [g for g in cfg["graphs"] if g in GRAPH_REGISTRY]
        if cfg.get("models"):
            models = cfg["models"]
    out_path = Path(args.output)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    run_index = 0
    with open(out_path, "w", encoding="utf-8") as f:
        for graph_name in graphs:
            for model_name in models:
                for prompt in prompts:
                    for r in range(args.repeat):
                        run_id = f"{graph_name}_{model_name}_{run_index}"
                        metrics = run_single(graph_name, model_name, prompt, run_id, seed=args.seed)
                        f.write(json.dumps(metrics.to_dict(), ensure_ascii=False) + "\n")
                        run_index += 1
    print(f"Wrote {run_index} runs to {out_path}")


if __name__ == "__main__":
    main()
