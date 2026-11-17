"""Build an offline review gallery from an unapproved candidate batch; no network."""
import argparse
import html
import json
import os
from pathlib import Path
import unicodedata
from urllib.parse import unquote_plus, urlsplit, urlunsplit

from card import make_card, draft_fingerprint, PngImagePlugin


def title_key(value):
    """Only exact long titles after normalization are hints, not proof of duplication."""
    if not isinstance(value, str) or len(value) > 1000:
        return None
    text = unicodedata.normalize('NFKC', value).casefold()
    key = ' '.join(''.join(char if char.isalnum() else ' ' for char in text).split())
    return key if sum(char.isalnum() for char in key) >= 20 else None


def source_key(value):
    """Drop fragment and common tracking parameters for comparison only, not submission."""
    if not isinstance(value, str) or len(value) > 2048:
        return None
    try:
        parts = urlsplit(value)
        if parts.scheme.lower() not in ('http', 'https') or not parts.hostname or parts.username or parts.password:
            return None
        query = []
        for item in parts.query.split('&'):
            if not item:
                continue
            key = unquote_plus(item.split('=', 1)[0]).casefold()
            if key.startswith('utm_') or key in ('gclid', 'fbclid'):
                continue
            query.append(item)
        return urlunsplit((parts.scheme.lower(), parts.netloc.lower(), parts.path, '&'.join(query), ''))
    except (ValueError, UnicodeError):
        return None


def possible_duplicates(drafts):
    """Return other 1-based candidate numbers. Never filter, edit, send or query a journal."""
    matches = [[] for _ in drafts]
    keys = [(title_key(draft.get('title')), source_key(draft.get('source_url'))) for draft in drafts]
    for i, (title, source) in enumerate(keys):
        for j in range(i):
            other_title, other_source = keys[j]
            if (title and title == other_title) or (source and source == other_source):
                matches[i].append(j + 1)
                matches[j].append(i + 1)
    return matches


def prepare(batch, output):
    if not isinstance(batch, dict) or batch.get('version') != 1 or not isinstance(batch.get('drafts'), list) or len(batch['drafts']) > 20:
        raise ValueError('Неверный формат подборки')
    for draft in batch['drafts']:
        if not isinstance(draft, dict) or draft.get('version') != 1 or draft.get('ready_for_review') is not False or draft.get('comment') != '':
            raise ValueError('Ожидаются только неподтверждённые кандидаты без комментария')
    # Exclusive directory creation: never overwrite a previous gallery.
    output.mkdir(mode=0o700)
    entries = []
    duplicates = possible_duplicates(batch['drafts'])
    for number, draft in enumerate(batch['drafts'], 1):
        image = make_card(draft)
        card_name = f'card-{number:02}.png'
        draft_name = f'draft-{number:02}.json'
        metadata = PngImagePlugin.PngInfo()
        metadata.add_text('SCM-Draft-SHA256', draft_fingerprint(draft))
        with os.fdopen(os.open(output / card_name, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600), 'wb') as file:
            image.save(file, format='PNG', optimize=True, pnginfo=metadata)
        with os.fdopen(os.open(output / draft_name, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600), 'w', encoding='utf-8') as file:
            json.dump(draft, file, ensure_ascii=False, indent=2)
            file.write('\n')
        similar = duplicates[number - 1]
        hint = ''
        if similar:
            others = ', '.join(f'№{item:02}' for item in similar)
            hint = f'<p class="duplicate"><strong>Возможный повтор:</strong> сравните с {others}. Совпали заголовок или адрес без меток; проверьте вручную.</p>'
        entries.append(f'<article><img src="{card_name}" alt="Карточка новости"><h2>№{number:02} · {html.escape(draft["title"])}</h2>{hint}<p>{html.escape(draft.get("description", ""))}</p><p><strong>Источник:</strong> {html.escape(draft.get("source_name", ""))}</p><p class="url">{html.escape(draft.get("source_url", ""))}</p></article>')
    page = '''<!doctype html><html lang="ru"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width"><title>Подборка SCM · черновики</title><style>body{margin:0;background:#081727;color:#eff8fa;font:16px/1.5 system-ui,sans-serif}main{max-width:1150px;margin:auto;padding:32px}h1{margin-bottom:8px}.notice{color:#b9d9dd}.grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(min(100%,310px),1fr));gap:22px;margin-top:28px}article{background:#102b42;border:1px solid #27516a;border-radius:18px;overflow:hidden;padding:0 18px 18px}img{width:calc(100% + 36px);margin:0 -18px;display:block}h2{font-size:19px}.url{overflow-wrap:anywhere;color:#8ccfc9;font-size:13px}.duplicate{background:#4a3922;border-left:3px solid #ffd07a;border-radius:6px;padding:10px;color:#fff1d6;font-size:14px}</style></head><body><main><h1>Подборка SCM</h1><p class="notice">Черновики: источники, права и факты не проверены. Добавьте собственный вывод. Ничего не отправлено в Telegram.</p><div class="grid">''' + ''.join(entries) + '</div></main></body></html>'
    with os.fdopen(os.open(output / 'index.html', os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600), 'w', encoding='utf-8') as file:
        file.write(page)
    return len(entries)


def main():
    parser = argparse.ArgumentParser(description='Создать локальную галерею карточек из подборки. Публикаций нет.')
    parser.add_argument('batch', type=Path)
    parser.add_argument('output', type=Path, help='Новый каталог галереи')
    args = parser.parse_args()
    try:
        with args.batch.open(encoding='utf-8') as file:
            batch = json.load(file)
        total = prepare(batch, args.output)
    except (OSError, ValueError, TypeError, KeyError) as exc:
        parser.exit(1, f'Галерея не создана полностью: {exc}. Если новый каталог появился, проверьте его вручную.\n')
    print(f'Создано карточек: {total}. Ничего не отправлено.')


if __name__ == '__main__':
    main()
