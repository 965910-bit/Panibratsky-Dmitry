#!/usr/bin/env python3
"""Render an existing read-only SEO smoke result as a bounded Actions summary."""
import html
import json
from pathlib import Path
import sys


def render(path):
    try:
        raw = Path(path).read_bytes()
        if len(raw) > 128 * 1024:
            raise ValueError('too large')
        report = json.loads(raw)
        pages = report['pages_expected']
        requests = report['requests_expected']
        findings = report['findings']
        if (type(pages) is not int or pages < 0 or type(requests) is not int or requests < 0
                or not isinstance(findings, list) or len(findings) > 200
                or any(not isinstance(item, str) or len(item) > 500 for item in findings)):
            raise ValueError('invalid report')
    except (OSError, UnicodeError, ValueError, TypeError, KeyError, json.JSONDecodeError):
        return '## Ежедневная публичная SEO-проверка\n\nОтчёт недоступен или повреждён; результат проверки не подтверждён.\n'
    status = 'Найдены замечания' if findings else 'Замечаний в проверенном наборе нет'
    lines = ['## Ежедневная публичная SEO-проверка', '', f'**{status}**. Страниц: {pages}; ожидаемых запросов: {requests}.', '']
    if findings:
        # HTML escaping plus code elements prevent report strings from injecting markdown/HTML.
        lines.extend(f'- <code>{html.escape(item, quote=True)}</code>' for item in findings)
        lines.append('')
    lines.append('Проверяются только фиксированные URL, sitemap, robots, canonical, noindex и синтаксис JSON-LD. Это не проверка индексации, позиций, доставки IndexNow или всего сайта.')
    return '\n'.join(lines) + '\n'


if __name__ == '__main__':
    if len(sys.argv) != 2:
        raise SystemExit('Usage: live_seo_summary.py <report.json>')
    print(render(sys.argv[1]), end='')
