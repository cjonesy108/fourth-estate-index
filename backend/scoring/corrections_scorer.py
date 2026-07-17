"""
Corrections scorer — Pillar 4: Be Accountable and Transparent.

Three dimensions:
  corrections_frequency: corrections per 100 articles
  corrections_velocity:  average days to correction (not yet implemented — requires original pub date)
  corrections_severity:  weighted by type (factual > attribution > omission > clarification)

Scoring philosophy:
  - Zero corrections is not automatically a perfect score.
    It may mean no errors, or it may mean errors went uncorrected.
    We score what we can observe: when corrections exist, how severe and how fast?
  - Frequency is scored relative to corpus size.
  - Type weights: factual errors are the most serious SPJ violation.
"""

from typing import Optional

# Severity weights by correction type
SEVERITY_WEIGHTS = {
    "factual":       1.0,   # stated something false
    "attribution":   0.8,   # wrong person credited
    "omission":      0.6,   # left out important information
    "clarification": 0.3,   # ambiguous but not false
}

# Frequency thresholds — corrections per 100 articles
# Below 1.0/100: minimal impact on score
# Above 5.0/100: significant pattern
FREQUENCY_PENALTY_SCALE = [
    (0.0, 1.0),    # 0 corrections per 100 articles: no penalty
    (1.0, 0.95),   # 1 per 100: very minor
    (2.0, 0.90),
    (3.0, 0.85),
    (5.0, 0.78),
    (8.0, 0.70),
    (10.0, 0.60),
]


def score_corrections(
    corrections: list[dict],
    corpus_size: int,
) -> dict:
    """
    Score the corrections record for Pillar 4.

    corrections: list of dicts with keys: correction_type, days_to_correction
    corpus_size: total articles in corpus
    """
    if corpus_size == 0:
        return {
            "corrections_frequency": None,
            "corrections_severity": None,
            "pillar_4_score": None,
        }

    count = len(corrections)
    per_100 = (count / corpus_size) * 100

    # Frequency score
    freq_score = _interpolate_penalty(per_100, FREQUENCY_PENALTY_SCALE)

    # Severity score — weighted average of correction types
    if corrections:
        severity_scores = []
        for c in corrections:
            ctype = (c.get("correction_type") or "clarification").lower()
            weight = SEVERITY_WEIGHTS.get(ctype, 0.3)
            severity_scores.append(weight)

        avg_severity = sum(severity_scores) / len(severity_scores)
        # Higher severity = lower score
        severity_score = round(1.0 - (avg_severity * 0.3), 2)
    else:
        severity_score = 1.0

    # Pillar 4 composite (frequency weighted more heavily)
    pillar_4 = round((freq_score * 0.6) + (severity_score * 0.4), 2)

    return {
        "corrections_frequency": round(freq_score, 2),
        "corrections_severity": round(severity_score, 2),
        "corrections_count": count,
        "corrections_per_100": round(per_100, 2),
        "pillar_4_score": pillar_4,
    }


def _interpolate_penalty(value: float, scale: list[tuple]) -> float:
    """Linear interpolation between threshold points."""
    for i, (threshold, score) in enumerate(scale):
        if value <= threshold:
            if i == 0:
                return score
            prev_threshold, prev_score = scale[i - 1]
            ratio = (value - prev_threshold) / (threshold - prev_threshold)
            return round(prev_score + ratio * (score - prev_score), 3)
    return scale[-1][1]
