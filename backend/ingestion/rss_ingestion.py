"""
RSS / Atom work-index ingester.

Stores headline, URL, date, and publisher-provided description.
Does not claim full text. access_level is 'excerpt' when a description
exists, otherwise 'metadata'.
"""

from __future__ import annotations

import logging
import re
from datetime import datetime, timezone
from email.utils import parsedate_to_datetime
from typing import Optional
from xml.etree import ElementTree as ET

import httpx

from backend.ingestion.article_ingestion import IngestionResult, ParsedArticle

logger = logging.getLogger(__name__)

ATOM = "{http://www.w3.org/2005/Atom}"
DC = "{http://purl.org/dc/elements/1.1/}"
CONTENT = "{http://purl.org/rss/1.0/modules/content/}"


def _text(el: Optional[ET.Element]) -> str:
    if el is None:
        return ""
    return "".join(el.itertext()).strip()


def _strip_html(html: str) -> str:
    clean = re.sub(r"<[^>]+>", " ", html or "")
    return re.sub(r"\s+", " ", clean).strip()


def _parse_date(value: str) -> Optional[datetime]:
    if not value:
        return None
    value = value.strip()
    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        pass
    try:
        return parsedate_to_datetime(value)
    except (TypeError, ValueError):
        return None


class RSSIngester:
    source_name = "rss"

    def __init__(self, timeout: float = 20.0):
        self.client = httpx.AsyncClient(
            timeout=timeout,
            headers={"User-Agent": "FourthEstateIndex/0.2 (+https://fourth-estate-index.vercel.app)"},
            follow_redirects=True,
        )

    async def close(self):
        await self.client.aclose()

    async def ingest(
        self,
        feed_url: str,
        date_from: datetime,
        date_to: datetime,
        existing_ids: set[str],
        default_section: str = "",
    ) -> tuple[list[ParsedArticle], IngestionResult]:
        result = IngestionResult(
            articles_ingested=0,
            articles_skipped_duplicate=0,
            articles_skipped_short=0,
            articles_skipped_no_body=0,
            corpus_start=None,
            corpus_end=None,
            errors=[],
        )
        try:
            resp = await self.client.get(feed_url)
            resp.raise_for_status()
        except Exception as e:
            result.errors.append(f"feed fetch failed: {e}")
            return [], result

        try:
            items = self.parse_feed(resp.text, default_section=default_section)
        except Exception as e:
            result.errors.append(f"feed parse failed: {e}")
            return [], result

        articles: list[ParsedArticle] = []
        start = date_from.replace(tzinfo=date_from.tzinfo or timezone.utc)
        end = date_to.replace(tzinfo=date_to.tzinfo or timezone.utc)

        for parsed in items:
            if parsed.guardian_id in existing_ids or parsed.url in existing_ids:
                result.articles_skipped_duplicate += 1
                continue
            pub = parsed.published_at
            if pub.tzinfo is None:
                pub = pub.replace(tzinfo=timezone.utc)
            if pub < start or pub > end:
                continue
            articles.append(parsed)
            existing_ids.add(parsed.guardian_id)
            result.articles_ingested += 1
            if result.corpus_start is None or parsed.published_at < result.corpus_start:
                result.corpus_start = parsed.published_at
            if result.corpus_end is None or parsed.published_at > result.corpus_end:
                result.corpus_end = parsed.published_at

        return articles, result

    def parse_feed(self, xml: str, default_section: str = "") -> list[ParsedArticle]:
        root = ET.fromstring(xml)
        if root.tag.lower().endswith("feed") or root.find(f"{ATOM}entry") is not None:
            return self._parse_atom(root, default_section)
        return self._parse_rss(root, default_section)

    def _parse_rss(self, root: ET.Element, default_section: str) -> list[ParsedArticle]:
        items = []
        for item in root.findall("./channel/item"):
            title = _text(item.find("title"))
            link = _text(item.find("link"))
            guid = _text(item.find("guid")) or link
            desc = _strip_html(_text(item.find("description")) or _text(item.find(f"{CONTENT}encoded")))
            pub = _parse_date(_text(item.find("pubDate")) or _text(item.find(f"{DC}date")))
            if not title or not link or pub is None:
                continue
            items.append(self._article(guid, title, desc, link, pub, default_section, _text(item.find(f"{DC}creator"))))
        return items

    def _parse_atom(self, root: ET.Element, default_section: str) -> list[ParsedArticle]:
        items = []
        for entry in root.findall(f"{ATOM}entry"):
            title = _text(entry.find(f"{ATOM}title"))
            link_el = entry.find(f"{ATOM}link[@rel='alternate']") or entry.find(f"{ATOM}link")
            link = (link_el.get("href") if link_el is not None else "") or ""
            ident = _text(entry.find(f"{ATOM}id")) or link
            summary = _strip_html(_text(entry.find(f"{ATOM}summary")) or _text(entry.find(f"{ATOM}content")))
            pub = _parse_date(_text(entry.find(f"{ATOM}published")) or _text(entry.find(f"{ATOM}updated")))
            if not title or not link or pub is None:
                continue
            author = _text(entry.find(f"{ATOM}author/{ATOM}name"))
            items.append(self._article(ident, title, summary, link, pub, default_section, author))
        return items

    def _article(self, external_id, headline, lede, url, published_at, section, byline) -> ParsedArticle:
        access = "excerpt" if lede else "metadata"
        return ParsedArticle(
            guardian_id=external_id or url,
            headline=headline,
            subheadline=lede or None,
            body=lede or None,
            url=url,
            published_at=published_at.replace(tzinfo=None),
            section=section,
            word_count=len(lede.split()) if lede else 0,
            byline=byline or None,
            access_level=access,
            lede=lede or None,
        )
