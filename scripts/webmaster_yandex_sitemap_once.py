#!/usr/bin/env python3
"""Add only the missing canonical sitemap to verified Yandex, once per dispatch."""
import json
import os
import re
import sys
import indexnow_submit as ix
from webmaster_actions import ActionError, ApiError, api, yandex_action


def run(repo, gh_token, token, *, git=ix.git, fetch=ix.request, validate=ix.validate_live, action=yandex_action, emit=lambda stage: None):
    if not re.fullmatch(r'[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+',repo or '') or not gh_token or not token:
        raise ActionError('missing configuration')
    emit('checkout')
    sha=git('rev-parse','HEAD')
    if not re.fullmatch(r'[a-f0-9]{40}',sha):
        raise ActionError('invalid checkout')
    root='https://api.github.com/repos/'+repo
    _,_,raw=fetch(root+'/git/ref/heads/main',token=gh_token)
    if json.loads(raw)['object']['sha']!=sha:
        raise ActionError('not current main')
    emit('pages_check')
    _,_,raw=fetch(root+'/pages/builds/latest',token=gh_token)
    build=json.loads(raw)
    if build.get('status')!='built' or build.get('commit')!=sha:
        raise ActionError('main is not the latest built Pages deployment')
    emit('live_preflight')
    validate([])
    _,_,raw=fetch(root+'/git/ref/heads/main',token=gh_token)
    if json.loads(raw)['object']['sha']!=sha:
        raise ActionError('main advanced')
    emit('provider_action')
    result=action(token,[],True)
    if result.get('sitemap') not in ('submitted','already_present') or result.get('recrawl') != []:
        raise ActionError('invalid response or unknown outcome')
    return result['sitemap']


def observed_action(token, urls, apply, *, emit, request=api):
    """Emit fixed operation names, never endpoint URLs, response bodies or credentials."""
    def observed(url, credential, scheme, method='GET', body=None):
        if method == 'GET' and url.endswith('/user'):
            stage = 'read_user'
        elif method == 'GET' and url.endswith('/hosts'):
            stage = 'read_hosts'
        elif method == 'GET' and url.endswith('/user-added-sitemaps?limit=100'):
            stage = 'read_sitemaps'
        elif method == 'POST' and url.endswith('/user-added-sitemaps'):
            stage = 'submit_sitemap'
        else:
            raise ActionError('unexpected provider operation')
        emit(stage)
        return request(url, credential, scheme, method=method, body=body)
    return yandex_action(token, urls, apply, request=observed)


def main():
    if (os.environ.get('GITHUB_EVENT_NAME')!='workflow_dispatch' or os.environ.get('GITHUB_REF')!='refs/heads/main'
        or os.environ.get('GITHUB_RUN_ATTEMPT','')!='1'):
        print('Повторный или неподходящий запуск заблокирован.',file=sys.stderr);return 1
    token=os.environ.pop('SCM_WM_YANDEX_ACCESS_TOKEN','')
    try:
        emit=lambda stage: print('::notice title=Yandex sitemap stage::'+stage,flush=True)
        action=lambda t, urls, apply: observed_action(t, urls, apply, emit=emit)
        outcome=run(os.environ.get('GITHUB_REPOSITORY',''),os.environ.get('GITHUB_TOKEN',''),token, action=action, emit=emit)
        print('::notice title=Yandex sitemap::'+outcome)
        print('Заявка на обработку карты не гарантирует индексацию.')
        return 0
    except ApiError as exc:
        status = str(exc.status) if type(exc.status) is int and 100 <= exc.status <= 599 else 'unknown'
        code = exc.code if exc.code in ('SITEMAP_ALREADY_ADDED','URL_ALREADY_ADDED','QUOTA_EXCEEDED') else 'unclassified'
        print('::error title=Yandex API::http='+status+'; code='+code)
        print('Действие не завершено; проверьте состояние перед повтором.',file=sys.stderr)
        return 1
    except Exception:
        print('::error title=Yandex sitemap::failed_unknown')
        print('Проверка или действие не завершены; при возможной отправке проверьте состояние перед повтором.',file=sys.stderr)
        return 1

if __name__=='__main__':sys.exit(main())
