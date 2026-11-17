"""Validate public news hyperlinks without fetching or changing the feed."""
import ipaddress
import re
from urllib.parse import urlsplit


def valid_news_link(value):
    if not isinstance(value, str) or not value or '\\' in value:
        return False
    if any(c.isspace() or ord(c) < 32 or 127 <= ord(c) <= 159 for c in value):
        return False
    try:
        parsed = urlsplit(value)
        # Match absolute HTTP(S) links only; userinfo makes a destination deceptive.
        if (parsed.scheme.lower() not in ('http', 'https') or not parsed.hostname
                or not value.lower().startswith(parsed.scheme.lower() + '://')
                or '@' in parsed.netloc or '%' in parsed.hostname):
            return False
        parsed.port  # Reject malformed or out-of-range ports.
        host = parsed.hostname
        if ':' in host:
            ipaddress.IPv6Address(host)
        else:
            ascii_host = host.encode('idna').decode('ascii')
            if not re.fullmatch(r'[a-zA-Z0-9_-]+(?:\.[a-zA-Z0-9_-]+)*\.?', ascii_host):
                return False
        return True
    except (ValueError, UnicodeError):
        return False
