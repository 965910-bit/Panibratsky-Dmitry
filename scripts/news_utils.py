"""Pure helpers for safely retaining and ordering collected news."""
from datetime import datetime, timedelta, timezone
from email.utils import parsedate_to_datetime
from urllib.parse import urlsplit


def news_date(item):
    try:
        date = parsedate_to_datetime(item.get('pubDate', ''))
        if date.tzinfo is None:
            date = date.replace(tzinfo=timezone.utc)
        return date.astimezone(timezone.utc)
    except (TypeError, ValueError, OverflowError):
        return None


def merge_news(existing, incoming, days=30, now=None):
    """Keep existing news, deduplicate URLs, prune dated old entries and sort by date.

    Undated entries are retained but placed last. An incoming item does not erase
    metadata such as the link checker's dead flag on an existing item.
    """
    now = now or datetime.now(timezone.utc)
    cutoff = now - timedelta(days=days)
    seen = set()
    merged = []
    for item in [*existing, *incoming]:
        if not isinstance(item, dict):
            continue
        link = item.get('link')
        if not isinstance(link, str):
            continue
        try:
            url = urlsplit(link)
            if url.scheme not in ('http', 'https') or not url.hostname:
                continue
        except ValueError:
            continue
        date = news_date(item)
        if date and date < cutoff:
            continue
        if link in seen:
            continue
        seen.add(link)
        merged.append(item)
    merged.sort(key=lambda item: news_date(item) or datetime.min.replace(tzinfo=timezone.utc), reverse=True)
    return merged
