"""
X (Twitter) API v2 ingestion.

Uses app-only Bearer token auth. The free tier allows user lookups but
timeline reads may return 403 — handled gracefully with an empty result.
Architecture is designed to run unchanged on Basic tier ($100/mo) which
unlocks full timeline access.
"""

import logging
from dataclasses import dataclass
from datetime import datetime
from typing import Optional

import httpx

logger = logging.getLogger(__name__)

BASE_URL = "https://api.twitter.com/2"


@dataclass
class XPost:
    post_id: str
    content: str
    posted_at: datetime
    is_reply: bool
    is_quote: bool
    platform: str = "twitter"


@dataclass
class XUser:
    user_id: str
    username: str
    display_name: str
    description: str
    followers: int
    verified: bool


class XIngester:
    def __init__(self, bearer_token: str):
        self._headers = {
            "Authorization": f"Bearer {bearer_token}",
            "User-Agent": "FourthEstateIndex/1.0",
        }

    async def get_user(self, username: str) -> Optional[XUser]:
        """Look up a user by username. Always available on free tier."""
        url = f"{BASE_URL}/users/by/username/{username}"
        params = {
            "user.fields": "public_metrics,description,verified,verified_type"
        }
        async with httpx.AsyncClient(headers=self._headers, timeout=30.0) as client:
            resp = await client.get(url, params=params)

        if resp.status_code == 404:
            logger.warning(f"X user not found: @{username}")
            return None
        if resp.status_code != 200:
            logger.warning(f"X user lookup failed for @{username}: HTTP {resp.status_code}")
            return None

        data = resp.json().get("data", {})
        if not data:
            return None

        metrics = data.get("public_metrics", {})
        return XUser(
            user_id=data["id"],
            username=data["username"],
            display_name=data.get("name", ""),
            description=data.get("description", ""),
            followers=metrics.get("followers_count", 0),
            verified=bool(data.get("verified") or data.get("verified_type")),
        )

    async def get_timeline(self, user_id: str, max_results: int = 100) -> list[XPost]:
        """
        Fetch recent tweets for a user. Requires Basic tier or higher.
        Returns empty list with a warning on free tier (HTTP 403).
        """
        url = f"{BASE_URL}/users/{user_id}/tweets"
        params = {
            "max_results": min(max_results, 100),
            "tweet.fields": "created_at,referenced_tweets,in_reply_to_user_id",
            "exclude": "retweets",
        }
        async with httpx.AsyncClient(headers=self._headers, timeout=30.0) as client:
            resp = await client.get(url, params=params)

        if resp.status_code == 403:
            logger.warning(
                f"Timeline read for user {user_id} returned 403 — "
                "free tier does not include timeline access. "
                "Upgrade to Basic ($100/mo) to enable social analysis."
            )
            return []
        if resp.status_code != 200:
            logger.warning(f"Timeline fetch failed for user {user_id}: HTTP {resp.status_code} — {resp.text[:200]}")
            return []

        tweets = resp.json().get("data", [])
        posts = []
        for t in tweets:
            created = t.get("created_at", "")
            try:
                posted_at = datetime.fromisoformat(created.replace("Z", "+00:00")).replace(tzinfo=None)
            except (ValueError, AttributeError):
                posted_at = datetime.utcnow()

            refs = t.get("referenced_tweets", [])
            ref_types = {r["type"] for r in refs} if refs else set()

            posts.append(XPost(
                post_id=t["id"],
                content=t["text"],
                posted_at=posted_at,
                is_reply=bool(t.get("in_reply_to_user_id")),
                is_quote="quoted" in ref_types,
            ))

        logger.info(f"Fetched {len(posts)} tweets for user {user_id}")
        return posts

    async def ingest(
        self,
        x_handle: str,
        existing_post_ids: set[str],
        max_results: int = 100,
    ) -> tuple[Optional[XUser], list[XPost]]:
        """
        Full ingestion: verify user exists, then fetch timeline.
        Returns (user_info, new_posts) — new_posts excludes already-stored IDs.
        """
        user = await self.get_user(x_handle)
        if not user:
            return None, []

        posts = await self.get_timeline(user.user_id, max_results=max_results)
        new_posts = [p for p in posts if p.post_id not in existing_post_ids]
        logger.info(f"@{x_handle}: {len(posts)} fetched, {len(new_posts)} new after dedup")
        return user, new_posts
