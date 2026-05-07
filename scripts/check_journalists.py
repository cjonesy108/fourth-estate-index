"""
Check Guardian contributor tags and article volume for a list of journalists.
Run this before adding anyone to the pipeline.
"""

import asyncio
import os
import httpx
from dotenv import load_dotenv

load_dotenv()

GUARDIAN_BASE = "https://content.guardianapis.com"

CANDIDATES = [
    "Lauren Gambino",
    "Shrai Popat",
    "Hugo Lowell",
    "David Smith",
    "Joan E Greve",
    "Stephanie Kirchgaessner",
    "Ed Pilkington",
]


async def check(client, name: str, api_key: str):
    # Find contributor tag
    resp = await client.get(f"{GUARDIAN_BASE}/tags", params={
        "type": "contributor",
        "q": name,
        "api-key": api_key,
    })
    results = resp.json().get("response", {}).get("results", [])
    if not results:
        print(f"  ✗ {name} — no contributor tag found")
        return

    tag = results[0]["id"]

    # Check article volume 2023-2024
    resp2 = await client.get(f"{GUARDIAN_BASE}/search", params={
        "tag": tag,
        "from-date": "2023-01-01",
        "to-date": "2024-12-31",
        "page-size": 1,
        "api-key": api_key,
    })
    total = resp2.json().get("response", {}).get("total", 0)

    status = "✅" if total >= 20 else "⚠️ " if total >= 5 else "✗ "
    print(f"  {status} {name:<35} tag: {tag:<45} articles: {total}")


async def main():
    api_key = os.environ.get("GUARDIAN_API_KEY")
    print(f"Checking {len(CANDIDATES)} candidates (2023-2024)...\n")
    async with httpx.AsyncClient(timeout=15) as client:
        for name in CANDIDATES:
            await check(client, name, api_key)
            await asyncio.sleep(0.3)


asyncio.run(main())
