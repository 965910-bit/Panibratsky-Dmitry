"""Offline PNG card for a manually checked Telegram draft; never sends data."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import unicodedata

try:
    from PIL import Image, ImageDraw, ImageFont, PngImagePlugin
except ImportError as exc:
    raise SystemExit('Нужна Pillow: pip install -r telegram-review/requirements-visuals.txt') from exc

WIDTH, HEIGHT = 1080, 1080
FONT_REGULAR = '/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf'
FONT_BOLD = '/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf'


def clean(value, limit=1000):
    if not isinstance(value, str):
        return ''
    # Avoid hidden control/bidirectional characters and multiline layout manipulation.
    value = ''.join(' ' if unicodedata.category(c).startswith('C') else c for c in value)
    return re.sub(r'\s+', ' ', value).strip()[:limit]


def draft_fingerprint(draft):
    digest = hashlib.sha256()
    for field in ('title', 'source_name', 'source_url'):
        value = draft.get(field)
        data = (value if isinstance(value, str) else '').encode('utf-8')
        digest.update(len(data).to_bytes(4, 'big'))
        digest.update(data)
    return digest.hexdigest()


def wrap_title(draw, title, font, width, max_lines):
    """Split long words safely and explicitly mark content truncated on the image."""
    tokens = title.split()
    lines, current = [], ''
    for token in tokens:
        while token:
            candidate = (current + ' ' + token).strip()
            if draw.textlength(candidate, font=font) <= width:
                current = candidate
                token = ''
            elif current:
                lines.append(current)
                current = ''
            else:
                index = 1
                while index < len(token) and draw.textlength(token[:index + 1], font=font) <= width:
                    index += 1
                lines.append(token[:index])
                token = token[index:]
    if current:
        lines.append(current)
    if len(lines) > max_lines:
        lines = lines[:max_lines]
        while lines[-1] and draw.textlength(lines[-1] + '…', font=font) > width:
            lines[-1] = lines[-1][:-1]
        lines[-1] = lines[-1].rstrip() + '…'
    return lines


def make_card(draft, font_regular=FONT_REGULAR, font_bold=FONT_BOLD):
    if not isinstance(draft, dict) or draft.get('version') != 1:
        raise ValueError('Неверный формат черновика')
    title = clean(draft.get('title'), 240)
    if not title:
        raise ValueError('Для карточки нужен заголовок')
    source = clean(draft.get('source_name'), 70)
    font = ImageFont.truetype(font_bold, 57)
    small = ImageFont.truetype(font_bold, 25)
    regular = ImageFont.truetype(font_regular, 24)
    image = Image.new('RGB', (WIDTH, HEIGHT), '#0b1e32')
    draw = ImageDraw.Draw(image)
    # Simple reproducible shapes; no downloaded photos, statistics or external services.
    draw.rounded_rectangle((65, 62, 1015, 1018), radius=40, fill='#102b42', outline='#27516a', width=2)
    draw.rounded_rectangle((106, 112, 350, 160), radius=14, fill='#164656')
    draw.text((125, 120), 'SCM NEWS', font=small, fill='#75e2d6')
    draw.text((107, 219), 'ЛОГИСТИКА И SCM', font=small, fill='#87cbc9')
    draw.rounded_rectangle((107, 274, 193, 282), radius=4, fill='#57d2c7')
    lines = wrap_title(draw, title, font, 855, 7)
    y = 315
    for line in lines:
        draw.text((106, y), line, font=font, fill='#f4f9fb', stroke_width=0)
        y += 76
    draw.line((106, 892, 974, 892), fill='#2e6677', width=2)
    if source:
        source_line = 'Источник: ' + source
        while draw.textlength(source_line, font=regular) > 850:
            source_line = source_line[:-2] + '…' if not source_line.endswith('…') else source_line[:-2] + '…'
        draw.text((107, 914), source_line, font=regular, fill='#b5cfda')
    else:
        draw.text((107, 914), 'Источник — в тексте поста', font=regular, fill='#b5cfda')
    draw.text((107, 958), 'ЛЮДИ  →  ПРОЦЕССЫ  →  РЕЗУЛЬТАТ', font=small, fill='#75e2d6')
    return image


def main():
    parser = argparse.ArgumentParser(description='Создать локальную PNG-карточку из JSON-черновика. Публикаций нет.')
    parser.add_argument('draft', type=Path)
    parser.add_argument('output', type=Path, help='Новый PNG-файл, например private-drafts/card.png')
    parser.add_argument('--font-regular', default=FONT_REGULAR)
    parser.add_argument('--font-bold', default=FONT_BOLD)
    args = parser.parse_args()
    if args.output.suffix.lower() != '.png':
        parser.error('Файл карточки должен иметь расширение .png')
    try:
        with args.draft.open(encoding='utf-8') as source:
            draft = json.load(source)
        image = make_card(draft, args.font_regular, args.font_bold)
        # Exclusive creation prevents overwriting an existing image.
        fd = os.open(args.output, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
        with os.fdopen(fd, 'wb') as output:
            metadata = PngImagePlugin.PngInfo()
            metadata.add_text('SCM-Draft-SHA256', draft_fingerprint(draft))
            image.save(output, format='PNG', optimize=True, pnginfo=metadata)
    except (ValueError, OSError) as exc:
        parser.exit(1, f'Карточка не создана: {exc}\n')
    print('Карточка создана локально. Проверьте изображение и первоисточник перед использованием.')


if __name__ == '__main__':
    main()
