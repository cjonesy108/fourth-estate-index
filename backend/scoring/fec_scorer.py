"""
Financial conflicts — Pillar 3.

Scores disclosed federal contributions on file, not guessed independence.
If FEC was not queried, return None. Do not mint a 1.0 from silence.
"""

from typing import Optional


def score_financial_conflicts(
    records: list[dict],
    looked_up: bool,
) -> dict:
    if not looked_up:
        return {
            "financial_conflicts": None,
            "contribution_count": 0,
            "contribution_total": 0.0,
            "looked_up": False,
        }

    count = len(records)
    total = float(sum(abs(float(r.get("amount") or 0)) for r in records))

    if count == 0:
        score = 0.92
    elif total < 200:
        score = 0.80
    elif total < 1000:
        score = 0.70
    elif total < 2800:
        score = 0.60
    else:
        score = 0.50

    return {
        "financial_conflicts": score,
        "contribution_count": count,
        "contribution_total": round(total, 2),
        "looked_up": True,
    }
