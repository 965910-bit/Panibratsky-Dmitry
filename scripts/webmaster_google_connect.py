#!/usr/bin/env python3
"""Google desktop OAuth onboarding: loopback, PKCE, secrets via gh stdin.

Run only on the account owner's own computer after creating a Google Desktop
OAuth client. Never prints tokens or OAuth codes. Does not enable automation.
"""
import base64
import hashlib
import hmac
import json
import re
from pathlib import Path
import secrets
import subprocess
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
import webbrowser
from http.server import BaseHTTPRequestHandler, HTTPServer

REPOSITORY_ID = 1102759388
SCOPE = 'https://www.googleapis.com/auth/webmasters'
AUTH = 'https://accounts.google.com/o/oauth2/v2/auth'
TOKEN = 'https://oauth2.googleapis.com/token'
SECRET_NAMES = ('SCM_WM_GOOGLE_CLIENT_ID', 'SCM_WM_GOOGLE_CLIENT_SECRET', 'SCM_WM_GOOGLE_REFRESH_TOKEN')
TIMEOUT = 180


class SetupError(Exception):
    pass


class NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return None


def pkce():
    verifier = secrets.token_urlsafe(48)
    digest = hashlib.sha256(verifier.encode('ascii')).digest()
    challenge = base64.urlsafe_b64encode(digest).rstrip(b'=').decode('ascii')
    return verifier, challenge


def load_desktop_client(path):
    try:
        if Path(path).stat().st_size > 65536:
            raise SetupError('bad client')
        data = json.loads(Path(path).read_text(encoding='utf-8-sig'))
        client = data.get('installed', {})
        cid, secret = client.get('client_id'), client.get('client_secret')
        if not isinstance(cid, str) or not isinstance(secret, str) or not cid or not secret:
            raise SetupError('bad client')
        if client.get('auth_uri') not in (AUTH, 'https://accounts.google.com/o/oauth2/auth') or client.get('token_uri') != TOKEN:
            raise SetupError('unexpected endpoints')
        return cid, secret
    except (OSError, UnicodeError, ValueError, AttributeError):
        raise SetupError('Не удалось прочитать файл Desktop OAuth приложения Google.') from None


def auth_url(cid, redirect, state, challenge):
    query = urllib.parse.urlencode({'client_id':cid, 'redirect_uri':redirect, 'response_type':'code',
        'scope':SCOPE, 'state':state, 'code_challenge':challenge, 'code_challenge_method':'S256',
        'access_type':'offline', 'prompt':'consent'})
    return AUTH + '?' + query


def parse_callback(target, state):
    parsed = urllib.parse.urlsplit(target)
    if parsed.path != '/callback' or parsed.scheme or parsed.netloc or len(target) > 8192:
        return None
    q = urllib.parse.parse_qs(parsed.query, keep_blank_values=True)
    if len(q.get('state', [])) != 1 or not hmac.compare_digest(q['state'][0], state):
        return None
    if q.get('error'):
        raise SetupError('Разрешение отклонено или Google вернул ошибку.')
    codes = q.get('code', [])
    return codes[0] if len(codes) == 1 and 0 < len(codes[0]) <= 4096 else None


def receive_code(cid, state, challenge, timeout=TIMEOUT):
    class Handler(BaseHTTPRequestHandler):
        def setup(self):
            super().setup()
            self.connection.settimeout(5)
        def log_message(self, fmt, *args):
            pass  # OAuth code and state must not reach logs.
        def do_GET(self):
            try:
                code = parse_callback(self.path, state)
            except SetupError:
                self.server.denied = True
                code = None
            if code:
                self.server.code = code
            body = ('Разрешение получено. Вернитесь в окно настройки.' if code else 'Запрос отклонён или неверен.').encode('utf-8')
            self.send_response(200 if code else 400)
            self.send_header('Content-Type','text/plain; charset=utf-8')
            self.send_header('Cache-Control','no-store')
            self.send_header('Referrer-Policy','no-referrer')
            self.send_header('Content-Length', str(len(body)))
            self.end_headers()
            self.wfile.write(body)
    # Listener is strictly loopback, not reachable from the LAN.
    with HTTPServer(('127.0.0.1', 0), Handler) as server:
        server.timeout = 1
        server.code = None
        server.denied = False
        redirect = 'http://127.0.0.1:' + str(server.server_port) + '/callback'
        if not webbrowser.open(auth_url(cid, redirect, state, challenge)):
            raise SetupError('Не удалось открыть браузер.')
        deadline = time.monotonic() + timeout
        while not server.code and not server.denied and time.monotonic() < deadline:
            server.handle_request()
        if not server.code:
            raise SetupError('Подключение отменено или время ожидания истекло.')
        return server.code, redirect


