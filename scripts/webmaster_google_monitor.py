#!/usr/bin/env python3
"""Daily read-only Google Search Console monitoring; no Google writes."""
import os
import sys
from webmaster_google_diagnostic import inspect
from live_seo_issue import sync

ACCESS_TITLE='Google Search Console: не удалось проверить подключение'
ACCESS_BODY=('<!-- scm-google-access-alert:v1 -->\n\n'
    'Автоматическая проверка Google Search Console не завершилась. Причиной могут быть '
    'токен, права на ресурс или временный сбой. Действия в Google не выполнялись.\n\n'
    'Запуск: {run}\n\nЗадача закроется после успешного чтения Google.\n')
SITEMAP_TITLE='Google Search Console: требуется проверить sitemap'
SITEMAP_BODY=('<!-- scm-google-sitemap-alert:v1 -->\n\n'
    'Google сообщает об ошибке sitemap или не показывает целевую карту в выбранном ресурсе. '
    'Сведения могут обновляться с задержкой. Мониторинг ничего не отправляет и не подтверждает индексацию.\n\n'
    'Запуск: {run}\n\nЗадача закроется только после подтверждённого успешного чтения карты Google.\n')


def monitor(creds,repo,run_id,github_token,*,read=inspect,alert=sync):
    try:
        result=read(*creds)
        if result.get('status')!='connected':raise ValueError('access unavailable')
        health=result.get('sitemap_health')
        if health not in ('healthy','missing','error','pending','unknown'):raise ValueError('invalid health')
    except Exception:
        connection='failure';health='unknown'
    else:connection='success'
    access=alert(repo,run_id,github_token,connection,title=ACCESS_TITLE,body_template=ACCESS_BODY)
    outcome='failure' if health in ('missing','error') else 'success' if health=='healthy' else None
    sitemap=alert(repo,run_id,github_token,outcome,title=SITEMAP_TITLE,body_template=SITEMAP_BODY) if outcome else 'unknown'
    return connection,health,access,sitemap


def main():
    creds=[os.environ.pop(key,'') for key in ('SCM_WM_GOOGLE_CLIENT_ID','SCM_WM_GOOGLE_CLIENT_SECRET','SCM_WM_GOOGLE_REFRESH_TOKEN')]
    gh=os.environ.pop('GITHUB_TOKEN','')
    try:
        connection,health,access,sitemap=monitor(creds,os.environ.get('GITHUB_REPOSITORY',''),os.environ.get('GITHUB_RUN_ID',''),gh)
        print('::notice title=Google Search Console monitor::access='+connection+'; sitemap_health='+health+'; access_alert='+access+'; sitemap_alert='+sitemap+'; google_writes=0')
        return 0 if connection=='success' else 1
    except Exception:
        print('::error title=Google Search Console monitor::monitor_or_alert_failed',file=sys.stderr);return 1
if __name__=='__main__':sys.exit(main())
