#!/usr/bin/env python3
import os
import re
import shutil

OLD_DOMAIN = "https://965910-bit.github.io/Panibratsky-Dmitry"
NEW_DOMAIN = "https://scm-news.ru"

# Расширения файлов, в которых будем заменять ссылки
EXTENSIONS = ('.html', '.xml', '.js', '.txt', '.json', '.css', '.md', '.rss')

# Папки, которые нужно исключить (например, .git, __pycache__)
EXCLUDE_DIRS = {'.git', '__pycache__', 'node_modules', 'venv', 'env', '.venv'}

def should_process_file(filepath):
    """Проверяет, нужно ли обрабатывать файл."""
    return filepath.lower().endswith(EXTENSIONS)

def backup_file(filepath):
    """Создаёт резервную копию файла с расширением .bak"""
    backup_path = filepath + '.bak'
    shutil.copy2(filepath, backup_path)
    print(f"  📁 Бэкап: {backup_path}")

def replace_links_in_file(filepath):
    """Заменяет старый домен на новый в содержимом файла."""
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            content = f.read()
    except UnicodeDecodeError:
        # Пробуем другую кодировку или пропускаем бинарные файлы
        try:
            with open(filepath, 'r', encoding='latin-1') as f:
                content = f.read()
        except:
            print(f"  ⚠️ Не удалось прочитать (вероятно, бинарный): {filepath}")
            return False

    new_content = content.replace(OLD_DOMAIN, NEW_DOMAIN)
    
    # Если есть ссылки вида "https://965910-bit.github.io/Panibratsky-Dmitry" без слеша в конце, то уже заменились.
    # Дополнительно можно заменить и просто старый путь (на случай, если где-то не хватает https)
    # Например, "965910-bit.github.io/Panibratsky-Dmitry" -> "scm-news.ru"
    # Но лучше оставить только первое.

    if new_content == content:
        return False  # ничего не изменилось

    with open(filepath, 'w', encoding='utf-8') as f:
        f.write(new_content)
    return True

def main():
    print("🚀 Замена ссылок со старого домена на новый")
    print(f"   Старый: {OLD_DOMAIN}")
    print(f"   Новый:  {NEW_DOMAIN}\n")
    
    count_changed = 0
    for root, dirs, files in os.walk('.'):
        # Исключаем указанные директории
        dirs[:] = [d for d in dirs if d not in EXCLUDE_DIRS]
        
        for file in files:
            filepath = os.path.join(root, file)
            if should_process_file(filepath):
                # Создаём бэкап перед изменениями
                backup_file(filepath)
                if replace_links_in_file(filepath):
                    print(f"  ✅ Изменён: {filepath}")
                    count_changed += 1
                else:
                    # Если не изменилось, удаляем пустой бэкап (опционально)
                    bak_path = filepath + '.bak'
                    if os.path.exists(bak_path):
                        os.remove(bak_path)
    
    print(f"\n✨ Готово! Обработано файлов: {count_changed}")
    print("⚠️  ВНИМАНИЕ: Созданы резервные копии с расширением .bak.")
    print("   Если всё работает, удалите их командой: find . -name '*.bak' -delete")
    print("   Или вручную.")

if __name__ == "__main__":
    main()