def exchange(code, redirect, cid, secret, verifier):
    data = urllib.parse.urlencode({'code':code, 'client_id':cid, 'client_secret':secret,
        'redirect_uri':redirect, 'grant_type':'authorization_code', 'code_verifier':verifier}).encode('utf-8')
    req = urllib.request.Request(TOKEN, data=data, method='POST', headers={'Content-Type':'application/x-www-form-urlencoded','Accept':'application/json'})
    try:
        with urllib.request.build_opener(NoRedirect).open(req, timeout=20) as r:
            raw = r.read(16385)
        if len(raw) > 16384:
            raise SetupError('Некорректный ответ Google.')
        data = json.loads(raw)
        refresh = data.get('refresh_token') if isinstance(data, dict) else None
        granted = data.get('scope') if isinstance(data, dict) else None
        if granted is not None and (not isinstance(granted, str) or SCOPE not in granted.split()):
            raise SetupError('Google не предоставил необходимые права.')
        if not isinstance(refresh, str) or not refresh or '\n' in refresh or '\r' in refresh:
            raise SetupError('Google не предоставил refresh-токен; автоматический доступ не готов.')
        return refresh
    except (urllib.error.URLError, TimeoutError, OSError, ValueError):
        raise SetupError('Не удалось завершить авторизацию Google.') from None


def gh_check():
    try:
        # Resolve the immutable repository ID; never select a repository from a user-supplied URL.
        p = subprocess.run(['gh','api',f'repositories/{REPOSITORY_ID}','--jq','.full_name'], capture_output=True, text=True, timeout=30, check=True)
        repo = p.stdout.strip()
        if not re.fullmatch(r'[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+', repo):
            raise SetupError('Не удалось определить целевой репозиторий.')
        p = subprocess.run(['gh','secret','list','--repo',repo], capture_output=True, text=True, timeout=30, check=True)
        existing = {line.split('\t',1)[0].strip() for line in p.stdout.splitlines() if line.strip()}
        if existing.intersection(SECRET_NAMES):
            raise SetupError('Один или несколько секретов уже существуют. Автоматическая перезапись запрещена.')
        return repo
    except (OSError, subprocess.SubprocessError):
        raise SetupError('Не удалось проверить GitHub CLI и доступ к секретам репозитория.') from None


def gh_store(repo, cid, secret, refresh):
    done = 0
    for name, value in zip(SECRET_NAMES, (cid, secret, refresh)):
        try:
            subprocess.run(['gh','secret','set',name,'--repo',repo], input=value.encode('utf-8'),
                           stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, timeout=30, check=True)
            done += 1
        except (OSError, subprocess.SubprocessError):
            raise SetupError('Сохранение не завершилось. Возможно, часть секретов уже создана; проверьте настройки GitHub.') from None
    return done


def main(argv=None):
    args = sys.argv[1:] if argv is None else argv
    if len(args) != 1:
        print('Запуск: python scripts/webmaster_google_connect.py ПУТЬ_К_DESKTOP_OAUTH_JSON')
        return 2
    print('Подключение Google Search Console к GitHub Actions для scm-news.ru.')
    print('Будет запрошен доступ webmasters: он позволяет изменять данные Search Console, не только читать их.')
    print('Программа сохранит три секрета в репозитории. Она НЕ включает автоматизацию.')
    print('Не публикуйте файл OAuth, токены и коды; после настройки защитите или удалите скачанный JSON.')
    try:
        answer = input('Продолжить? Введите ДА: ').strip().upper()
    except (EOFError, KeyboardInterrupt):
        print('Отменено. Изменений не выполняли.')
        return 0
    if answer != 'ДА':
        print('Отменено. Изменений не выполняли.')
        return 0
    try:
        cid, secret = load_desktop_client(args[0])
        repo = gh_check()
        verifier, challenge = pkce()
        state = secrets.token_urlsafe(32)
        print('Откроется официальный сайт Google. Разрешите доступ и вернитесь в это окно.')
        code, redirect = receive_code(cid, state, challenge)
        refresh = exchange(code, redirect, cid, secret, verifier)
        gh_store(repo, cid, secret, refresh)
        print('Данные подключения Google сохранены в секретах GitHub. Автоматизация по-прежнему выключена.')
        print('Работа с реальным сайтом не проверена; включение будет отдельным шагом после проверки.')
        return 0
    except (SetupError, OSError, EOFError, KeyboardInterrupt):
        print('Не удалось завершить подключение. Проверьте настройки Google и GitHub; возможно, часть секретов уже создана.')
        return 1


if __name__ == '__main__':
    sys.exit(main())
