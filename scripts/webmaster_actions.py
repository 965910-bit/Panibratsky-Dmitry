#!/usr/bin/env python3
"""Guarded write actions for existing webmaster properties; no credentials or scheduler.

Dry-run by default. --apply submits ONLY the fixed sitemap and selected canonical URLs.
There is no blind retry on ambiguous network errors and no guarantee of indexing.
"""
import argparse
import json
import os
import re
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from generate_sitemap import BASE, PAGES
from indexnow_submit import validate_live
from webmaster_readonly import GOOGLE_API, YANDEX_API, SITE, DOMAIN_PROPERTY

MAP = SITE + 'sitemap.xml'
MAX_URLS = 5
TASK_ID = re.compile(r'[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12}\Z')
MAX_RESPONSE = 2 * 1024 * 1024
# The provider currently reports its Sitemap tool as read-only (owner screenshot).
# Change only after independently confirming recovery and reconciling unknown writes.
SITEMAP_WRITES_PAUSED = True


class ActionError(Exception):
    pass


class ApiError(ActionError):
    def __init__(self, status, code=None, retry_after=None):
        super().__init__('API HTTP ' + str(status))
        self.status, self.code, self.retry_after = status, code, retry_after


class NetworkError(ActionError):
    pass


class NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return None


def _api_once(url, token, scheme, method='GET', body=None):
    if not (url.startswith(GOOGLE_API + '/') or url.startswith(YANDEX_API + '/')):
        raise ActionError('invalid endpoint')
    if not token or '\r' in token or '\n' in token or method not in ('GET', 'POST', 'PUT'):
        raise ActionError('invalid request')
    data = json.dumps(body).encode('utf-8') if body is not None else None
    headers = {'Authorization': scheme + ' ' + token, 'Accept': 'application/json'}
    if data is not None:
        headers['Content-Type'] = 'application/json'
    req = urllib.request.Request(url, data=data, headers=headers, method=method)
    try:
        with urllib.request.build_opener(NoRedirect).open(req, timeout=20) as resp:
            content = resp.read(MAX_RESPONSE + 1)
        if len(content) > MAX_RESPONSE:
            raise ActionError('response too large')
        result = json.loads(content) if content else {}
        if not isinstance(result, dict):
            raise ActionError('invalid response')
        return result
    except urllib.error.HTTPError as exc:
        code = None
        # Only recognise provider error codes we explicitly handle; never print body.
        try:
            body = json.loads(exc.read(4096))
            if isinstance(body, dict) and body.get('error_code') in ('SITEMAP_ALREADY_ADDED', 'URL_ALREADY_ADDED', 'QUOTA_EXCEEDED'):
                code = body['error_code']
        except (ValueError, OSError):
            pass
        # A server-provided delay that is invalid or too long must not be ignored.
        value = exc.headers.get('Retry-After') if exc.headers else None
        if value is None:
            retry_after = None
        elif value.isascii() and value.isdigit() and len(value) <= 6:
            retry_after = int(value)
        else:
            retry_after = -1
        raise ApiError(exc.code, code, retry_after) from None
    except (urllib.error.URLError, TimeoutError, OSError):
        raise NetworkError('network error; outcome may be unknown') from None
    except (UnicodeError, json.JSONDecodeError):
        raise ActionError('invalid response; outcome may be unknown') from None


def api(url, token, scheme, method='GET', body=None):
    """Bounded retries for GET only; never repeat an ambiguous write."""
    for attempt in range(3):
        try:
            return _api_once(url, token, scheme, method, body)
        except (ApiError, NetworkError) as exc:
            if method != 'GET' or body is not None or attempt == 2:
                raise
            delay = attempt + 1
            if isinstance(exc, ApiError):
                if exc.status not in (429, 500, 502, 503, 504):
                    raise
                if exc.retry_after is not None:
                    if exc.retry_after < 0 or exc.retry_after > 5:
                        raise
                    delay = max(delay, exc.retry_after)
            time.sleep(delay)


def allowed_urls(urls):
    if len(urls) > MAX_URLS or len(set(urls)) != len(urls):
        raise ActionError('at most five distinct URLs')
    allowed = {BASE + name for name in PAGES}
    if any(url not in allowed for url in urls):
        raise ActionError('URL not in canonical sitemap allowlist')
    return urls


def google_action(token, apply, request=api):
    response = request(GOOGLE_API + '/sites', token, 'Bearer')
    entries = response.get('siteEntry', []) if isinstance(response,dict) else None
    if not isinstance(entries,list) or any(not isinstance(x,dict) or not isinstance(x.get('siteUrl'),str) for x in entries):
        raise ActionError('invalid Google properties')
    matching = [x for x in entries if x['siteUrl'] in (SITE,DOMAIN_PROPERTY)]
    if len({x['siteUrl'] for x in matching}) != len(matching):
        raise ActionError('ambiguous Google properties')
    selected = next((x for x in matching if x['siteUrl']==SITE),None)
    if selected is None:
        selected = next((x for x in matching if x['siteUrl']==DOMAIN_PROPERTY),None)
    if selected is None:
        raise ActionError('Google property missing')
    if selected.get('permissionLevel') not in ('siteOwner','siteFullUser'):
        raise ActionError('Google property lacks full permission')
    prop = selected['siteUrl']
    base = GOOGLE_API + '/sites/' + urllib.parse.quote(prop, safe='')
    response = request(base + '/sitemaps', token, 'Bearer')
    maps = response.get('sitemap', []) if isinstance(response,dict) else None
    if not isinstance(maps,list) or any(not isinstance(x,dict) or not isinstance(x.get('path'),str) for x in maps):
        raise ActionError('invalid Google sitemap list')
    if any(item['path'] == MAP for item in maps):
        return {'status': 'already_present', 'property': prop}
    if not apply:
        return {'status': 'would_submit', 'property': prop}
    request(base + '/sitemaps/' + urllib.parse.quote(MAP, safe=''), token, 'Bearer', method='PUT')
    return {'status': 'submitted', 'property': prop}


