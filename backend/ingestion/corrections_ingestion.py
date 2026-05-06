"""
Corrections ingestion — publication-specific scrapers.

TODO: Implement per-publication scrapers.
The Guardian corrections: https://www.theguardian.com/theguardian/series/corrections-and-clarifications
"""


class CorrectionsIngester:
    async def ingest(
        self,
        publication_id: str,
        journalist_id: str,
        date_from,
        date_to,
    ) -> dict:
        # TODO: Implement
        # 1. Load publication scraper config
        # 2. Fetch corrections page
        # 3. Parse entries and match to journalist byline
        # 4. Classify correction type via Claude API
        # 5. Calculate days_to_correction
        raise NotImplementedError("Corrections ingestion not yet implemented")
