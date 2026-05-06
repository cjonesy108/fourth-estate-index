"""
Pillar scorer — aggregates dimension scores into pillar scores.

Each dimension has a minimum corpus threshold. Dimensions below threshold
are marked None (insufficient data), not zero. A zero score means the
journalist failed the dimension. None means we don't have enough data to say.

The composite score is not calculated until all four pillars have at
least one scored dimension. Partial data produces a partial profile,
not a score.
"""

import json
import logging
from pathlib import Path
from typing import Optional

logger = logging.getLogger(__name__)

RUBRIC_PATH = Path(__file__).parent.parent.parent / "methodology" / "rubric.json"


def load_rubric() -> dict:
    return json.loads(RUBRIC_PATH.read_text())


def score_pillar(
    pillar_key: str,
    dimension_scores: dict[str, Optional[float]],
    rubric: dict,
) -> Optional[float]:
    """
    Weight and average the scored dimensions for one pillar.
    Returns None if no dimensions were scored.
    """
    pillar_def = rubric["pillars"][pillar_key]["dimensions"]
    total_weight = 0.0
    weighted_sum = 0.0
    any_scored = False

    for dim_name, dim_def in pillar_def.items():
        score = dimension_scores.get(dim_name)
        if score is None:
            continue
        weight = dim_def["weight"]
        weighted_sum += score * weight
        total_weight += weight
        any_scored = True

    if not any_scored or total_weight == 0:
        return None

    return round(weighted_sum / total_weight, 2)


def score_composite(
    pillar_scores: dict[str, Optional[float]],
    rubric: dict,
) -> Optional[float]:
    """
    Weight and average pillar scores into composite.
    Returns None if any pillar is unscored.
    """
    weights = rubric["composite_weights"]
    total = 0.0

    for pillar_key, weight in weights.items():
        score = pillar_scores.get(pillar_key)
        if score is None:
            logger.info(f"Composite score deferred — {pillar_key} not yet scored")
            return None
        total += score * weight

    return round(total, 2)


def build_pillar_scores(
    dimension_results: dict[str, Optional[float]],
) -> dict:
    rubric = load_rubric()

    pillar_scores = {}
    for pillar_key in ["pillar_1", "pillar_2", "pillar_3", "pillar_4"]:
        pillar_scores[pillar_key] = score_pillar(pillar_key, dimension_results, rubric)

    composite = score_composite(pillar_scores, rubric)

    return {
        "pillar_1_score": pillar_scores.get("pillar_1"),
        "pillar_2_score": pillar_scores.get("pillar_2"),
        "pillar_3_score": pillar_scores.get("pillar_3"),
        "pillar_4_score": pillar_scores.get("pillar_4"),
        "composite_score": composite,
    }
