"""
Upsert the versioned journalist directory into Postgres.

Usage:
    PYTHONPATH=. python3 scripts/seed_directory.py
"""

import asyncio
import json
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()

from backend.database.db import get_conn, save_journalist, save_publication

ROOT = Path(__file__).resolve().parents[1]
DIRECTORY = ROOT / "frontend" / "data" / "directory.json"
ADDITIONS = ROOT / "frontend" / "data" / "directory-additions.json"


def load_directory() -> dict:
    data = json.loads(DIRECTORY.read_text())
    if ADDITIONS.exists():
        extra = json.loads(ADDITIONS.read_text())
        extra_slugs = {o["slug"] for o in extra.get("outlets", [])}
        outlets = [o for o in data["outlets"] if o["slug"] not in extra_slugs]
        outlets.extend(extra.get("outlets", []))
        seen = {j["slug"] for j in data["journalists"]}
        journalists = list(data["journalists"])
        for j in extra.get("journalists", []):
            if j["slug"] not in seen:
                journalists.append(j)
                seen.add(j["slug"])
        data["outlets"] = outlets
        data["journalists"] = journalists
        data["version"] = extra.get("version", data["version"])
    return data


def _status(raw: str | None) -> str:
    if raw == "scored":
        return "scored"
    return "collecting"


async def main():
    data = load_directory()
    outlets = {o["slug"]: o for o in data["outlets"]}
    print(f"Directory v{data['version']} · {len(data['journalists'])} journalists")

    conn = await get_conn()
    try:
        await conn.execute(
            """
            CREATE TABLE IF NOT EXISTS journalist_identities (
                id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                journalist_id   UUID REFERENCES journalists(id) NOT NULL,
                outlet_slug     VARCHAR(255) NOT NULL,
                author_slug     VARCHAR(255),
                author_url      VARCHAR(1000),
                feed_url        VARCHAR(1000),
                guardian_tag    VARCHAR(255),
                start_date      DATE,
                end_date        DATE,
                source          VARCHAR(100),
                created_at      TIMESTAMP DEFAULT NOW(),
                UNIQUE (journalist_id, outlet_slug, author_slug)
            )
            """
        )

        for outlet in data["outlets"]:
            if outlet.get("queued") and not any(
                j["primary_outlet"] == outlet["slug"] for j in data["journalists"]
            ):
                continue
            await save_publication(
                conn,
                name=outlet["name"],
                domain=outlet["domain"],
                api_source=outlet["api_source"],
            )
            print(f"  outlet {outlet['name']} ({outlet['access']})")

        for j in data["journalists"]:
            outlet = outlets[j["primary_outlet"]]
            jid = await save_journalist(
                conn,
                full_name=j["full_name"],
                slug=j["slug"],
                primary_outlet=outlet["name"],
                guardian_tag=j.get("guardian_tag"),
                x_handle=j.get("x_handle"),
            )
            await conn.execute(
                """
                UPDATE journalists
                SET beat = $1,
                    data_status = CASE
                        WHEN data_status = 'scored' THEN data_status
                        ELSE $2
                    END,
                    updated_at = NOW()
                WHERE id = $3
                """,
                j.get("beat"),
                _status(j.get("directory_status")),
                jid,
            )
            await conn.execute(
                """
                INSERT INTO journalist_identities
                    (journalist_id, outlet_slug, author_slug, author_url, feed_url, guardian_tag, source)
                VALUES ($1,$2,$3,$4,$5,$6,'directory')
                ON CONFLICT (journalist_id, outlet_slug, author_slug) DO UPDATE
                    SET author_url = EXCLUDED.author_url,
                        feed_url = EXCLUDED.feed_url,
                        guardian_tag = EXCLUDED.guardian_tag
                """,
                jid,
                j["primary_outlet"],
                j.get("author_slug") or j["slug"],
                j.get("author_url"),
                j.get("feed_url"),
                j.get("guardian_tag"),
            )
            print(f"  {j['full_name']} → {outlet['name']} [{j['directory_status']}]")

        print("Done.")
    finally:
        await conn.close()


if __name__ == "__main__":
    asyncio.run(main())
