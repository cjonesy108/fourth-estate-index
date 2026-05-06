"""
Raw debug — prints the exact Guardian API response so we can see what's happening.
"""

import asyncio
import os
import httpx
from dotenv import load_dotenv

load_dotenv()

GUARDIAN_BASE = "https://content.guardianapis.com"


async def main():
    api_key = os.environ.get("GUARDIAN_API_KEY")
    print(f"API key present: {'yes' if api_key else 'NO - check .env file'}")
    print()

    async with httpx.AsyncClient() as client:
        # Test 1: tag search with body
        print("Test 1: search by tag with body field")
        resp = await client.get(f"{GUARDIAN_BASE}/search", params={
            "tag": "profile/hadleyfreeman",
            "show-fields": "headline,byline,wordcount,body",
            "page-size": 3,
            "api-key": api_key,
        })
        data = resp.json()
        response = data.get("response", {})
        print(f"  Status:  {response.get('status')}")
        print(f"  Total:   {response.get('total')}")
        print(f"  Results: {len(response.get('results', []))}")

        for r in response.get("results", [])[:2]:
            fields = r.get("fields", {})
            body = fields.get("body", "")
            print(f"  - {fields.get('headline', r.get('webTitle', ''))[:60]}")
            print(f"    body present: {'yes' if body else 'NO'} ({len(body)} chars)")

        print()

        # Test 2: same but without body — see if that's the blocker
        print("Test 2: search by tag WITHOUT body field")
        resp2 = await client.get(f"{GUARDIAN_BASE}/search", params={
            "tag": "profile/hadleyfreeman",
            "show-fields": "headline,byline,wordcount",
            "page-size": 3,
            "api-key": api_key,
        })
        data2 = resp2.json()
        response2 = data2.get("response", {})
        print(f"  Status:  {response2.get('status')}")
        print(f"  Total:   {response2.get('total')}")
        print(f"  Results: {len(response2.get('results', []))}")

        # Test 3: same search WITH date range
        print()
        print("Test 3: search by tag WITH date range 2023-2024")
        resp3 = await client.get(f"{GUARDIAN_BASE}/search", params={
            "tag": "profile/hadleyfreeman",
            "from-date": "2023-01-01",
            "to-date": "2024-12-31",
            "show-fields": "headline,byline,wordcount,body",
            "page-size": 3,
            "api-key": api_key,
        })
        data3 = resp3.json()
        response3 = data3.get("response", {})
        print(f"  Status:  {response3.get('status')}")
        print(f"  Total:   {response3.get('total')}")
        print(f"  Results: {len(response3.get('results', []))}")
        for r in response3.get("results", [])[:2]:
            fields = r.get("fields", {})
            body = fields.get("body", "")
            print(f"  - {fields.get('headline', r.get('webTitle', ''))[:60]}")
            print(f"    body: {'yes' if body else 'NO'} ({len(body)} chars)")
            print(f"    date: {r.get('webPublicationDate', 'n/a')}")


asyncio.run(main())
