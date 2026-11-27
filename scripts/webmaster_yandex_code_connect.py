#!/usr/bin/env python3
"""Yandex verification_code OAuth with PKCE on the owner's computer only.

No client secret required. Does not enable automation or store a refresh token.
"""
import getpass
import re
import sys
import urllib.parse
import webbrowser
from webmaster_google_connect import pkce
from webmaster_yandex_connect import (SetupError, SnapshotError, SCOPES, TOKEN,
                                      gh_check, gh_store, verify_site, oauth_request)

AUTH = 'https://oauth.yandex.ru/authorize'
REDIRECT = 'https://oauth.yandex.ru/verification_code'


def build_auth_url(client_id, challenge):
    if not re.fullmatch(r'[a-fA-F0-9]{32}',client_id or ''):
        raise SetupError('Некорректный ID приложения.')
    if not re.fullmatch(r'[A-Za-z0-9_-]{43}',challenge or ''):
        raise SetupError('Не удалось подготовить защищённый запрос.')
    query=urllib.parse.urlencode({'response_type':'code', 'client_id':client_id,
        'redirect_uri':REDIRECT, 'scope':SCOPES,
        'code_challenge':challenge,'code_challenge_method':'S256'})
    return AUTH+'?'+query


def exchange(client_id, code, verifier, *, request=oauth_request):
    if not re.fullmatch(r'[A-Za-z0-9_-]{4,512}',code or ''):
        raise SetupError('Некорректный код подтверждения.')
    response=request(TOKEN, {'grant_type':'authorization_code','code':code,
                             'client_id':client_id,'code_verifier':verifier})
    error=response.get('error')
    safe_errors={'invalid_client','invalid_request','invalid_grant','invalid_scope','unauthorized_client','unsupported_grant_type'}
    if error:
        if isinstance(error,str) and error in safe_errors:
            raise SetupError('Яндекс не выдал доступ: '+error+'.')
        raise SetupError('Яндекс не выдал доступ.')
    scope=response.get('scope')
    if scope is not None and (not isinstance(scope,str) or not set(SCOPES.split()).issubset(set(scope.split()))):
        raise SetupError('Яндекс предоставил недостаточно прав.')
    token=response.get('access_token')
    if not isinstance(token,str) or not token or '\n' in token or '\r' in token:
        raise SetupError('Яндекс не выдал токен доступа.')
    return token


def main():
    print('Подключение Яндекс Вебмастера к GitHub Actions для scm-news.ru.')
    print('Права webmaster:hostinfo и webmaster:verify могут разрешать изменения в Вебмастере, включая управление сайтом.')
    try:
        if input('Продолжить? Введите ДА: ').strip().upper() != 'ДА':
            print('Отменено. Изменений не выполняли.');return 0
        repo=gh_check()
        cid=input('ClientID приложения Яндекс OAuth: ').strip()
        verifier,challenge=pkce()
        url=build_auth_url(cid,challenge)
        print('Откроется официальный сайт Яндекса. Подтвердите доступ и перенесите показанный код в это окно.')
        if not webbrowser.open(url):
            print('Браузер не открылся. Откройте эту ссылку вручную: '+url)
        code=getpass.getpass('Код подтверждения со страницы Яндекса (не пароль): ').strip()
        token=exchange(cid,code,verifier)
        verify_site(token)
        gh_store(repo,token)
        print('Доступ сохранён в GitHub Secrets; сайт подтверждён. Автоматизация остаётся выключенной.')
        print('Автообновление токена не настроено.')
        return 0
    except SetupError as exc:
        print(str(exc)+' Подключение не завершено; секрет мог быть создан при сбое ответа.')
        return 1
    except (SnapshotError,EOFError,KeyboardInterrupt,OSError):
        print('Подключение не завершено. Проверьте доступ к Яндексу и GitHub; секрет мог быть создан при сбое ответа.')
        return 1


if __name__=='__main__':
    sys.exit(main())
