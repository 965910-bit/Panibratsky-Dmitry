#!/usr/bin/env python3
"""Weekly GA4 report connection and known-event monitor; does not write GA4."""
import os
import sys
from analytics_ga4_reports_diagnostic import inspect
from live_seo_issue import sync

TITLE='Google Analytics: не удалось проверить отчёты'
BODY=('<!-- scm-ga4-reports-access:v1 -->\n\n'
      'Автоматическая проверка отчётов Google Analytics не завершилась. '
      'Возможные причины: срок OAuth, права, настройки API или временная ошибка. '
      'Монитор не меняет настройки Google.\n\n'
      'Запуск: {run}\n\nЗадача закроется после успешного чтения отчёта.\n')

def monitor(admin,report,repo,run_id,token,*,read=inspect,alert=sync):
    try:
        result=read(admin,report)
        if not isinstance(result,dict) or not isinstance(result.get('observed'),list):raise ValueError('invalid report')
        status='success'
    except Exception:
        result=None;status='failure'
    notice=alert(repo,run_id,token,status,title=TITLE,body_template=BODY)
    return status,result,notice

def main():
    if (os.environ.get('GITHUB_EVENT_NAME') not in ('workflow_dispatch','schedule') or os.environ.get('GITHUB_REF')!='refs/heads/main' or os.environ.get('GITHUB_REPOSITORY_ID')!='1102759388'):
        print('Monitor blocked.',file=sys.stderr);return 1
    admin=[os.environ.pop(k,'') for k in ('SCM_GA4_CLIENT_ID','SCM_GA4_CLIENT_SECRET','SCM_GA4_REFRESH_TOKEN')]
    report=[os.environ.pop(k,'') for k in ('SCM_GA4_REPORT_CLIENT_ID','SCM_GA4_REPORT_CLIENT_SECRET','SCM_GA4_REPORT_REFRESH_TOKEN')]
    token=os.environ.pop('GITHUB_TOKEN','')
    try:
        status,result,alert=monitor(admin,report,os.environ.get('GITHUB_REPOSITORY',''),os.environ.get('GITHUB_RUN_ID',''),token)
        if result is not None:
            print('::notice title=GA4 weekly report::status=success; observed_agreed_events='+str(len(result['observed']))+'; thresholded='+str(result['thresholded']).lower()+'; sampled='+str(result['sampled']).lower()+'; missing_is_not_zero; ga4_writes=0; alert='+alert)
        else:print('::error title=GA4 weekly report::status=failure; ga4_writes=0; alert='+alert,file=sys.stderr)
        return 0 if status=='success' else 1
    except Exception:
        print('::error title=GA4 weekly report::monitor_or_alert_failed; ga4_writes=0',file=sys.stderr);return 1
if __name__=='__main__':sys.exit(main())
