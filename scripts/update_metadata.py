#!/usr/bin/env python
import json
import os
import re
from datetime import datetime

def update_metadata():
    # Путь к trends.html
    trends_path = os.path.join(os.path.dirname(__file__), "..", "trends.html")
    if not os.path.exists(trends_path):
        print("trends.html not found")
        return

    with open(trends_path, "r", encoding="utf-8") as f:
        content = f.read()

    # Загружаем новости
    news_path = os.path.join(os.path.dirname(__file__), "..", "data", "news.json")
    news_items = []
    if os.path.exists(news_path):
        with open(news_path, "r", encoding="utf-8") as f:
            news_items = json.load(f)

    # Формируем ключевые слова из заголовков новостей (первые 5)
    keywords = []
    for item in news_items[:5]:
        title = item.get("title", "")
        # Извлекаем слова длиной > 3 символа
        words = re.findall(r'\b[а-яё]{4,}\b', title.lower())
        keywords.extend(words[:3])
    # Убираем дубликаты, ограничиваем 10
    keywords = list(dict.fromkeys(keywords))[:10]
    keyword_str = ", ".join(keywords) if keywords else "логистика, SCM, управление цепями поставок, новости логистики"

    # Формируем title
    month_name = datetime.now().strftime("%B %Y")
    title = f"Новости логистики и SCM {month_name} | Тренды управления цепями поставок"
    # Можно добавить конкретные ключевые слова в начало, если есть
    if keywords:
        title = f"{keyword_str[:50]}: {title}"

    # Формируем description
    description = f"Актуальные новости логистики, транспорта, склада и цифровой трансформации. {keyword_str}. Ежедневное обновление."

    # Заменяем title
    title_pattern = r'<title>.*?</title>'
    new_title = f'<title>{title}</title>'
    content = re.sub(title_pattern, new_title, content, flags=re.DOTALL)

    # Заменяем meta description
    desc_pattern = r'<meta name="description" content=".*?"/?>'
    new_desc = f'<meta name="description" content="{description}">'
    if re.search(desc_pattern, content):
        content = re.sub(desc_pattern, new_desc, content)
    else:
        # Если нет, вставляем после <head>
        content = re.sub(r'(<head>)', r'\1\n    ' + new_desc, content)

    # Сохраняем
    with open(trends_path, "w", encoding="utf-8") as f:
        f.write(content)
    print("Metadata updated in trends.html")

if __name__ == "__main__":
    update_metadata()
