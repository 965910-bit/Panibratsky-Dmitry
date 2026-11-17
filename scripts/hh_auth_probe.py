"""One read-only HH vacancy request using an existing application access token.

No token issuance, retries, redirects, analytics writes, or publication.
"""
import getpass
import http.client
import json
import os
import re
import sys
from urllib.parse import urlencode

HOST = 'api.hh.ru'
USER_AGENT = 'DmitryGerasimovBot/1.0 (dmitry.gerasimov.2026@yandex.ru)'
MAX_BODY = 131072
CATEGORIES = {'captcha_required', 'bad_authorization', 'token_expired', 'token_revoked',
              'application_not_found', 'user_auth_expected', 'api_access_payment'}


def probe(token, connection_factory=http.client.HTTPSConnection):
    if not isinstance(token, str) or not re.fullmatch(r'[A-Za-z0-9._~+/-]{1,2048}={0,2}', token):
        return 'invalid_token_format'
    connection = None
    try:
        connection = connection_factory(HOST, timeout=20)
        path = '/vacancies?' + urlencode({'text': 'склад', 'per_page': 1, 'page': 0})
        connection.request('GET', path, headers={'User-Agent': USER_AGENT, 'Accept': 'application/json',
                                                 'Authorization': 'Bearer ' + token})
        response = connection.getresponse()
        status = response.status
        if status != 200:
            # Do not follow redirects or publish arbitrary error text, URLs, or headers.
            category = None
            raw = response.read(MAX_BODY + 1)
            if len(raw) <= MAX_BODY:
                try:
                    body = json.loads(raw)
                    errors = body.get('errors') if isinstance(body, dict) else None
                    if isinstance(errors, list):
                        for item in errors[:20]:
                            if isinstance(item, dict):
                                for key in ('value', 'type'):
                                    value = item.get(key)
                                    if isinstance(value, str) and value in CATEGORIES:
                                        category = value
                                        break
                            if category:
                                break
                except (ValueError, UnicodeError):
                    pass
            code = str(status) if type(status) is int and 100 <= status <= 599 else 'unknown'
            return 'http=' + code + ((' api_error=' + category) if category else '')
        raw = response.read(MAX_BODY + 1)
        if len(raw) > MAX_BODY:
            return 'invalid_response'
        try:
            body = json.loads(raw)
        except (ValueError, UnicodeError):
            return 'invalid_response'
        if not isinstance(body, dict) or not isinstance(body.get('items'), list) or type(body.get('found')) is not int or body['found'] < 0:
            return 'invalid_response'
        return 'ok'
    except Exception:
        # Exceptions may contain request details; never print them.
        return 'network_error'
    finally:
        if connection is not None:
            try:
                connection.close()
            except Exception:
                pass


def main():
    if sys.argv[1:] != ['--confirm-read-only']:
        print('Use --confirm-read-only to send one vacancy search request.', file=sys.stderr)
        return 2
    token = os.environ.get('HH_APP_ACCESS_TOKEN')
    if token is None:
        try:
            token = getpass.getpass('HH application access token (input hidden): ')
        except (EOFError, KeyboardInterrupt):
            print('Token input cancelled.', file=sys.stderr)
            return 2
    result = probe(token)
    print('HH read-only probe: ' + result)
    return 0 if result == 'ok' else 1


if __name__ == '__main__':
    sys.exit(main())
