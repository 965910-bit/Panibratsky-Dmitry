#!/usr/bin/env python3
"""Add only the missing canonical sitemap to verified Yandex, once per dispatch."""
import json
import os
import re
import sys
import indexnow_submit as ix
from webmaster_actions import ActionError, yandex_action


def run(repo, gh_token, token, *, git=ix.git, fetch=ix.request, validate=ix.validate_live, action=yandex_action):
    if not re.fullmatch(r'[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+',repo or '') or not gh_token or not token:
        raise ActionError('missing configuration')
    sha=git('rev-parse','HEAD')
    if not re.fullmatch(r'[a-f0-9]{40}',sha):
        raise ActionError('invalid checkout')
    root='https://api.github.com/repos/'+repo
    _,_,raw=fetch(root+'/git/ref/heads/main',token=gh_token)
    if json.loads(raw)['object']['sha']!=sha:
        raise ActionError('not current main')
    _,_,raw=fetch(root+'/pages/builds/latest',token=gh_token)
    build=json.loads(raw)
    if build.get('status')!='built' or build.get('commit')!=sha:
        raise ActionError('main is not the latest built Pages deployment')
    validate([])
    _,_,raw=fetch(root+'/git/ref/heads/main',token=gh_token)
    if json.loads(raw)['object']['sha']!=sha:
        raise ActionError('main advanced')
    result=action(token,[],True)
    if result.get('sitemap') not in ('submitted','already_present') or result.get('recrawl') != []:
        raise ActionError('invalid response or unknown outcome')
    return result['sitemap']


def main():
    if (os.environ.get('GITHUB_EVENT_NAME')!='workflow_dispatch' or os.environ.get('GITHUB_REF')!='refs/heads/main'
        or os.environ.get('GITHUB_RUN_ATTEMPT','')!='1'):
        print('Повторный или неподходящий запуск заблокирован.',file=sys.stderr);return 1
    token=os.environ.pop('SCM_WM_YANDEX_ACCESS_TOKEN','')
    try:
        outcome=run(os.environ.get('GITHUB_REPOSITORY',''),os.environ.get('GITHUB_TOKEN',''),token)
        print('::notice title=Yandex sitemap::'+outcome)
        print('Заявка на обработку карты не гарантирует индексацию.')
        return 0
    except Exception:
        print('Проверка или действие не завершены; при возможной отправке проверьте состояние перед повтором.',file=sys.stderr)
        return 1

if __name__=='__main__':sys.exit(main())
