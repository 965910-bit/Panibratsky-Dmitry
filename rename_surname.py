#!/usr/bin/env python3
import os
import re

# Расширения файлов, в которых будем менять текст
EXTENSIONS = ('.html', '.htm', '.js', '.css', '.json', '.xml', '.txt', '.md', '.rss', '.csv', '.yml', '.yaml')

# Словарь замен: что → на что (с учётом падежей)
REPLACEMENTS = {
    'Панибратский': 'Герасимов',
    'Панибратского': 'Герасимова',
    'Панибратскому': 'Герасимову',
    'Панибратским': 'Герасимовым',
    'Панибратском': 'Герасимове',
    'Дмитрий Панибратский': 'Дмитрий Герасимов',
    'Панибратский Дмитрий': 'Герасимов Дмитрий',
}

def replace_in_file(filepath):
    """Заменяет текст в файле, возвращает True, если были изменения."""
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            content = f.read()
    except UnicodeDecodeError:
        # Пробуем другую кодировку (например, для старых файлов)
        try:
            with open(filepath, 'r', encoding='latin-1') as f:
                content = f.read()
        except Exception:
            print(f'⚠️ Пропускаем (не удалось прочитать): {filepath}')
            return False

    new_content = content
    for old, new in REPLACEMENTS.items():
        new_content = new_content.replace(old, new)

    if new_content == content:
        return False  # ничего не изменилось

    # Записываем обновлённое содержимое
    with open(filepath, 'w', encoding='utf-8') as f:
        f.write(new_content)
    return True

def main():
    count = 0
    for root, dirs, files in os.walk('.'):
        # Исключаем системные папки и папки с медиа (чтобы не трогать бинарные файлы)
        dirs[:] = [d for d in dirs if d not in {
            '.git', '__pycache__', 'node_modules', 'venv', 'env', '.venv',
            'icons', 'images', 'videos', 'fonts', 'audio'
        }]
        for file in files:
            if file.lower().endswith(EXTENSIONS):
                filepath = os.path.join(root, file)
                if replace_in_file(filepath):
                    print(f'✅ Обновлён: {filepath}')
                    count += 1
    print(f'\n✨ Готово! Обработано файлов: {count}')

if __name__ == '__main__':
    main()
