#!/usr/bin/env python3
"""Read-only alert when automatic GA4 search or outbound measurement is enabled or unknown."""
import os,sys
from analytics_ga4_privacy_inventory import inventory_settings
from live_seo_issue import sync
TITLE='GA4: проверить автоматический поиск и исходящие ссылки'
BODY=('<!-- scm-ga4-search-outbound-privacy:v1 -->\n\nАвтоматическое измерение поиска или исходящих ссылок в GA4 включено либо настройки не удалось проверить. '
      'Тест показал риск передачи параметров URL; проверьте настройки и доступ к API. Монитор ничего не меняет. '
      'Запуск: {run}\n\nЗадача закроется после подтверждения, что обе настройки отключены.\n')
def monitor(creds,repo,run,token,*,read=inventory_settings,alert=sync):
    try:
        data=read(creds)
        if not isinstance(data,dict) or any(type(data.get(k)) is not bool for k in ('search','outbound')):raise ValueError('invalid')
        status='failure' if data['search'] or data['outbound'] else 'success'
    except Exception:status='failure'
    result=alert(repo,run,token,status,title=TITLE,body_template=BODY)
    return status,result

def main():
    if os.environ.get('GITHUB_EVENT_NAME') not in ('workflow_dispatch','schedule') or os.environ.get('GITHUB_REF')!='refs/heads/main' or os.environ.get('GITHUB_REPOSITORY_ID')!='1102759388':return 1
    creds=[os.environ.pop(k,'') for k in ('SCM_GA4_CLIENT_ID','SCM_GA4_CLIENT_SECRET','SCM_GA4_REFRESH_TOKEN')];token=os.environ.pop('GITHUB_TOKEN','')
    try:
        status,alert=monitor(creds,os.environ.get('GITHUB_REPOSITORY',''),os.environ.get('GITHUB_RUN_ID',''),token)
        print('::notice title=GA4 search and outbound privacy monitor::status='+status+'; google_writes=0; alert='+alert)
        return 0 if status=='success' else 1
    except Exception:
        print('::error title=GA4 search and outbound privacy monitor::monitor_or_alert_failed; google_writes=0',file=sys.stderr);return 1
if __name__=='__main__':sys.exit(main())
