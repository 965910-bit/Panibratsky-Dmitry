#!/usr/bin/env python3
"""Read fixed, documented Yandex diagnostic statuses; no writes."""
import os
import sys
import urllib.parse
from webmaster_actions import ActionError, ApiError, NetworkError, YANDEX_API, SITE, api

CODES = ('DISALLOWED_IN_ROBOTS','DNS_ERROR','MAIN_PAGE_ERROR','THREATS',
         'SLOW_AVG_RESPONSE_TIME','SSL_CERTIFICATE_ERROR','ERROR_IN_ROBOTS_TXT',
         'ERRORS_IN_SITEMAPS','NO_SITEMAPS','NO_SITEMAP_MODIFICATIONS',
         'MAIN_MIRROR_IS_NOT_HTTPS','MAIN_PAGE_REDIRECTS','SOFT_404',
         'TOO_MANY_PAGE_DUPLICATES','DOCUMENTS_MISSING_DESCRIPTION','DOCUMENTS_MISSING_TITLE')
STATES = ('PRESENT','ABSENT','UNDEFINED')


def inspect(token, *, request=api):
    if not token: raise ActionError('not configured')
    uid=request(YANDEX_API+'/user',token,'OAuth').get('user_id')
    if type(uid) is not int or uid<1: raise ActionError('invalid user')
    root=YANDEX_API+'/user/'+str(uid)+'/hosts'
    hosts=request(root,token,'OAuth').get('hosts')
    if not isinstance(hosts,list): raise ActionError('invalid hosts')
    hosts=[h for h in hosts if isinstance(h,dict) and h.get('ascii_host_url')==SITE and h.get('verified') is True and isinstance(h.get('host_id'),str) and h['host_id']]
    if len(hosts)!=1: raise ActionError('verified exact host unavailable')
    problems=request(root+'/'+urllib.parse.quote(hosts[0]['host_id'],safe='')+'/diagnostics',token,'OAuth').get('problems')
    if not isinstance(problems,dict): raise ActionError('invalid diagnostics')
    result={}
    for code in CODES:
        entry=problems.get(code)
        if entry is None: result[code]='NOT_REPORTED'
        elif isinstance(entry,dict) and entry.get('state') in STATES: result[code]=entry['state']
        else: raise ActionError('invalid state')
    return result


def main():
    token=os.environ.pop('SCM_WM_YANDEX_ACCESS_TOKEN','')
    try:
        result=inspect(token)
        present=[name for name in CODES if result[name]=='PRESENT']
        unknown=sum(result[name] in ('UNDEFINED','NOT_REPORTED') for name in CODES)
        print('::notice title=Yandex site diagnostics::present='+(','.join(present) or 'none')+'; unknown_or_not_reported='+str(unknown))
        print('Статусы диагностики не доказывают индексацию.')
        return 0
    except ApiError as exc:
        status=str(exc.status) if type(exc.status) is int and 100 <= exc.status <= 599 else 'unknown'
        print('::error title=Yandex site diagnostics::http='+status)
        return 1
    except NetworkError:
        print('::error title=Yandex site diagnostics::network_error')
        return 1
    except ActionError as exc:
        allowed=('not configured','invalid user','invalid hosts','verified exact host unavailable','invalid diagnostics','invalid state')
        reason=str(exc) if str(exc) in allowed else 'unknown'
        print('::error title=Yandex site diagnostics::'+reason)
        return 1
    except Exception:
        print('Не удалось прочитать диагностику сайта Яндекса.',file=sys.stderr)
        return 1

if __name__ == '__main__':sys.exit(main())
