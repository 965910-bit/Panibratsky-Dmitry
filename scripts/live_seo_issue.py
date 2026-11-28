#!/usr/bin/env python3
"""Open/resolve one bot-owned public SEO smoke alert; never expose report details."""
import json
import os
import re
import sys
import urllib.error
import urllib.parse
import urllib.request

REPOSITORY_ID = 1102759388
TITLE = 'Автопроверка сайта: найдено техническое замечание'
MARKER = '<!-- scm-public-seo-alert:v1 -->'
BODY = (MARKER + '\n\nПубличная техническая SEO-проверка завершилась ошибкой. '
        'Причиной может быть сетевой сбой или задержка публикации; индексирование эта проверка не оценивает.\n\n'
        'Запуск: {run}\n\nЗадача закрывается автоматически после следующей успешной проверки.\n')


class AlertError(Exception):
    pass


class NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return None


def request(url, token, *, method='GET', body=None):
    if not url.startswith('https://api.github.com/') or method not in ('GET','POST','PATCH'):
        raise AlertError('invalid endpoint')
    headers = {'Accept':'application/vnd.github+json', 'X-GitHub-Api-Version':'2022-11-28',
               'Authorization':'Bearer '+token, 'User-Agent':'SCM-public-SEO-alert/1.0'}
    raw = None if body is None else json.dumps(body,ensure_ascii=False).encode('utf-8')
    if raw is not None:
        headers['Content-Type']='application/json'
    req = urllib.request.Request(url,data=raw,headers=headers,method=method)
    try:
        with urllib.request.build_opener(NoRedirect).open(req,timeout=20) as response:
            raw = response.read(2*1024*1024+1)
        if len(raw)>2*1024*1024:
            raise AlertError('response too large')
        return json.loads(raw)
    except (urllib.error.URLError,OSError,TimeoutError,UnicodeError,ValueError):
        # No retry on a write: the remote result may be unknown.
        raise AlertError('GitHub alert request failed; outcome may be unknown') from None


def sync(repo, run_id, token, outcome, *, call=request, title=TITLE, body_template=BODY):
    if (not re.fullmatch(r'[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+',repo or '') or
        not re.fullmatch(r'[1-9][0-9]{0,19}',run_id or '') or
        not isinstance(token,str) or not token or '\n' in token or '\r' in token or
        outcome not in ('success','failure')):
        raise AlertError('invalid alert configuration or uncertain check outcome')
    base='https://api.github.com/repos/'+repo
    metadata=call(base,token)
    if not isinstance(metadata,dict) or metadata.get('id') != REPOSITORY_ID or metadata.get('has_issues') is not True:
        raise AlertError('repository identity or issue support not confirmed')
    found=[]
    body_pattern = re.escape(body_template.format(run='RUN_URL')).replace('RUN_URL',re.escape('https://github.com/'+repo+'/actions/runs/') + r'[1-9][0-9]{0,19}')
    for page in range(1,11):
        page_data=call(base+'/issues?state=open&per_page=100&page='+str(page),token)
        if not isinstance(page_data,list) or len(page_data)>100:
            raise AlertError('invalid issue list')
        for issue in page_data:
            if not isinstance(issue,dict) or 'pull_request' in issue:
                continue
            user=issue.get('user')
            body=issue.get('body')
            if (issue.get('title') == title and isinstance(user,dict) and
                user.get('login') == 'github-actions[bot]' and user.get('type') == 'Bot' and
                isinstance(body,str) and re.fullmatch(body_pattern,body)):
                number=issue.get('number')
                if type(number) is not int or number < 1:
                    raise AlertError('invalid matching issue')
                found.append(number)
        if len(page_data)<100:
            break
    else:
        raise AlertError('too many open issues to verify safely')
    if len(found)>1:
        raise AlertError('multiple matching alert issues; no mutation')
    if outcome=='failure' and not found:
        run='https://github.com/'+repo+'/actions/runs/'+run_id
        call(base+'/issues',token,method='POST',body={'title':title,'body':body_template.format(run=run)})
        return 'created'
    if outcome=='success' and found:
        call(base+'/issues/'+str(found[0]),token,method='PATCH',body={'state':'closed','state_reason':'completed'})
        return 'closed'
    return 'already_open' if found else 'clear'


def main():
    token=os.environ.pop('GITHUB_TOKEN','')
    try:
        result=sync(os.environ.get('GITHUB_REPOSITORY',''),os.environ.get('GITHUB_RUN_ID',''),token,os.environ.get('SEO_CHECK_OUTCOME',''))
        print('GitHub SEO alert: '+result+'. Доставка уведомлений зависит от подписки GitHub.')
        return 0
    except Exception:
        print('Не удалось синхронизировать оповещение GitHub; проверьте права и журнал.',file=sys.stderr)
        return 1


if __name__=='__main__':
    sys.exit(main())
