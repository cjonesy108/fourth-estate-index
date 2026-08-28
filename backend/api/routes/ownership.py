from fastapi import APIRouter, HTTPException
from backend.ownership.graph import load_graph, entity, edges_from, edges_to

router = APIRouter()


@router.get("")
async def ownership_index():
    graph = load_graph()
    return {
        "version": graph["version"],
        "as_of_economic": graph["as_of_economic"],
        "as_of_note": graph["as_of_note"],
        "outlets": [e for e in graph["entities"] if e.get("is_outlet")],
        "institutions": [e for e in graph["entities"] if e["type"] == "institution"],
        "controllers": [
            e
            for e in graph["entities"]
            if e["type"] in ("family", "individual", "trust")
        ],
    }


@router.get("/{slug}")
async def ownership_entity(slug: str):
    row = entity(slug)
    if not row:
        raise HTTPException(status_code=404, detail="Entity not found")
    return {
        "entity": row,
        "held_by": edges_to(slug),
        "holds": edges_from(slug),
    }
