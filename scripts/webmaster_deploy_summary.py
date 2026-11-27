#!/usr/bin/env python3
"""Render a bounded, escaped after-deployment report for GitHub Actions."""
import html
import json
from pathlib import Path
import sys

DISABLED = 'Автоматизация кабинетов не включена; запросы не выполнялись.'


def render(path):
    try:
        raw = Path(path).read_bytes()
        if len(raw) > 256 * 1024:
            raise ValueError('report too large')
        text = raw.decode('utf-8').strip()
        if text == DISABLED:
            return '## Вебмастера после публикации\n\nАвтоматизация выключена; запросов в кабинеты не было.\n'
        data = json.loads(text)
        if not isinstance(data,dict) or not isinstance(data.get('sources'),dict):
            raise ValueError('invalid report')
        lines = ['## Вебмастера после публикации', '']
        sources = data['sources']
        labels = {'google':'Google Search Console','yandex':'Яндекс Вебмастер'}
        for name in ('google','yandex'):
            entry = sources.get(name)
            if not isinstance(entry,dict) or entry.get('status') not in ('ok','error','not_connected'):
                raise ValueError('invalid source')
            states = {'ok':'вызов завершён', 'error':'ошибка или неизвестный исход', 'not_connected':'не подключён'}
            lines.append(f"- **{labels[name]}:** {states[entry['status']]}")
            if name != 'yandex':
                continue
            result = entry.get('result',{})
            if not isinstance(result,dict):
                raise ValueError('invalid result')
            tasks = result.get('recrawl',[])
            deferred = entry.get('deferred_urls',[])
            if not isinstance(tasks,list) or len(tasks)>5 or not isinstance(deferred,list) or len(deferred)>500:
                raise ValueError('invalid batch')
            for task in tasks:
                if not isinstance(task,dict) or task.get('status') not in ('accepted','already_added','quota_exhausted','unknown'):
                    raise ValueError('invalid task')
                url = task.get('url'); task_id = task.get('task_id')
                if not isinstance(url,str) or len(url)>500 or (task_id is not None and (not isinstance(task_id,str) or len(task_id)>100)):
                    raise ValueError('invalid task details')
                suffix = f' · задача <code>{html.escape(task_id,quote=True)}</code>' if task_id else ''
                lines.append(f"  - <code>{html.escape(url,quote=True)}</code>: <code>{task['status']}</code>{suffix}")
            if any(not isinstance(url,str) or len(url)>500 for url in deferred):
                raise ValueError('invalid deferred URL')
            if deferred:
                lines.append(f'  - Не отправлены: {len(deferred)}. Первые {min(len(deferred), 25)}:')
                lines.extend(f'    - <code>{html.escape(url,quote=True)}</code>' for url in deferred[:25])
        lines.extend(['', 'Принятие заявки не гарантирует обход или индексацию. Неизвестный исход требует сверки перед повтором; отчёт не является постоянной очередью.'])
        return '\n'.join(lines)+'\n'
    except (OSError, UnicodeError, ValueError, TypeError, KeyError):
        return '## Вебмастера после публикации\n\nОтчёт недоступен или повреждён; состояние действий не подтверждено. Проверьте журнал.\n'


if __name__ == '__main__':
    if len(sys.argv)!=2:
        raise SystemExit('Usage: webmaster_deploy_summary.py <report>')
    print(render(sys.argv[1]),end='')
