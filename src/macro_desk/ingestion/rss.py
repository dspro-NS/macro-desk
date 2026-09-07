from __future__ import annotations

import logging
from email.utils import parsedate_to_datetime
from typing import Optional
from xml.etree import ElementTree

from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)


class RssItem(BaseModel):
    title: str = Field(min_length=1)
    source_url: str = Field(min_length=1)
    published_at: Optional[str] = None
    raw_text: str = ""


def _text(element: Optional[ElementTree.Element]) -> str:
    if element is None or element.text is None:
        return ""
    return element.text.strip()


def parse_rss(xml_bytes: bytes) -> list[RssItem]:
    """Parse an RSS 2.0 feed into item records. Invalid items are skipped."""
    xml_text = xml_bytes.decode("utf-8-sig")
    try:
        root = ElementTree.fromstring(xml_text)
    except ElementTree.ParseError as exc:
        raise ValueError("RSS feed is not valid XML") from exc

    items: list[RssItem] = []
    for item in root.findall("./channel/item"):
        title = _text(item.find("title"))
        link = _text(item.find("link"))
        description = _text(item.find("description"))
        pub_date = _text(item.find("pubDate")) or None
        if not title or not link:
            logger.warning("Skipping RSS item missing title or link")
            continue
        items.append(
            RssItem(
                title=title,
                source_url=link,
                published_at=pub_date,
                raw_text=description,
            )
        )
    return items


def parse_pub_date(value: Optional[str]):
    """Parse RSS pubDate; naive timestamps are treated as UTC."""
    from datetime import datetime, timezone

    if not value:
        return datetime.now(timezone.utc)
    try:
        parsed = parsedate_to_datetime(value)
    except (TypeError, ValueError) as exc:
        logger.warning("Could not parse pubDate %r: %s", value, exc)
        return datetime.now(timezone.utc)
    if parsed.tzinfo is None:
        return parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone(timezone.utc)
