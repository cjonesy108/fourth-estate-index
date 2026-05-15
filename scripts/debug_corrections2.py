"""
Debug: show what headlines and URLs are extractable from corrections articles.
"""

import asyncio
import os
import re
from datetime import datetime
from dotenv import load_dotenv

load_dotenv()

import httpx

GUARDIAN_BASE = "https://content.guardianapis.com"


async def main():
    api_key = os.environ["GUARDIAN_API_KEY"]

    async with httpx.AsyncClient() as client:
        resp = await client.get(f"{GUARDIAN_BASE}/search", params={
            "tag": "theguardian/series/corrections-and-clarifications",
            "from-date": "2024-06-01",
            "to-date": "2024-06-30",
            "show-fields": "body,headline",
            "page-size": 3,
            "api-key": api_key,
        })
        articles = resp.json().get("response", {}).get("results", [])

    for article in articles[:2]:
        body_html = article.get("fields", {}).get("body", "")

        print(f"\nURL: {article.get('webUrl', '')[:80]}")
        print(f"\n--- RAW HTML (first 1000 chars) ---")
        print(body_html[:1000])

        # Extract all guardian.com links from HTML
        links = re.findall(r'href="(https://www\.theguardian\.com/[^"]+)"', body_html)
        print(f"\n--- GUARDIAN LINKS FOUND ({len(links)}) ---")
        for link in links[:10]:
            print(f"  {link}")

        # Extract quoted titles
        quoted = re.findall(r'["""]([^"""]{10,120})["""]', body_html)
        print(f"\n--- QUOTED TEXT ({len(quoted)}) ---")
        for q in quoted[:5]:
            print(f"  {q}")

        print("\n" + "=" * 60)


asyncio.run(main())
