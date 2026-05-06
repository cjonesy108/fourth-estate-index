"""
X / Twitter social post ingestion — X API Pro.

Includes replies — they often contain the most unguarded expression
of viewpoint and are public record.

TODO: Implement when X API Pro access is available.
"""


class SocialIngester:
    async def ingest(
        self,
        journalist_id: str,
        x_handle: str,
        date_from,
        date_to,
        existing_post_ids: set[str],
    ) -> dict:
        # TODO: Implement
        # 1. Auth with bearer token
        # 2. Pull timeline with date range filter
        # 3. Include original posts, quote tweets, replies
        # 4. Exclude pure retweets with no added text
        raise NotImplementedError("Social ingestion not yet implemented")
