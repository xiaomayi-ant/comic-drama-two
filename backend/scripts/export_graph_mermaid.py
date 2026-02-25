"""
Export current workflow topology to Mermaid text.

This script supports two modes:
1) Preferred: runtime render via LangGraph's built-in `draw_mermaid()`
2) Fallback: static AST parse of `src/agent/graph.py` (no dependencies needed)

Usage:
    python3 scripts/export_graph_mermaid.py
    python3 scripts/export_graph_mermaid.py --out outputs/graph.mmd
"""

from __future__ import annotations

import argparse
import ast
import os
import sys
import logging
from typing import Any

logging.basicConfig(level=logging.INFO, format="%(message)s")
logger = logging.getLogger(__name__)


def _project_root() -> str:
    # scripts/.. -> project root
    return os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))


def _ensure_import_path() -> None:
    root = _project_root()
    if root not in sys.path:
        sys.path.insert(0, root)


def _manual_mermaid() -> str:
    """
    Fallback Mermaid if LangGraph rendering is unavailable.
    Keep it aligned with src/agent/graph.py topology.
    """
    return """flowchart TD
  %% entry
  intent_analysis[intent_analysis]

  %% routing
  breakdown[breakdown]
  simple_chat[simple_chat]
  analysis_output[analysis_output]
  analysis_report[analysis_report]

  reverse_engineer[reverse_engineer]
  move_plan[move_plan]
  writing[writing]
  verify[verify]
  proofread[proofread]

  END(((END)))

  %% copy flow (prior-driven imitation)
  intent_analysis -->|copy_flow| reverse_engineer
  intent_analysis -->|analysis_flow| breakdown
  intent_analysis -->|chat_flow| simple_chat

  breakdown -->|to_analysis_report| analysis_report
  breakdown -->|to_analysis_output| analysis_output
  analysis_report --> reverse_engineer

  %% main imitation chain
  reverse_engineer --> move_plan --> writing --> verify
  verify -->|proceed| proofread
  verify -->|revise| writing

  proofread -->|continue| writing
  proofread -->|end| END

  simple_chat --> END
  analysis_output --> END
"""


def export_mermaid() -> tuple[str, dict[str, Any]]:
    _ensure_import_path()
    # Preferred: LangGraph runtime rendering (if dependencies installed).
    try:
        from src.agent.graph import create_agent_graph  # noqa: WPS433 (runtime import)

        graph = create_agent_graph(with_memory=False)
        g = graph.get_graph()
        mermaid = g.draw_mermaid()  # type: ignore[attr-defined]
        return mermaid, {"renderer": "langgraph_runtime"}
    except Exception as e:
        # Fallback: static parse src/agent/graph.py so user can always see topology.
        try:
            mermaid = _mermaid_from_ast()
            return mermaid, {"renderer": "ast_fallback", "reason": str(e)}
        except Exception as e2:
            return _manual_mermaid(), {
                "renderer": "manual_fallback",
                "reason": str(e),
                "error": str(e2),
            }


def _as_node_ref(expr: ast.AST) -> str | None:
    if isinstance(expr, ast.Constant) and isinstance(expr.value, str):
        return expr.value
    if isinstance(expr, ast.Name):
        return expr.id
    return None


def _iter_calls(tree: ast.AST) -> list[ast.Call]:
    calls: list[ast.Call] = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Call):
            calls.append(node)
    return calls


def _get_attr_name(call: ast.Call) -> str | None:
    func = call.func
    if isinstance(func, ast.Attribute):
        return func.attr
    return None


def _mermaid_from_ast() -> str:
    project_root = _project_root()
    graph_py = os.path.join(project_root, "src", "agent", "graph.py")
    with open(graph_py, "r", encoding="utf-8") as f:
        source = f.read()

    tree = ast.parse(source, filename=graph_py)

    nodes: set[str] = set()
    edges: list[tuple[str, str, str | None]] = []
    entry: str | None = None

    for call in _iter_calls(tree):
        attr = _get_attr_name(call)
        if not attr:
            continue

        if attr == "add_node" and len(call.args) >= 2:
            name = _as_node_ref(call.args[0])
            if name and name not in {"START", "END"}:
                nodes.add(name)

        elif attr == "set_entry_point" and len(call.args) >= 1:
            entry = _as_node_ref(call.args[0]) or entry

        elif attr == "add_edge" and len(call.args) >= 2:
            src = _as_node_ref(call.args[0])
            dst = _as_node_ref(call.args[1])
            if src and dst:
                nodes.add(src) if src not in {"START", "END"} else None
                nodes.add(dst) if dst not in {"START", "END"} else None
                edges.append((src, dst, None))

        elif attr == "add_conditional_edges" and len(call.args) >= 3:
            src = _as_node_ref(call.args[0])
            mapping = call.args[2]
            if not src or not isinstance(mapping, ast.Dict):
                continue
            nodes.add(src) if src not in {"START", "END"} else None
            # NOTE: keep compatible with older Python where zip(strict=...) is unsupported.
            for k, v in zip(mapping.keys, mapping.values):
                if k is None:
                    continue
                label = _as_node_ref(k) or ast.unparse(k)
                dst = _as_node_ref(v) or (ast.unparse(v) if v is not None else None)
                if dst:
                    nodes.add(dst) if dst not in {"START", "END"} else None
                    edges.append((src, dst, label))

    # Normalize special nodes
    nodes.discard("END")
    nodes.discard("START")

    lines: list[str] = ["flowchart TD"]
    lines.append("  START(((START)))")
    lines.append("  END(((END)))")
    for n in sorted(nodes):
        lines.append(f"  {n}[{n}]")
    if entry:
        lines.append(f"  START --> {entry}")

    for src, dst, label in edges:
        s = src
        d = dst
        if s == "END":
            s = "END"
        if d == "END":
            d = "END"
        if s == "START":
            s = "START"
        if d == "START":
            d = "START"
        if label:
            lines.append(f"  {s} -->|{label}| {d}")
        else:
            lines.append(f"  {s} --> {d}")

    return "\n".join(lines) + "\n"


def main() -> int:
    parser = argparse.ArgumentParser(description="Export LangGraph to Mermaid text")
    parser.add_argument(
        "--out",
        default="",
        help="Write Mermaid to file (e.g. outputs/graph.mmd). If omitted, prints to stdout.",
    )
    args = parser.parse_args()

    mermaid, meta = export_mermaid()

    header = f"%% generated_by: scripts/export_graph_mermaid.py\n%% meta: {meta}\n"
    content = header + mermaid

    if args.out:
        out_path = args.out
        if not os.path.isabs(out_path):
            out_path = os.path.join(_project_root(), out_path)
        os.makedirs(os.path.dirname(out_path), exist_ok=True)
        with open(out_path, "w", encoding="utf-8") as f:
            f.write(content)
        logger.info(out_path)
    else:
        logger.info(content)

    return 0


if __name__ == "__main__":
    raise SystemExit(main())


