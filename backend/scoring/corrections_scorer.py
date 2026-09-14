"""
Corrections scorer — Pillar 4: Be Accountable and Transparent.

Zero corrections is not a perfect score when we never looked.
If ingested=False, every P4 dimension is None (insufficient), not 1.0.
"""

from typing import Optional

SEVERITY_WEIGHTS = {
    "factual": 1.0,
    "attribution": 0.8,
    "omission": 0.6,
    "clarification": 0.3,
}

FREQUENCY_PENALTY_SCALE = [
    (0.0, 0.85),  # searched, found none — not a 1.0; absence is unverified quality
    (1.0, 0.80),
    (2.0, 0.74),
    (3.0, 0.68),
    (5.0, 0.60),
    (8.0, 0.50),
    (10.0, 0.40),
]


def score_corrections(
    corrections: list[dict],
    corpus_size: int,
    ingested: bool = False,
) -> dict:
    if not ingested:
        return {
            "corrections_frequency": None,
            "corrections_severity": None,
            "corrections_velocity": None,
            "corrections_count": 0,
            "corrections_per_100": None,
            "pillar_4_score": None,
            "ingested": False,
        }

    if corpus_size == 0:
        return {
            "corrections_frequency": None,
            "corrections_severity": None,
            "corrections_velocity": None,
            "pillar_4_score": None,
            "ingested": True,
        }

    count = len(corrections)
    per_100 = (count / corpus_size) * 100
    freq_score = _interpolate_penalty(per_100, FREQUENCY_PENALTY_SCALE)

    if corrections:
        severity_scores = []
        delays = []
        for c in corrections:
            ctype = (c.get("correction_type") or "clarification").lower()
            severity_scores.append(SEVERITY_WEIGHTS.get(ctype, 0.3))
            if c.get("days_to_correction") is not None:
                delays.append(c["days_to_correction"])
        avg_severity = sum(severity_scores) / len(severity_scores)
        severity_score = round(1.0 - (avg_severity * 0.3), 2)
        if delays:
            avg_days = sum(delays) / len(delays)
            velocity_score = round(max(0.4, 1.0 - (avg_days / 60.0) * 0.4), 2)
        else:
            velocity_score = None
    else:
        severity_score = None
        velocity_score = None

    parts = [s for s in (freq_score, severity_score, velocity_score) if s is not None]
    pillar_4 = round(sum(parts) / len(parts), 2) if parts else None

    return {
        "corrections_frequency": round(freq_score, 2),
        "corrections_severity": severity_score,
        "corrections_velocity": velocity_score,
        "corrections_count": count,
        "corrections_per_100": round(per_100, 2),
        "pillar_4_score": pillar_4,
        "ingested": True,
    }


def _interpolate_penalty(value: float, scale: list[tuple]) -> float:
    for i, (threshold, score) in enumerate(scale):
        if value <= threshold:
            if i == 0:
                return score
            prev_threshold, prev_score = scale[i - 1]
            ratio = (value - prev_threshold) / (threshold - prev_threshold)
            return round(prev_score + ratio * (score - prev_score), 3)
    return scale[-1][1]
