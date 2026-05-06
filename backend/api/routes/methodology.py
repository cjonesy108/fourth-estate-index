import json
from pathlib import Path

from fastapi import APIRouter, HTTPException

router = APIRouter()

METHODOLOGY_DIR = Path(__file__).parent.parent.parent.parent / "methodology"


@router.get("")
async def get_methodology():
    """Current methodology version — full rubric, weights, and prompt inventory."""
    rubric_path = METHODOLOGY_DIR / "rubric.json"
    if not rubric_path.exists():
        raise HTTPException(status_code=503, detail="Methodology not yet published")
    return json.loads(rubric_path.read_text())


@router.get("/versions")
async def get_methodology_versions():
    # TODO: wire to methodology_versions table
    return []
