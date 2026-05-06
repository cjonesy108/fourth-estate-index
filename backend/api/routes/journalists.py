import os
from typing import Optional
from fastapi import APIRouter, HTTPException, Query
from backend.database.queries import list_journalists, get_journalist_profile, get_conn

router = APIRouter()


def _dsn():
    return os.environ["DATABASE_URL"].replace("postgresql+asyncpg://", "postgresql://")


@router.get("")
async def list_journalists_route(
    scored_only: bool = Query(False),
):
    conn = await get_conn(_dsn())
    try:
        journalists = await list_journalists(conn)
        if scored_only:
            journalists = [j for j in journalists if j.get("composite_score") is not None]
        # Convert UUIDs and decimals to JSON-serializable types
        return [_serialize(j) for j in journalists]
    finally:
        await conn.close()


@router.get("/{slug}")
async def get_journalist_route(slug: str):
    conn = await get_conn(_dsn())
    try:
        profile = await get_journalist_profile(conn, slug)
        if not profile:
            raise HTTPException(status_code=404, detail="Journalist not found")
        return _serialize_profile(profile)
    finally:
        await conn.close()


def _serialize(row: dict) -> dict:
    return {
        k: str(v) if hasattr(v, "hex") else  # UUID
           float(v) if hasattr(v, "__round__") and not isinstance(v, (int, float, bool)) else  # Decimal
           v.isoformat() if hasattr(v, "isoformat") else  # datetime
           v
        for k, v in row.items()
    }


def _serialize_profile(profile: dict) -> dict:
    j = _serialize(profile["journalist"])
    s = _serialize(profile["scores"]) if profile["scores"] else None

    return {
        "id": j["id"],
        "full_name": j["full_name"],
        "slug": j["slug"],
        "primary_outlet": j.get("primary_outlet"),
        "beat": j.get("beat"),
        "data_status": j.get("data_status"),
        "pillar_scores": s,
        "fec_records": [_serialize(r) for r in profile["fec_records"]],
        "corrections": [_serialize(r) for r in profile["corrections"]],
        "appeals": [_serialize(r) for r in profile["appeals"]],
        "corpus_size": profile["corpus_size"],
        "corpus_start": profile["corpus_start"].isoformat() if profile["corpus_start"] else None,
        "corpus_end": profile["corpus_end"].isoformat() if profile["corpus_end"] else None,
        "methodology_version": s.get("methodology_version") if s else None,
        "composite_score": s.get("composite_score") if s else None,
        "scored_at": s.get("scored_at") if s else None,
    }
