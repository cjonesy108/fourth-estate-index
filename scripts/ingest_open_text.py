"""
Fetch public full text into the warehouse. Does not call any model.

Usage:
    PYTHONPATH=. python3 scripts/ingest_open_text.py propublica
    PYTHONPATH=. python3 scripts/ingest_open_text.py texastribune
    PYTHONPATH=. python3 scripts/ingest_open_text.py propublica justin-elliott
"""

import asyncio
import json
import sys
from datetime import datetime
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()

from backend.database.db import (
    get_article_id_map,
    get_conn,
    get_existing_guardian_ids,
    save_articles,
    save_journalist,
    save_publication,
)
from backend.ingestion.propublica_ingestion import ProPublicaIngester
from backend.ingestion.texastribune_ingestion import TexasTribuneIngester

ROOT = Path(__file__).resolve().parents[1]
DATE_FROM = datetime(2023, 1, 1)
DATE_TO = datetime(2026, 9, 1)

OUTLETS = {
    "propublica": {
        "name": "ProPublica",
        "domain": "propublica.org",
        "api_source": "propublica",
        "slug": "propublica",
        "ingester": ProPublicaIngester,
    },
    "texastribune": {
        "name": "The Texas Tribune",
        "domain": "texastribune.org",
        "api_source": "texastribune",
        "slug": "texas-tribune",
        "ingester": TexasTribuneIngester,
    },
}


def load_people(outlet_slug: str) -> list[dict]:
    extra = json.loads((ROOT / "frontend/data/directory-additions.json").read_text())
    return [j for j in extra.get("journalists", []) if j.get("primary_outlet") == outlet_slug]


async def ingest_one(conn, pub_id: str, spec: dict, journalist: dict):
    name = journalist["full_name"]
    slug = journalist["slug"]
    print(f"\n  {name}")
    journalist_id = await save_journalist(
        conn,
        full_name=name,
        slug=slug,
        primary_outlet=spec["name"],
    )
    existing_ids = await get_existing_guardian_ids(conn, journalist_id)
    async with spec["ingester"]() as ingester:
        articles, result = await ingester.ingest(
            journalist_id=journalist_id,
            author_slug=journalist.get("author_slug") or slug,
            date_from=DATE_FROM,
            date_to=DATE_TO,
            existing_ids=existing_ids,
        )
    print(
        f"    fetched={result.articles_ingested}  "
        f"dup={result.articles_skipped_duplicate}  "
        f"short={result.articles_skipped_short}  "
        f"no_body={result.articles_skipped_no_body}"
    )
    if result.errors:
        print(f"    errors: {result.errors}")
    if articles:
        saved = await save_articles(
            conn, journalist_id, pub_id, articles, source_api=spec["api_source"]
        )
        print(f"    saved={saved}")
    total = len(await get_article_id_map(conn, journalist_id))
    print(f"    corpus={total}")
    await conn.execute(
        """
        UPDATE journalists
        SET data_status = CASE
            WHEN data_status = 'scored' THEN data_status
            ELSE 'collecting'
        END,
        updated_at = NOW()
        WHERE id = $1
        """,
        journalist_id,
    )


async def main():
    if len(sys.argv) < 2 or sys.argv[1] not in OUTLETS:
        print("Usage: ingest_open_text.py propublica|texastribune [slug]")
        sys.exit(1)
    key = sys.argv[1]
    slug_filter = sys.argv[2] if len(sys.argv) > 2 else None
    spec = OUTLETS[key]
    people = load_people(spec["slug"])
    if slug_filter:
        people = [j for j in people if j["slug"] == slug_filter]
    if not people:
        print(f"No journalists for {key} {slug_filter or ''}")
        sys.exit(1)

    print(f"Ingest only — {spec['name']} — {len(people)} journalists — no model")
    conn = await get_conn()
    try:
        pub_id = await save_publication(
            conn,
            name=spec["name"],
            domain=spec["domain"],
            api_source=spec["api_source"],
        )
        for journalist in people:
            try:
                await ingest_one(conn, pub_id, spec, journalist)
            except Exception as e:
                print(f"    Failed {journalist.get('slug')}: {e}")
        print("\nIngest complete.\n")
    finally:
        await conn.close()


if __name__ == "__main__":
    asyncio.run(main())
