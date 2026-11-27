#!/usr/bin/env python3
"""Opt-in, read-only webmaster API snapshot. Tokens only in process environment.

Not an OAuth client or scheduler. Do not redirect output into a public repo.
"""
import argparse
from datetime import date, datetime, timedelta, timezone
import json
import os
import sys
import urllib.error
import urllib.parse
import urllib.request

SITE = 'https://scm-news.ru/'
DOMAIN_PROPERTY = 'sc-domain:scm-news.ru'
YANDEX_API = 'https://api.webmaster.yandex.net/v4'
GOOGLE_API = 'https://www.googleapis.com/webmasters/v3'
MAX_RESPONSE = 2 * 1024 * 1024


class SnapshotError(Exception):
    pass


class NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return None


def request_json(url, token, scheme, body=None):
    # URL construction is internal, never from a command-line option or API response.
    if not (url.startswith(YANDEX_API + '/') or url.startswith(GOOGLE_API + '/')):
        raise SnapshotError('unexpected endpoint')
    if not token or '\r' in token or '\n' in token:
        raise SnapshotError('missing or invalid token')
    headers = {'Authorization': scheme + ' ' + token, 'Accept': 'application/json'}
    raw = None
    if body is not None:
        raw = json.dumps(body).encode('utf-8')
        headers['Content-Type'] = 'application/json'
    request = urllib.request.Request(url, data=raw, headers=headers, method='POST' if raw is not None else 'GET')
    try:
        with urllib.request.build_opener(NoRedirect).open(request, timeout=20) as response:
            content = response.read(MAX_RESPONSE + 1)
        if len(content) > MAX_RESPONSE:
            raise SnapshotError('response too large')
        data = json.loads(content)
        if not isinstance(data, dict):
            raise SnapshotError('unexpected response')
        return data
    except urllib.error.HTTPError as exc:
        # Do not print API response bodies or exception URLs: these can expose account data.
        raise SnapshotError('HTTP ' + str(exc.code)) from None
    except (urllib.error.URLError, TimeoutError, OSError, UnicodeError, json.JSONDecodeError):
        raise SnapshotError('network or response error') from None


def google_snapshot(token, start, end, request=request_json):
    sites = request(GOOGLE_API + '/sites', token, 'Bearer').get('siteEntry', [])
    props = [x.get('siteUrl') for x in sites if isinstance(x, dict)]
    # Never silently choose a different hostname or a scheme variant.
    property_name = next((x for x in (SITE, DOMAIN_PROPERTY) if x in props), None)
    if property_name is None:
        raise SnapshotError('site property not found or inaccessible')
    base = GOOGLE_API + '/sites/' + urllib.parse.quote(property_name, safe='')
    sitemaps = request(base + '/sitemaps', token, 'Bearer').get('sitemap', [])
    wanted = [s for s in sitemaps if isinstance(s, dict) and s.get('path') == SITE + 'sitemap.xml']
    performance = request(base + '/searchAnalytics/query', token, 'Bearer', {
        'startDate': start.isoformat(), 'endDate': end.isoformat(), 'type': 'web',
        'dataState': 'final', 'rowLimit': 1,
    })
    rows = performance.get('rows', [])
    row = rows[0] if rows else None
    return {'status': 'ok', 'property': property_name,
            'sitemap': [{'path': x.get('path'), 'errors': x.get('errors'), 'warnings': x.get('warnings'),
                         'isPending': x.get('isPending'), 'lastDownloaded': x.get('lastDownloaded')} for x in wanted],
            'performance': None if row is None else {key: row.get(key) for key in ('clicks', 'impressions', 'ctr', 'position')},
            'note': 'Только финализированные данные поиска web; отсутствие строк не означает нулевой трафик. Индексация не проверяется.'}


def yandex_snapshot(token, start, end, request=request_json):
    user = request(YANDEX_API + '/user', token, 'OAuth').get('user_id')
    if not isinstance(user, int) or isinstance(user, bool) or user < 1:
        raise SnapshotError('invalid user response')
    root = YANDEX_API + '/user/' + str(user) + '/hosts'
    hosts = request(root, token, 'OAuth').get('hosts', [])
    matching = [h for h in hosts if isinstance(h, dict) and h.get('ascii_host_url') == SITE and isinstance(h.get('host_id'), str)]
    if len(matching) != 1:
        raise SnapshotError('exact site host not found or ambiguous')
    host = matching[0]
    if host.get('verified') is not True:
        raise SnapshotError('site host is not verified')
    base = root + '/' + urllib.parse.quote(host['host_id'], safe='')
    maps = request(base + '/user-added-sitemaps?limit=100', token, 'OAuth')
    query = urllib.parse.urlencode([('query_indicator', 'TOTAL_SHOWS'), ('query_indicator', 'TOTAL_CLICKS'),
                                   ('date_from', start.isoformat()), ('date_to', end.isoformat())])
    history = request(base + '/search-queries/all/history?' + query, token, 'OAuth')
    return {'status': 'ok', 'host': SITE, 'verified': True,
            'sitemap_in_first_100': any(x.get('sitemap_url') == SITE + 'sitemap.xml' for x in maps.get('sitemaps', []) if isinstance(x, dict)),
            'sitemap_count': maps.get('count'), 'indicators': history.get('indicators', {}),
            'note': 'Список sitemap не подтверждает успешную обработку; показатели могут отсутствовать или поступать с задержкой.'}


def snapshot(tokens, start, end, request=request_json):
    result = {'created_utc': datetime.now(timezone.utc).isoformat(), 'site': SITE,
              'period': {'from': start.isoformat(), 'to': end.isoformat()}, 'sources': {}}
    for name, fn in [('google', google_snapshot), ('yandex', yandex_snapshot)]:
        token = tokens.get(name)
        if not token:
            result['sources'][name] = {'status': 'not_connected'}
            continue
        try:
            result['sources'][name] = fn(token, start, end, request)
        except (SnapshotError, TypeError, ValueError, AttributeError, KeyError):
            # Suppress provider data and token-bearing error messages.
            result['sources'][name] = {'status': 'error', 'message': 'Не удалось получить данные. Проверьте срок разрешения, права на сайт и подключение.'}
    return result


def main(argv=None):
    parser = argparse.ArgumentParser(description='Локальный снимок API вебмастеров; требуется отдельная настройка OAuth.')
    parser.add_argument('--days', type=int, default=28, help='Период до 90 дней; данные берутся с задержкой пять дней')
    args = parser.parse_args(argv)
    if not 1 <= args.days <= 90:
        parser.error('days must be 1..90')
    end = date.today() - timedelta(days=5)
    start = end - timedelta(days=args.days - 1)
    tokens = {'google': os.environ.pop('SCM_GOOGLE_WEBMASTER_TOKEN', ''),
              'yandex': os.environ.pop('SCM_YANDEX_WEBMASTER_TOKEN', '')}
    result = snapshot(tokens, start, end)
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0 if all(x['status'] == 'ok' for x in result['sources'].values()) else 1


if __name__ == '__main__':
    sys.exit(main())
