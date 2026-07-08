from __future__ import annotations

import json
from pathlib import Path

from .schema import CharacterGraph


def save_graph(graph: CharacterGraph, path: Path | str) -> None:
    destination = Path(path)
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_text(
        json.dumps(graph.to_dict(), indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )


def load_graph(path: Path | str) -> CharacterGraph | None:
    source = Path(path)
    if not source.exists():
        return None
    payload = json.loads(source.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError(f"{source} must contain a JSON object.")
    return CharacterGraph.from_dict(payload)
