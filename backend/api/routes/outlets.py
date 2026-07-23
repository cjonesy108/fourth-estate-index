import os
from fastapi import APIRouter, HTTPException
from backend.database.queries import list_outlets, get_outlet_profile, get_conn

router = APIRouter()


def _dsn():
    return os.environ["DATABASE_URL"].replace("postgresql+asyncpg://", "postgresql://")


def _serialize(v):
    if hasattr(v, "hex"):          return str(v)
    if hasattr(v, "isoformat"):    return v.isoformat()
    if hasattr(v, "__round__") and not isinstance(v, (int, float, bool)):
        return float(v)
    return v


def _serialize_row(row: dict) -> dict:
    return {k: _serialize(v) for k, v in row.items()}


@router.get("")
async def list_outlets_route():
    conn = await get_conn(_dsn())
    try:
        outlets = await list_outlets(conn)
        return [_serialize_row(o) for o in outlets]
    finally:
        await conn.close()


@router.get("/{slug}")
async def get_outlet_route(slug: str):
    conn = await get_conn(_dsn())
    try:
        profile = await get_outlet_profile(conn, slug)
        if not profile:
            raise HTTPException(status_code=404, detail="Outlet not found")
        result = _serialize_row({k: v for k, v in profile.items() if k != "journalists"})
        result["journalists"] = [_serialize_row(j) for j in profile["journalists"]]
        return result
    finally:
        await conn.close()
