#!/usr/bin/env python3
"""Report snapshot job failure without exposing private report contents."""
import os
import sys
from live_seo_issue import sync

TITLE = 'Приватный отчёт: автоматический запуск завершился ошибкой'
BODY = ('<!-- scm-private-snapshot-alert:v1 -->\n\n'
        'Создание или публикация зашифрованного отчёта завершилась ошибкой. '
        'Результат публикации может быть неизвестен: проверьте задачу с зашифрованными отчётами перед повторным запуском. '
        'Это уведомление не подтверждает доставку владельцу или успешное восстановление.\n\n'
        'Запуск: {run}\n\nЗадача закроется после успешного запуска формирования и публикации.\n')


def main():
    if (os.environ.get('GITHUB_EVENT_NAME') not in ('workflow_dispatch', 'schedule') or
        os.environ.get('GITHUB_REF') != 'refs/heads/main' or
        os.environ.get('GITHUB_REPOSITORY_ID') != '1102759388'):
        print('Snapshot alert blocked.', file=sys.stderr)
        return 1
    outcome = os.environ.get('SNAPSHOT_JOB_STATUS', '')
    if outcome not in ('success', 'failure'):
        print('Snapshot status uncertain; alert unchanged.', file=sys.stderr)
        return 1
    token = os.environ.pop('GITHUB_TOKEN', '')
    try:
        result = sync(os.environ.get('GITHUB_REPOSITORY', ''), os.environ.get('GITHUB_RUN_ID', ''),
                      token, outcome, title=TITLE, body_template=BODY)
        print('::notice title=Private snapshot alert::status=' + result + '; delivery_and_recovery_unverified')
        return 0
    except Exception:
        print('::error title=Private snapshot alert::alert_unavailable; delivery_and_recovery_unverified', file=sys.stderr)
        return 1


if __name__ == '__main__':
    sys.exit(main())
