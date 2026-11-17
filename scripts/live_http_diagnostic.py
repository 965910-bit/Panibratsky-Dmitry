#!/usr/bin/env python3
"""Read-only fixed-origin HTTP probe. Does not follow redirects or enumerate hosts."""
import json
import socket
import ssl
import urllib.error
import urllib.request
from urllib.parse import urlsplit

URLS = {
    'http_apex': 'http://scm-news.ru/',
    'https_apex': 'https://scm-news.ru/',
    'http_www': 'http://www.scm-news.ru/',
    'https_www': 'https://www.scm-news.ru/',
    'missing': 'https://scm-news.ru/diagnostic-nonexistent-fb8e0f63.html',
    'index_alias': 'https://scm-news.ru/index.html',
}


class NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return None


def fetch(url):
    req = urllib.request.Request(url, headers={'User-Agent': 'SCM-News-HTTP-Diagnostic/1.0'})
    try:
        response = urllib.request.build_opener(NoRedirect).open(req, timeout=15)
    except urllib.error.HTTPError as exc:
        response = exc
    with response:
        return response.status, response.headers


def safe_location(value):
    if not value:
        return None
    parsed = urlsplit(value)
    if parsed.query or parsed.fragment or parsed.username or parsed.password:
        return 'redacted redirect with parameters or credentials'
    if not parsed.netloc:
        return parsed.path if parsed.path.startswith('/') else 'relative redirect'
    if parsed.scheme in ('http', 'https') and parsed.netloc.lower() in ('scm-news.ru', 'www.scm-news.ru'):
        return parsed.scheme + '://' + parsed.netloc.lower() + parsed.path
    return 'other origin'


def probe(fetcher=fetch):
    output = {}
    for label, url in URLS.items():
        try:
            status, headers = fetcher(url)
            hsts = headers.get('Strict-Transport-Security', '')
            output[label] = {'status': status, 'location': safe_location(headers.get('Location', '')),
                             'hsts': hsts[:160] if hsts else None}
        except (urllib.error.URLError, OSError, ValueError) as exc:
            reason = getattr(exc, 'reason', exc)
            kind = ('tls' if isinstance(reason, ssl.SSLError) else
                    'dns' if isinstance(reason, socket.gaierror) else
                    'timeout' if isinstance(reason, (TimeoutError, socket.timeout)) else 'network')
            output[label] = {'error': kind}

    return output


def main():
    result = probe()
    for label, row in result.items():
        # Fixed labels, status, host-only redirects and response headers; no cookies.
        print('::notice title=HTTP ' + label + '::' + json.dumps(row, ensure_ascii=True).replace('%', '%25'))
    print('Read-only fixed URLs only; no subdomain enumeration, preload or index verification.')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
