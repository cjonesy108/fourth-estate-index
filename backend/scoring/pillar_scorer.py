"""
Pillar scorer — aggregates dimension scores into pillar scores.

Missing dimensions are None, not zero.
A pillar is only published when scored dimensions cover more than half
of that pillar's rubric weight. Otherwise the pillar is insufficient.
That stops a single easy dimension from becoming a 100.
"""

import json
import logging
from pathlib import Path
from typing import Optional

logger = logging.getLogger(__name__)

RUBRIC_PATH = Path(__file__).parent.parent.parent / "methodology" / "rubric.json"
MIN_PILLAR_COVERAGE = 0.51


def load_rubric() -> dict:
    return json.loads(RUBRIC_PATH.read_text())


def score_pillar(
    pillar_key: str,
    dimension_scores: dict[str, Optional[float]],
    rubric: dict,
) -> tuple[Optional[float], dict]:
    pillar_def = rubric["pillars"][pillar_key]["dimensions"]
    full_weight = sum(d["weight"] for d in pillar_def.values())
    total_weight = 0.0
    weighted_sum = 0.0
    coverage = {}

    for dim_name, dim_def in pillar_def.items():
        score = dimension_scores.get(dim_name)
        coverage[dim_name] = score is not None
        if score is None:
            continue
        weight = dim_def["weight"]
        weighted_sum += score * weight
        total_weight += weight

    ratio = (total_weight / full_weight) if full_weight else 0.0
    if total_weight == 0 or ratio < MIN_PILLAR_COVERAGE:
        return None, coverage
    return round(weighted_sum / total_weight, 2), coverage


def score_composite(
    pillar_scores: dict[str, Optional[float]],
    rubric: dict,
) -> Optional[float]:
    weights = rubric["composite_weights"]
    total = 0.0
    for pillar_key, weight in weights.items():
        score = pillar_scores.get(pillar_key)
        if score is None:
            logger.info("Composite deferred — %s not yet scored", pillar_key)
            return None
        total += score * weight
    return round(total, 2)


def build_pillar_scores(
    dimension_results: dict[str, Optional[float]],
) -> dict:
    rubric = load_rubric()
    pillar_scores = {}
    dimensions_scored = {}
    for pillar_key in ["pillar_1", "pillar_2", "pillar_3", "pillar_4"]:
        score, coverage = score_pillar(pillar_key, dimension_results, rubric)
        pillar_scores[pillar_key] = score
        dimensions_scored.update(coverage)

    composite = score_composite(pillar_scores, rubric)
    return {
        "pillar_1_score": pillar_scores.get("pillar_1"),
        "pillar_2_score": pillar_scores.get("pillar_2"),
        "pillar_3_score": pillar_scores.get("pillar_3"),
        "pillar_4_score": pillar_scores.get("pillar_4"),
        "composite_score": composite,
        "dimensions_scored": dimensions_scored,
        "rubric_status": "complete" if composite is not None else "partial",
    }
