#!/usr/bin/env python3
"""Interactive Yandex OAuth device setup, on the owner's computer only.

Stores a scoped access token in GitHub Actions secrets via gh stdin; never
prints token, device code, client secret or error response. Does not enable jobs.
"""
import getpass
import json
import re
import subprocess
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
import webbrowser

from webmaster_google_connect import REPOSITORY_ID
from webmaster_readonly import YANDEX_API, SITE, request_json, SnapshotError

DEVICE = 'https://oauth.yandex.ru/device/code'
TOKEN = 'https://oauth.yandex.ru/token'
VERIFY = 'https://oauth.yandex.ru/device'
SCOPES = 'webmaster:hostinfo webmaster:verify'
SECRET_NAME = 'SCM_WM_YANDEX_ACCESS_TOKEN'
MAX_BYTES = 16384


class SetupError(Exception):
    pass


class NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return None


def oauth_request(endpoint, fields):
    if endpoint not in (DEVICE, TOKEN):
        raise SetupError('Некорректный адрес авторизации.')
    data = urllib.parse.urlencode(fields).encode('utf-8')
    req = urllib.request.Request(endpoint, data=data, method='POST', headers={'Content-Type':'application/x-www-form-urlencoded','Accept':'application/json'})
    try:
        try:
            with urllib.request.build_opener(NoRedirect).open(req, timeout=20) as response:
                raw = response.read(MAX_BYTES + 1)
        except urllib.error.HTTPError as exc:
            # Only an OAuth error object is considered; never print its body.
            if exc.code != 400:
                raise SetupError('Ошибка связи с Яндекс OAuth.') from None
            raw = exc.read(MAX_BYTES + 1)
        if len(raw) > MAX_BYTES:
            raise SetupError('Некорректный ответ Яндекса.')
        value = json.loads(raw)
        if not isinstance(value, dict):
            raise SetupError('Некорректный ответ Яндекса.')
        return value
    except (urllib.error.URLError, TimeoutError, OSError, UnicodeError, ValueError):
        raise SetupError('Не удалось получить ответ Яндекс OAuth.') from None


def request_device(cid, request=oauth_request):
    data = request(DEVICE, {'client_id':cid, 'scope':SCOPES})
    device, user = data.get('device_code'), data.get('user_code')
    interval, expires = data.get('interval'), data.get('expires_in')
    if (not isinstance(device,str) or not 1 <= len(device) <= 2048 or
        not isinstance(user,str) or not re.fullmatch(r'[A-Za-z0-9-]{4,32}', user) or
        data.get('verification_url') not in (VERIFY, 'https://oauth.yandex.com/device') or type(interval) is not int or not 1 <= interval <= 60 or
        type(expires) is not int or not 1 <= expires <= 900):
        raise SetupError('Не удалось начать безопасную авторизацию Яндекса.')
    return device, user, interval, expires


def wait_for_token(cid, secret, device, interval, expires, request=oauth_request, clock=time.monotonic, sleep=time.sleep):
    deadline = clock() + expires
    delay = interval
    while clock() + delay < deadline:
        sleep(delay)
        data = request(TOKEN, {'grant_type':'device_code','code':device,'client_id':cid,'client_secret':secret})
        if data.get('error') == 'authorization_pending':
            continue
        if data.get('error') == 'slow_down':
            delay += 5
            continue
        if data.get('error'):
            raise SetupError('Авторизация Яндекса отклонена или недоступна.')
        token = data.get('access_token')
        scope = data.get('scope')
        if scope is not None and (not isinstance(scope,str) or not set(SCOPES.split()).issubset(set(scope.split()))):
            raise SetupError('Яндекс не предоставил необходимые права.')
        if not isinstance(token,str) or not token or '\n' in token or '\r' in token:
            raise SetupError('Яндекс не предоставил токен доступа.')
        # Refresh token is intentionally not persisted; automatic rotation is not implemented.
        return token
    raise SetupError('Время авторизации истекло.')


def verify_site(token, request=request_json):
    uid = request(YANDEX_API + '/user', token, 'OAuth').get('user_id')
    if type(uid) is not int or uid < 1:
        raise SetupError('Не удалось проверить учётную запись Яндекса.')
    hosts = request(YANDEX_API + '/user/' + str(uid) + '/hosts', token, 'OAuth').get('hosts', [])
    matching = [h for h in hosts if isinstance(h,dict) and h.get('ascii_host_url') == SITE and h.get('verified') is True]
    if len(matching) != 1:
        raise SetupError('Подтверждённый сайт не найден в этом аккаунте Яндекса.')


def gh_check():
    try:
        p = subprocess.run(['gh','api',f'repositories/{REPOSITORY_ID}','--jq','.full_name'], capture_output=True, text=True, timeout=30, check=True)
        repo = p.stdout.strip()
        if not re.fullmatch(r'[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+', repo):
            raise SetupError('Не удалось определить репозиторий.')
        p = subprocess.run(['gh','secret','list','--repo',repo], capture_output=True, text=True, timeout=30, check=True)
        names = {line.split('\t',1)[0].strip() for line in p.stdout.splitlines() if line.strip()}
        if SECRET_NAME in names:
            raise SetupError('Секрет уже существует. Перезапись не выполняется.')
        return repo
    except (OSError, subprocess.SubprocessError):
        raise SetupError('Не удалось проверить доступ GitHub CLI к репозиторию.') from None


def gh_store(repo, token):
    try:
        subprocess.run(['gh','secret','set',SECRET_NAME,'--repo',repo], input=token.encode('utf-8'), stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, timeout=30, check=True)
    except (OSError, subprocess.SubprocessError):
        raise SetupError('Не удалось подтвердить сохранение секрета GitHub.') from None


def main():
    print('Подключение Яндекс Вебмастера к GitHub Actions для scm-news.ru.')
    print('Права webmaster:hostinfo и webmaster:verify могут разрешать изменения в Вебмастере, включая управление сайтом.')
    print('Секрет OAuth-приложения вводится локально; пароль Яндекс ID и коды в чат не отправляйте.')
    try:
        if input('Продолжить? Введите ДА: ').strip().upper() != 'ДА':
            print('Отменено. Изменений не выполняли.')
            return 0
        repo = gh_check()
        cid = input('ID приложения Яндекс OAuth: ').strip()
        secret = getpass.getpass('Секрет приложения Яндекс OAuth (не пароль Яндекс ID): ')
        if not cid or not secret or any(x in cid+secret for x in '\r\n'):
            raise SetupError('Не заполнены данные приложения.')
        device, user, interval, expires = request_device(cid)
        print('Откройте официальную страницу Яндекса и введите показанный ниже одноразовый код только там.')
        print(VERIFY)
        print('Код для Яндекса: ' + user)
        if not webbrowser.open(VERIFY):
            print('Браузер не открылся. Введите адрес выше вручную на этом устройстве.')
        token = wait_for_token(cid, secret, device, interval, expires)
        verify_site(token)
        gh_store(repo, token)
        print('Доступ сохранён в GitHub Secrets, сайт подтверждён. Автоматизация остаётся выключенной.')
        print('Автообновление токена не настроено; при истечении понадобится повторное подключение.')
        return 0
    except (SetupError, SnapshotError, EOFError, KeyboardInterrupt, OSError):
        print('Подключение не завершено. Проверьте приложение Яндекса, права на сайт и доступ к GitHub. Секрет мог быть создан при сбое ответа.')
        return 1


if __name__ == '__main__':
    sys.exit(main())
