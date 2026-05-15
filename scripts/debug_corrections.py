"""
Print sample corrections articles to understand the format.
"""

import asyncio
import os
from datetime import datetime
from dotenv import load_dotenv

load_dotenv()

from backend.ingestion.corrections_ingestion import GuardianCorrectionsIngester

async def main():
    ingester = GuardianCorrectionsIngester(api_key=os.environ["GUARDIAN_API_KEY"])

    articles = await ingester.fetch_corrections(
        datetime(2024, 6, 1),
        datetime(2024, 6, 30),
    )

    print(f"Found {len(articles)} corrections articles in June 2024\n")

    for article in articles[:3]:
        fields = article.get("fields", {})
        body = ingester._strip_html(fields.get("body", ""))
        print(f"DATE:  {article.get('webPublicationDate', '')[:10]}")
        print(f"URL:   {article.get('webUrl', '')}")
        print(f"BODY:\n{body[:800]}")
        print("\n" + "─" * 60 + "\n")

    await ingester.close()

asyncio.run(main())