def yandex_action(token, urls, apply, request=api, *, manage_sitemap=True):
    if type(manage_sitemap) is not bool:
        raise ActionError('invalid sitemap mode')
    allowed_urls(urls)
    uid = request(YANDEX_API + '/user', token, 'OAuth').get('user_id')
    if type(uid) is not int or uid < 1:
        raise ActionError('invalid user')
    root = YANDEX_API + '/user/' + str(uid) + '/hosts'
    hosts = request(root, token, 'OAuth').get('hosts', [])
    hosts = [x for x in hosts if isinstance(x, dict) and x.get('ascii_host_url') == SITE and isinstance(x.get('host_id'), str)]
    if len(hosts) != 1 or hosts[0].get('verified') is not True:
        raise ActionError('verified exact host unavailable')
    base = root + '/' + urllib.parse.quote(hosts[0]['host_id'], safe='')
    sitemap = 'not_checked'
    if manage_sitemap:
        maps = request(base + '/user-added-sitemaps?limit=100', token, 'OAuth')
        listed = maps.get('sitemaps')
        count = maps.get('count')
        if not isinstance(listed, list) or type(count) is not int or count < 0:
            raise ActionError('invalid sitemap list')
        present = any(isinstance(item, dict) and item.get('sitemap_url') == MAP for item in listed)
        if not present and count > len(listed):
            raise ActionError('sitemap list incomplete; no write')
        sitemap = 'already_present' if present else 'would_submit'
        if not present and apply:
            if SITEMAP_WRITES_PAUSED:
                raise ActionError('Yandex sitemap writes paused; no submission attempted')
            try:
                response = request(base + '/user-added-sitemaps', token, 'OAuth', method='POST', body={'url': MAP})
                if not isinstance(response, dict) or not isinstance(response.get('sitemap_id'), str) or not response['sitemap_id']:
                    raise ActionError('invalid response; submission outcome unknown')
                sitemap = 'submitted'
            except ApiError as exc:
                if exc.status == 409 and exc.code == 'SITEMAP_ALREADY_ADDED':
                    sitemap = 'already_present'
                else:
                    raise
    results = []
    if urls:
        quota = request(base + '/recrawl/quota', token, 'OAuth').get('quota_remainder')
        if type(quota) is not int or quota < 0:
            raise ActionError('invalid quota')
        for url in urls:
            if quota == 0:
                results.append({'url': url, 'status': 'quota_exhausted'})
                continue
            if not apply:
                results.append({'url': url, 'status': 'would_submit'})
                quota -= 1
                continue
            try:
                response = request(base + '/recrawl/queue', token, 'OAuth', method='POST', body={'url': url})
                task, remaining = response.get('task_id'), response.get('quota_remainder')
                if not isinstance(task, str) or not TASK_ID.fullmatch(task) or type(remaining) is not int or remaining < 0:
                    raise ActionError('invalid response; submission outcome unknown')
                results.append({'url': url, 'status': 'accepted', 'task_id': task})
                quota = remaining
            except ApiError as exc:
                if exc.status == 409 and exc.code == 'URL_ALREADY_ADDED':
                    results.append({'url': url, 'status': 'already_added'})
                elif exc.status == 429 and exc.code == 'QUOTA_EXCEEDED':
                    quota = 0
                    results.append({'url': url, 'status': 'quota_exhausted'})
                else:
                    raise
    return {'sitemap': sitemap, 'recrawl': results}


def main(argv=None):
    parser = argparse.ArgumentParser(description='Sitemap и переобход: по умолчанию только план.')
    parser.add_argument('--apply', action='store_true', help='разрешить фактическую отправку')
    parser.add_argument('--url', action='append', default=[], help='канонический URL изменённой страницы (до 5)')
    args = parser.parse_args(argv)
    tokens = {'google': os.environ.pop('SCM_GOOGLE_WEBMASTER_TOKEN', ''), 'yandex': os.environ.pop('SCM_YANDEX_WEBMASTER_TOKEN', '')}
    output = {'mode': 'apply' if args.apply else 'dry-run', 'sources': {}}
    try:
        allowed_urls(args.url)
        # Reuse the same deployed-byte, sitemap, canonical, robots and key checks as IndexNow.
        if args.apply and any(tokens.values()):
            validate_live(args.url)
    except Exception:
        # A failed preflight is always a stop, including malformed live XML.
        print('Проверка опубликованных страниц не пройдена. Изменений не выполняли.', file=sys.stderr)
        return 1
    for name, action in (('google', lambda t: google_action(t, args.apply)),
                         ('yandex', lambda t: yandex_action(t, args.url, args.apply))):
        if not tokens[name]:
            output['sources'][name] = {'status': 'not_connected'}
            continue
        try:
            output['sources'][name] = {'status': 'ok', 'result': action(tokens[name])}
        except (ActionError, ValueError, TypeError, KeyError, AttributeError):
            output['sources'][name] = {'status': 'error', 'message': 'Операция не завершена; состояние на стороне сервиса может быть неизвестно. Проверьте кабинет перед повтором.'}
    print(json.dumps(output, ensure_ascii=False, indent=2))
    return 0 if all(x['status'] == 'ok' for x in output['sources'].values()) else 1


if __name__ == '__main__':
    sys.exit(main())
