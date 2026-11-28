#!/usr/bin/env python3
"""Track confirmed Yandex sitemap and description problems as bot-owned issues.

Only GET requests go to Yandex. Unknown status never creates or closes an issue.
"""
import os
import datetime
import sys
from live_seo_issue import sync
from webmaster_yandex_discovered import inspect as read_sitemap
from webmaster_yandex_site_problems import inspect as read_problems

SITEMAP_TITLE = 'Яндекс Вебмастер: ошибка обработки sitemap'
SITEMAP_BODY = ('<!-- scm-yandex-sitemap-health:v1 -->\n\n'
    'Яндекс сообщил об ошибке sitemap или диагностика указала проблему с картой. '
    'Данные могут относиться к предыдущему обходу. Нужны проверка и последующий контроль; '
    'эта задача не подтверждает состояние индексации.\n\n'
    'Запуск: {run}\n\nЗадача закрывается автоматически только при подтверждённом отсутствии ошибок в данных Яндекса.\n')
DESCRIPTION_TITLE = 'Яндекс Вебмастер: замечание об описаниях страниц'
DESCRIPTION_BODY = ('<!-- scm-yandex-description-health:v1 -->\n\n'
    'Диагностика Яндекса сообщает об отсутствующих описаниях страниц. '
    'Данные могут относиться к прежнему обходу или другим страницам. '
    'Нужна проверка, автоматическое изменение сайта не выполняется.\n\n'
    'Запуск: {run}\n\nЗадача закрывается автоматически после подтверждения отсутствия замечания Яндексом.\n')


def sync_health(token, repo, run_id, github_token, *, sitemap=read_sitemap, problems=read_problems, alert=sync):
    # Obtain both snapshots before touching issues. Never close on failed reads.
    sm = sitemap(token)
    site = problems(token)
    sitemap_status = site.get('ERRORS_IN_SITEMAPS')
    description_status = site.get('DOCUMENTS_MISSING_DESCRIPTION')
    if sitemap_status not in ('PRESENT','ABSENT','UNDEFINED','UNKNOWN_STATE','NOT_REPORTED') or description_status not in ('PRESENT','ABSENT','UNDEFINED','UNKNOWN_STATE','NOT_REPORTED'):
        raise ValueError('invalid diagnostics')
    found = sm.get('state') == 'found'
    count = sm.get('errors') if found else None
    if found and (type(count) is not int or count < 0):
        raise ValueError('invalid sitemap result')
    try:
        access_date = datetime.date.fromisoformat(sm.get('access_date', ''))
        date_known = access_date <= datetime.datetime.now(datetime.timezone.utc).date()
    except (TypeError, ValueError):
        date_known = False
    if sitemap_status == 'PRESENT' or (found and count > 0):
        sitemap_outcome = 'failure'
    elif sitemap_status == 'ABSENT' and found and count == 0 and date_known:
        sitemap_outcome = 'success'
    else:
        sitemap_outcome = None
    desc_outcome = {'PRESENT':'failure', 'ABSENT':'success'}.get(description_status)
    actions = []
    for outcome, title, body in ((sitemap_outcome,SITEMAP_TITLE,SITEMAP_BODY), (desc_outcome,DESCRIPTION_TITLE,DESCRIPTION_BODY)):
        if outcome is None:
            actions.append('unknown')
        else:
            actions.append(alert(repo,run_id,github_token,outcome,title=title,body_template=body))
    return tuple(actions)


def main():
    token=os.environ.pop('SCM_WM_YANDEX_ACCESS_TOKEN','')
    gh=os.environ.pop('GITHUB_TOKEN','')
    try:
        result=sync_health(token,os.environ.get('GITHUB_REPOSITORY',''),os.environ.get('GITHUB_RUN_ID',''),gh)
        print('::notice title=Yandex health alerts::sitemap='+result[0]+'; descriptions='+result[1])
        return 0
    except Exception:
        print('Не удалось синхронизировать уведомления о состоянии Яндекса; прежние задачи могут оставаться открытыми.',file=sys.stderr)
        return 1

if __name__ == '__main__':sys.exit(main())
