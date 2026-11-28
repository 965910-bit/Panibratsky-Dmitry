#!/usr/bin/env python3
"""Read-only alert when automatic GA4 form measurement is enabled or unknown."""
import os,sys
from analytics_ga4_privacy_inventory import inventory_settings
from live_seo_issue import sync
TITLE='GA4: проверить автоматический сбор форм'
BODY=('<!-- scm-ga4-form-privacy:v1 -->\n\nАвтоматические события форм в GA4 включены или их настройку не удалось проверить. '
      'На страницах инструментов включён GA4 после согласия посетителя; проверьте formInteractionsEnabled и доступ к API. '
      'Монитор ничего не меняет. Запуск: {run}\n\nЗадача закроется после подтверждения, что автоматические события форм отключены.\n')
def monitor(creds,repo,run,token,*,read=inventory_settings,alert=sync):
    try:
        data=read(creds)
        if not isinstance(data,dict) or type(data.get('forms')) is not bool:raise ValueError('invalid')
        status='failure' if data['forms'] else 'success'
    except Exception:status='failure'
    result=alert(repo,run,token,status,title=TITLE,body_template=BODY)
    return status,result

def main():
    if os.environ.get('GITHUB_EVENT_NAME') not in ('workflow_dispatch','schedule') or os.environ.get('GITHUB_REF')!='refs/heads/main' or os.environ.get('GITHUB_REPOSITORY_ID')!='1102759388':return 1
    creds=[os.environ.pop(k,'') for k in ('SCM_GA4_CLIENT_ID','SCM_GA4_CLIENT_SECRET','SCM_GA4_REFRESH_TOKEN')];token=os.environ.pop('GITHUB_TOKEN','')
    try:
        status,alert=monitor(creds,os.environ.get('GITHUB_REPOSITORY',''),os.environ.get('GITHUB_RUN_ID',''),token)
        print('::notice title=GA4 form privacy monitor::status='+status+'; google_writes=0; alert='+alert)
        return 0 if status=='success' else 1
    except Exception:
        print('::error title=GA4 form privacy monitor::monitor_or_alert_failed; google_writes=0',file=sys.stderr);return 1
if __name__=='__main__':sys.exit(main())
