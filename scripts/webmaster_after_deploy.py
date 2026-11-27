#!/usr/bin/env python3
"""Run guarded webmaster actions after a verified production Pages deployment.

Disabled unless SCM_WEBMASTER_AUTOMATION=1. Never print credentials. No blind
retries after partial/ambiguous provider writes; this is not a durable queue.
"""
import json
import os
import re
import subprocess
import sys
import urllib.error
import urllib.parse
import urllib.request

import indexnow_submit as ix
from webmaster_actions import ActionError, google_action, yandex_action

GOOGLE_TOKEN_URL = 'https://oauth2.googleapis.com/token'


def refresh_google(client_id, client_secret, refresh_token):
    if not all((client_id, client_secret, refresh_token)):
        raise ActionError('incomplete Google OAuth configuration')
    data = urllib.parse.urlencode({'client_id': client_id, 'client_secret': client_secret,
                                   'refresh_token': refresh_token, 'grant_type': 'refresh_token'}).encode()
    req = urllib.request.Request(GOOGLE_TOKEN_URL, data=data, method='POST',
                                 headers={'Content-Type': 'application/x-www-form-urlencoded', 'Accept': 'application/json'})
    try:
        with urllib.request.build_opener(ix.NoRedirect).open(req, timeout=20) as response:
            raw = response.read(16385)
        if len(raw) > 16384:
            raise ActionError('invalid OAuth response')
        payload = json.loads(raw)
        token = payload.get('access_token') if isinstance(payload, dict) else None
        if not isinstance(token, str) or not token or '\n' in token or '\r' in token:
            raise ActionError('invalid OAuth response')
        return token
    except (urllib.error.URLError, TimeoutError, OSError, ValueError):
        raise ActionError('Google OAuth refresh failed') from None


def build_plan(event, repo, github_token, *, fetch=ix.request, git=ix.git, ancestry=subprocess.run):
    if not re.fullmatch(r'[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+', repo):
        raise ActionError('invalid repository')
    current = event.get('workflow_run', {})
    sha = current.get('head_sha', '')
    if (event.get('action') != 'completed' or current.get('head_branch') != 'main'
            or current.get('conclusion') != 'success' or current.get('run_attempt', 1) != 1
            or not re.fullmatch(r'[a-f0-9]{40}', sha) or git('rev-parse', 'HEAD') != sha):
        raise ActionError('deployment event is not eligible')
    workflow_id = current.get('workflow_id')
    if type(workflow_id) is not int or workflow_id <= 0:
        raise ActionError('invalid workflow')
    github_api = 'https://api.github.com/repos/' + repo
    _, _, body = fetch(github_api + '/actions/workflows/' + str(workflow_id), token=github_token)
    workflow = json.loads(body)
    if workflow.get('name') != 'pages-build-deployment' or workflow.get('path') != 'dynamic/pages/pages-build-deployment':
        raise ActionError('not the Pages deployment workflow')
    _, _, body = fetch(github_api + '/git/ref/heads/main', token=github_token)
    if json.loads(body)['object']['sha'] != sha:
        raise ActionError('main advanced before validation')
    previous = ix.find_previous_deployment(event, github_api, github_token, fetch=fetch)
    if not previous:
        raise ActionError('no earlier successful deployment')
    baseline = previous.get('head_sha', '')
    if not re.fullmatch(r'[a-f0-9]{40}', baseline):
        raise ActionError('invalid baseline')
    ancestry(['git', 'merge-base', '--is-ancestor', baseline, sha], cwd=ix.ROOT, check=True, capture_output=True)
    changed = git('diff', '--name-only', '--diff-filter=AM', baseline, sha, '--').splitlines()
    urls = ix.changed_urls(changed)
    return {'sha': sha, 'github_api': github_api, 'urls': urls}


def run(event, repo, github_token, google, yandex_token, *, fetch=ix.request,
        git=ix.git, ancestry=subprocess.run, validate=ix.validate_live,
        refresh=refresh_google, google_call=google_action, yandex_call=yandex_action):
    plan = build_plan(event, repo, github_token, fetch=fetch, git=git, ancestry=ancestry)
    # Check every changed URL, including those deferred by the per-run cap.
    validate(plan['urls'])
    _, _, body = fetch(plan['github_api'] + '/git/ref/heads/main', token=github_token)
    if json.loads(body)['object']['sha'] != plan['sha']:
        raise ActionError('main advanced during validation')
    result = {'changed_count': len(plan['urls']), 'sources': {}, 'not_guaranteed_indexed': True}
    if any(google.values()):
        try:
            token = refresh(google.get('id'), google.get('secret'), google.get('refresh'))
            result['sources']['google'] = {'status': 'ok', 'result': google_call(token, True)}
        except Exception:
            result['sources']['google'] = {'status': 'error', 'message': 'Google: ошибка доступа или действия; проверьте состояние перед повтором.'}
    else:
        result['sources']['google'] = {'status': 'not_connected'}
    if yandex_token:
        try:
            # A bounded batch. The remainder is explicitly surfaced, not silently submitted.
            batch = plan['urls'][:5]
            result['sources']['yandex'] = {'status': 'ok', 'result': yandex_call(yandex_token, batch, True),
                                            'deferred_urls': plan['urls'][5:]}
        except Exception:
            result['sources']['yandex'] = {'status': 'error', 'message': 'Яндекс: ошибка доступа или действия; проверьте состояние перед повтором.'}
    else:
        result['sources']['yandex'] = {'status': 'not_connected'}
    return result


def main():
    if os.environ.get('SCM_WEBMASTER_AUTOMATION') != '1':
        print('Автоматизация кабинетов не включена; запросы не выполнялись.')
        return 0
    if os.environ.get('GITHUB_RUN_ATTEMPT', '1') != '1':
        print('Повторный запуск заблокирован: сначала проверьте состояние кабинетов.', file=sys.stderr)
        return 1
    google = {'id': os.environ.pop('SCM_WM_GOOGLE_CLIENT_ID', ''),
              'secret': os.environ.pop('SCM_WM_GOOGLE_CLIENT_SECRET', ''),
              'refresh': os.environ.pop('SCM_WM_GOOGLE_REFRESH_TOKEN', '')}
    yandex = os.environ.pop('SCM_WM_YANDEX_ACCESS_TOKEN', '')
    if not any(google.values()) and not yandex:
        print('Доступы к вебмастерам не настроены; запросы не выполнялись.', file=sys.stderr)
        return 1
    try:
        with open(os.environ['GITHUB_EVENT_PATH'], encoding='utf-8') as f:
            event = json.load(f)
        result = run(event, os.environ['GITHUB_REPOSITORY'], os.environ['GITHUB_TOKEN'], google, yandex)
        print(json.dumps(result, ensure_ascii=False, indent=2))
        if any(item['status'] != 'ok' or item.get('deferred_urls') or
               any(r.get('status') == 'quota_exhausted' for r in item.get('result', {}).get('recrawl', []))
               for item in result['sources'].values()):
            return 1
        return 0
    except Exception:
        print('Проверка публикации или запуск не удались; проверьте состояние сервисов перед повтором.', file=sys.stderr)
        return 1


if __name__ == '__main__':
    sys.exit(main())
