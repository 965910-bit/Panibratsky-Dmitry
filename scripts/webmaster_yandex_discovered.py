#!/usr/bin/env python3
"""Read whether Yandex robots detected the fixed sitemap; never write."""
import os
import re
import sys
import urllib.parse
from webmaster_actions import ActionError, YANDEX_API, SITE, MAP, api


def inspect(token, *, request=api):
    if not token:
        raise ActionError('not configured')
    uid = request(YANDEX_API + '/user', token, 'OAuth').get('user_id')
    if type(uid) is not int or uid < 1:
        raise ActionError('invalid user')
    root = YANDEX_API + '/user/' + str(uid) + '/hosts'
    hosts = request(root, token, 'OAuth').get('hosts')
    if not isinstance(hosts, list):
        raise ActionError('invalid hosts')
    hosts = [h for h in hosts if isinstance(h, dict) and h.get('ascii_host_url') == SITE and h.get('verified') is True and isinstance(h.get('host_id'), str) and h['host_id']]
    if len(hosts) != 1:
        raise ActionError('verified exact host unavailable')
    base = root + '/' + urllib.parse.quote(hosts[0]['host_id'], safe='')
    entries = request(base + '/sitemaps?limit=100', token, 'OAuth').get('sitemaps')
    if not isinstance(entries, list) or len(entries) > 100:
        raise ActionError('invalid sitemap list')
    found = [entry for entry in entries if isinstance(entry, dict) and entry.get('sitemap_url') == MAP]
    if len(found) > 1:
        raise ActionError('ambiguous sitemap')
    if not found:
        # This endpoint has no total count; do not infer global absence from one page.
        return {'state': 'not_found_in_first_page'}
    item = found[0]
    errors, urls, sources = item.get('errors_count'), item.get('urls_count'), item.get('sources')
    if (type(errors) is not int or errors < 0 or type(urls) is not int or urls < 0 or
        not isinstance(sources, list) or not all(isinstance(s, str) for s in sources)):
        raise ActionError('invalid sitemap information')
    known = sorted(set(s for s in sources if s in ('ROBOTS_TXT', 'WEBMASTER', 'INDEX_SITEMAP')))
    raw_date = item.get('last_access_date')
    date = raw_date[:10] if isinstance(raw_date, str) and re.match(r'^[0-9]{4}-[0-9]{2}-[0-9]{2}T', raw_date) else 'unknown'
    return {'state': 'found', 'errors': errors, 'urls': urls, 'sources': known, 'access_date': date}


def main():
    token = os.environ.pop('SCM_WM_YANDEX_ACCESS_TOKEN', '')
    try:
        result = inspect(token)
        if result['state'] == 'found':
            print('::notice title=Yandex robot sitemap::found; errors='+str(result['errors'])+'; urls='+str(result['urls'])+'; sources='+(','.join(result['sources']) or 'unknown')+'; access_date='+result['access_date'])
        else:
            print('::notice title=Yandex robot sitemap::not_found_in_first_page')
        print('Наличие карты у робота не гарантирует индексацию страниц.')
        return 0
    except Exception:
        print('Не удалось прочитать список карт, обнаруженных роботом Яндекса.', file=sys.stderr)
        return 1

if __name__ == '__main__':
    sys.exit(main())
