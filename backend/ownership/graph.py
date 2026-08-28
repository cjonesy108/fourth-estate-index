"""Load the curated ownership graph.

v1 source of truth is frontend/data/ownership.json so the Vercel
frontend can render without a database migration. 13F ingest will
write to ownership_* tables and this loader will prefer the DB.
"""
from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path

GRAPH_PATH = (
    Path(__file__).resolve().parents[2] / "frontend" / "data" / "ownership.json"
)


@lru_cache(maxsize=1)
def load_graph() -> dict:
    with GRAPH_PATH.open() as f:
        return json.load(f)


def entity(slug: str) -> dict | None:
    for row in load_graph()["entities"]:
        if row["slug"] == slug:
            return row
    return None


def edges_from(slug: str) -> list[dict]:
    return [e for e in load_graph()["edges"] if e["holder"] == slug]


def edges_to(slug: str) -> list[dict]:
    return [e for e in load_graph()["edges"] if e["asset"] == slug]
