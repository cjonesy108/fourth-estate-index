"""
Look up a journalist's correct Guardian tag and preview their articles.
Usage: python3 scripts/find_guardian_tag.py
"""

import asyncio
import os
import httpx
from dotenv import load_dotenv

load_dotenv()

NAME = "Hadley Freeman"
GUARDIAN_BASE = "https://content.guardianapis.com"


async def main():
    api_key = os.environ.get("GUARDIAN_API_KEY")

    async with httpx.AsyncClient() as client:
        # Step 1: find the contributor tag
        print(f"Searching for contributor tag: {NAME}")
        resp = await client.get(f"{GUARDIAN_BASE}/tags", params={
            "type": "contributor",
            "q": NAME,
            "api-key": api_key,
        })
        data = resp.json()
        results = data.get("response", {}).get("results", [])

        if not results:
            print("No contributor tag found.")
        else:
            for r in results:
                print(f"  Found tag: {r['id']}  —  {r.get('webTitle')}")

        print()

        # Step 2: try a direct article search by byline
        print(f"Searching articles by byline...")
        resp2 = await client.get(f"{GUARDIAN_BASE}/search", params={
            "q": f'"{NAME}"',
            "show-fields": "headline,byline,wordcount",
            "page-size": 5,
            "api-key": api_key,
        })
        data2 = resp2.json()
        articles = data2.get("response", {}).get("results", [])
        total = data2.get("response", {}).get("total", 0)

        print(f"  Total articles found: {total}")
        for a in articles:
            fields = a.get("fields", {})
            print(f"  - {fields.get('headline', a.get('webTitle'))}")
            print(f"    Byline: {fields.get('byline', 'n/a')}")
            print(f"    Tag: {a.get('id')}")
            print()


asyncio.run(main())
