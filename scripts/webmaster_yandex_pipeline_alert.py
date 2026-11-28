#!/usr/bin/env python3
"""Track failure of the entire Yandex read-only monitoring pipeline."""
import os
import sys
from live_seo_issue import sync

TITLE = 'Яндекс Вебмастер: мониторинг выполнен не полностью'
BODY = ('<!-- scm-yandex-pipeline-alert:v1 -->\n\n'
        'Один или несколько этапов мониторинга не выполнены. Сведения о карте, '
        'диагностике или уведомлениях могут быть неполными. Причиной может быть '
        'временная ошибка сети, доступ к сервису или ошибка обработки. '
        'Мониторинг не отправляет запросы на переобход и не подтверждает индексацию.\n\n'
        'Запуск: {run}\n\nЗадача закрывается автоматически только после успешного выполнения всех этапов.\n')
KEYS = ('ACCESS_OUTCOME','SITEMAP_OUTCOME','DIAGNOSTICS_OUTCOME','ISSUES_OUTCOME')


def classify(values):
    if len(values) != len(KEYS) or any(v not in ('success','failure','skipped','cancelled','') for v in values):
        raise ValueError('invalid stage outcomes')
    if all(v == 'success' for v in values): return 'success'
    # Skipped or missing stages alone are not proof of a successful check.
    return 'failure'


def main():
    token=os.environ.pop('GITHUB_TOKEN','')
    try:
        outcome=classify([os.environ.get(key,'') for key in KEYS])
        result=sync(os.environ.get('GITHUB_REPOSITORY',''),os.environ.get('GITHUB_RUN_ID',''),token,outcome,title=TITLE,body_template=BODY)
        print('::notice title=Yandex pipeline alert::'+result+'; pipeline='+outcome)
        return 0
    except Exception:
        print('Не удалось синхронизировать уведомление о полноте мониторинга.',file=sys.stderr)
        return 1
if __name__=='__main__':sys.exit(main())
