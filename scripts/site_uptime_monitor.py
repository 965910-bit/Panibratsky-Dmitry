#!/usr/bin/env python3
"""Scheduled single-region HTTP availability probe with alerts in the existing project task."""
import os
import re
import sys
import time
import urllib.error
import urllib.request
from live_seo_issue import request as github_request, REPOSITORY_ID, NoRedirect

URL='https://scm-news.ru/'
MARKER='<!-- scm-uptime-monitor:v1 -->'
class MonitorError(Exception):pass

def probe():
    req=urllib.request.Request(URL,headers={'User-Agent':'SCM-News-Availability-Monitor/1.0','Accept':'text/html'})
    try:
        with urllib.request.build_opener(NoRedirect).open(req,timeout=15) as response:
            if response.status!=200 or response.headers.get_content_type()!='text/html':return False
            content=response.read(8192).lower()
            return b'<html' in content or b'<!doctype html' in content
    except (urllib.error.URLError,TimeoutError,OSError,ValueError):return False

def availability(*, check=probe, wait=time.sleep):
    for attempt in range(3):
        if check():return True
        if attempt<2:wait(8)
    return False

def alert(repo,run_id,token,available,*,call=github_request):
    if not re.fullmatch(r'[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+',repo or '') or not re.fullmatch(r'[1-9][0-9]{0,19}',run_id or '') or not token or '\n' in token or '\r' in token or type(available) is not bool:raise MonitorError('invalid context')
    base='https://api.github.com/repos/'+repo
    metadata=call(base,token)
    if not isinstance(metadata,dict) or metadata.get('id')!=REPOSITORY_ID or metadata.get('has_issues') is not True:raise MonitorError('repository mismatch')
    issue=call(base+'/issues/244',token)
    if not isinstance(issue,dict) or issue.get('number')!=244 or 'pull_request' in issue or issue.get('state')!='open':raise MonitorError('project task unavailable')
    pattern=re.compile(re.escape(MARKER)+r'\nstatus=(failure|recovery)\n.*',re.S)
    states=[]
    for page in range(1,11):
        comments=call(base+'/issues/244/comments?per_page=100&page='+str(page),token)
        if not isinstance(comments,list) or len(comments)>100:raise MonitorError('invalid comments')
        for c in comments:
            if not isinstance(c,dict):raise MonitorError('invalid comment')
            author=c.get('user',{})
            if not isinstance(author,dict):raise MonitorError('invalid author')
            if author.get('login')!='github-actions[bot]' or author.get('type')!='Bot':continue
            body=c.get('body');match=pattern.fullmatch(body) if isinstance(body,str) else None
            if match:
                if type(c.get('id')) is not int or c['id']<1:raise MonitorError('invalid id')
                states.append((c['id'],match.group(1)))
        if len(comments)<100:break
    else:raise MonitorError('comment limit')
    previous=max(states)[1] if states else None
    current='recovery' if available else 'failure'
    if previous==current or (previous is None and available):return 'unchanged'
    run='https://github.com/'+repo+'/actions/runs/'+run_id
    message=('Главная страница не ответила ожидаемым HTTP 200 и HTML при трёх проверках из GitHub Actions. Это может быть локальный сетевой сбой и не доказывает глобальную недоступность.' if not available else 'Главная страница снова ответила ожидаемым HTTP 200 и HTML при проверке из GitHub Actions.')
    body=MARKER+'\nstatus='+current+'\n\n'+message+'\n\nЗапуск: '+run+'\n\nПроверка периодическая, из одного региона; доставку уведомлений определяют настройки GitHub.'
    result=call(base+'/issues/244/comments',token,method='POST',body={'body':body})
    if not isinstance(result,dict) or type(result.get('id')) is not int or result['id']<1:raise MonitorError('unconfirmed notification')
    return 'notified'

def main():
    if os.environ.get('GITHUB_EVENT_NAME') not in ('workflow_dispatch','schedule') or os.environ.get('GITHUB_REF')!='refs/heads/main' or os.environ.get('GITHUB_REPOSITORY_ID')!=str(REPOSITORY_ID):
        print('Blocked.',file=sys.stderr);return 1
    token=os.environ.pop('GITHUB_TOKEN','')
    try:
        up=availability()
        notice=alert(os.environ.get('GITHUB_REPOSITORY',''),os.environ.get('GITHUB_RUN_ID',''),token,up)
        print('::notice title=Homepage availability::reachable='+str(up).lower()+'; alert='+notice+'; single_region_periodic; not_sla')
        return 0 if up else 1
    except Exception:
        print('::error title=Homepage availability::monitor_or_notification_failed; availability_unknown',file=sys.stderr);return 1
if __name__=='__main__':sys.exit(main())
