"""Artifacts persistence utilities (local filesystem).

We keep this intentionally simple for MVP:
- Write a per-run JSON artifact (single file) under outputs/
- Append a JSONL record for easy later indexing
"""

from __future__ import annotations

import json
import os
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, Optional


@dataclass(frozen=True)
class ArtifactPaths:
    run_json: str
    runs_jsonl: str


def _utc_ts() -> str:
    return datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")


def ensure_outputs_dir(project_root: str) -> str:
    outputs_dir = os.path.join(project_root, "outputs")
    os.makedirs(outputs_dir, exist_ok=True)
    return outputs_dir


def persist_run_artifacts(
    project_root: str,
    thread_id: str,
    payload: dict[str, Any],
    *,
    filename_prefix: str = "run",
) -> ArtifactPaths:
    outputs_dir = ensure_outputs_dir(project_root)
    ts = _utc_ts()
    safe_thread = "".join(c for c in thread_id if c.isalnum() or c in ("-", "_"))[:64]
    base = f"{filename_prefix}_{ts}_{safe_thread or 'default'}"

    run_json_path = os.path.join(outputs_dir, f"{base}.json")
    runs_jsonl_path = os.path.join(outputs_dir, "runs.jsonl")

    # Write single JSON file (pretty for inspection)
    with open(run_json_path, "w", encoding="utf-8") as f:
        json.dump(payload, f, ensure_ascii=False, indent=2)

    # Append JSONL record (one-line)
    record = {
        "ts_utc": ts,
        "thread_id": thread_id,
        "artifact_json": os.path.basename(run_json_path),
        "payload": payload,
    }
    with open(runs_jsonl_path, "a", encoding="utf-8") as f:
        f.write(json.dumps(record, ensure_ascii=False) + "\n")

    return ArtifactPaths(run_json=run_json_path, runs_jsonl=runs_jsonl_path)


