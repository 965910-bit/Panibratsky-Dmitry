#!/usr/bin/env python3
"""Read-only connection, sitemap presence and recrawl-quota diagnostic."""
import os
import sys
import urllib.parse
from webmaster_actions import ActionError, YANDEX_API, SITE, api, yandex_action


def inspect(token, *, request=api):
    if not token:
        raise ActionError('not configured')
    result=yandex_action(token, [], False, request=request)
    if result.get('sitemap') not in ('already_present','would_submit') or result.get('recrawl') != []:
        raise ActionError('invalid result')
    uid=request(YANDEX_API+'/user',token,'OAuth').get('user_id')
    if type(uid) is not int or uid < 1:
        raise ActionError('invalid user')
    root=YANDEX_API+'/user/'+str(uid)+'/hosts'
    hosts=request(root,token,'OAuth').get('hosts')
    if not isinstance(hosts,list):
        raise ActionError('invalid hosts')
    hosts=[h for h in hosts if isinstance(h,dict) and h.get('ascii_host_url')==SITE and h.get('verified') is True and isinstance(h.get('host_id'),str) and h['host_id']]
    if len(hosts)!=1:
        raise ActionError('verified exact host unavailable')
    quota=request(root+'/'+urllib.parse.quote(hosts[0]['host_id'],safe='')+'/recrawl/quota',token,'OAuth').get('quota_remainder')
    if type(quota) is not int or quota<0:
        raise ActionError('invalid quota')
    return {'verified':True,'sitemap':result['sitemap'],'quota_remaining':quota}


def main():
    token=os.environ.pop('SCM_WM_YANDEX_ACCESS_TOKEN','')
    try:
        result=inspect(token)
        print('::notice title=Yandex diagnostic::sitemap='+result['sitemap']+'; quota_remaining='+str(result['quota_remaining']))
        print('Подтверждённый сайт scm-news.ru: найден.')
        print('Sitemap: '+('уже добавлен' if result['sitemap']=='already_present' else 'не найден в полном списке добавленных карт.'))
        print('Остаток суточной квоты переобхода: '+str(result['quota_remaining'])+'.')
        print('Проверка только читает данные; отправка и индексация не проверены.')
        return 0
    except Exception:
        print('Проверка Яндекс Вебмастера не завершена; проверьте доступ и права. Секреты не выводятся.',file=sys.stderr)
        return 1


if __name__=='__main__':sys.exit(main())
