"""
Print what is actually in the scoring warehouse.
Does not score. Does not call Anthropic.

Usage:
    PYTHONPATH=. python3 scripts/warehouse_status.py
"""

import asyncio
from dotenv import load_dotenv

load_dotenv()

from backend.database.db import get_conn


async def main():
    conn = await get_conn()
    try:
        pubs = await conn.fetch(
            "SELECT name, domain, api_source FROM publications ORDER BY name"
        )
        print("Publications")
        if not pubs:
            print("  (none)")
        for p in pubs:
            print(f"  {p['name']}  {p['domain']}  source={p['api_source']}")

        print("\nJournalists")
        rows = await conn.fetch(
            """
            SELECT
                j.full_name,
                j.slug,
                j.primary_outlet,
                j.data_status,
                COUNT(a.id) AS stored,
                COUNT(a.id) FILTER (
                    WHERE a.body IS NOT NULL AND COALESCE(a.access_level, 'full') = 'full'
                ) AS full_text,
                MIN(a.published_at) AS first_story,
                MAX(a.published_at) AS last_story,
                ps.composite_score,
                ps.corpus_size AS scored_from,
                ps.scored_at
            FROM journalists j
            LEFT JOIN articles a ON a.journalist_id = j.id
            LEFT JOIN LATERAL (
                SELECT composite_score, corpus_size, scored_at
                FROM pillar_scores
                WHERE journalist_id = j.id
                ORDER BY scored_at DESC
                LIMIT 1
            ) ps ON true
            GROUP BY j.id, j.full_name, j.slug, j.primary_outlet, j.data_status,
                     ps.composite_score, ps.corpus_size, ps.scored_at
            ORDER BY j.primary_outlet, j.full_name
            """
        )
        print(f"  {len(rows)} rows")
        for r in rows:
            score = (
                f"score={round(float(r['composite_score']) * 100)}"
                if r["composite_score"] is not None
                else "score=—"
            )
            first = r["first_story"].date().isoformat() if r["first_story"] else "—"
            last = r["last_story"].date().isoformat() if r["last_story"] else "—"
            print(
                f"  {r['full_name']:28}  {r['primary_outlet'] or '':20}  "
                f"stored={r['stored']:4}  full={r['full_text']:4}  "
                f"{first}..{last}  {score}  {r['data_status']}"
            )
    except Exception as e:
        print(f"Warehouse status failed: {e}")
        raise
    finally:
        await conn.close()


if __name__ == "__main__":
    asyncio.run(main())
