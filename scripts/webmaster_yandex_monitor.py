#!/usr/bin/env python3
"""Read-only daily Yandex monitoring with a separately owned access alert."""
import os
import sys
from webmaster_yandex_diagnostic import inspect
from live_seo_issue import sync

TITLE = 'Яндекс Вебмастер: не удалось проверить подключение'
BODY = ('<!-- scm-yandex-read-access-alert:v1 -->\n\n'
        'Не удалось безопасно прочитать подтверждённый сайт, список карт и квоту. '
        'Возможны временный сбой, истечение токена или изменение прав. '
        'Отправка sitemap и переобход этой проверкой не выполняются.\n\n'
        'Запуск: {run}\n\nЗадача закрывается автоматически после успешной проверки чтения.\n')


def monitor(yandex_token, repo, run_id, github_token, *, read=inspect, alert=sync):
    try:
        result = read(yandex_token)
        state = result['sitemap']
        quota = result['quota_remaining']
        if result.get('verified') is not True or state not in ('already_present', 'would_submit') or type(quota) is not int or quota < 0:
            raise ValueError('invalid diagnostic result')
        outcome = 'success'
    except Exception:
        outcome = 'failure'
        state, quota = 'unknown', None
    alert_result = alert(repo, run_id, github_token, outcome, title=TITLE, body_template=BODY)
    return outcome, state, quota, alert_result


def main():
    token = os.environ.pop('SCM_WM_YANDEX_ACCESS_TOKEN', '')
    github_token = os.environ.pop('GITHUB_TOKEN', '')
    try:
        outcome, state, quota, issue = monitor(token, os.environ.get('GITHUB_REPOSITORY',''), os.environ.get('GITHUB_RUN_ID',''), github_token)
        print('::notice title=Yandex monitoring::access='+outcome+'; sitemap='+state+'; quota_remaining='+str(quota if quota is not None else 'unknown'))
        print('GitHub alert: '+issue+'. Проверка не отправляет данные в Яндекс и не подтверждает индексацию.')
        return 0 if outcome == 'success' else 1
    except Exception:
        print('Не удалось завершить мониторинг или синхронизировать уведомление GitHub.', file=sys.stderr)
        return 1

if __name__ == '__main__':
    sys.exit(main())
