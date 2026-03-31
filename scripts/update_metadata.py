#!/usr/bin/env python
import json
import os
import re
from datetime import datetime

def update_metadata():
    trends_path = os.path.join(os.path.dirname(__file__), "..", "trends.html")
    if not os.path.exists(trends_path):
        print("trends.html not found")
        return

    with open(trends_path, "r", encoding="utf-8") as f:
        content = f.read()

    news_path = os.path.join(os.path.dirname(__file__), "..", "data", "news.json")
    news_items = []
    if os.path.exists(news_path):
        with open(news_path, "r", encoding="utf-8") as f:
            news_items = json.load(f)

    keywords = []
    for item in news_items[:5]:
        title = item.get("title", "")
        words = re.findall(r'\b[а-яё]{4,}\b', title.lower())
        keywords.extend(words[:3])
    keywords = list(dict.fromkeys(keywords))[:10]
    keyword_str = ", ".join(keywords) if keywords else "логистика, SCM, управление цепями поставок, новости логистики"

    month_name = datetime.now().strftime("%B %Y")
    title = f"Новости логистики и SCM {month_name} | Тренды управления цепями поставок"
    if keywords:
        title = f"{keyword_str[:50]}: {title}"

    description = f"Актуальные новости логистики, транспорта, склада и цифровой трансформации. {keyword_str}. Ежедневное обновление."

    # Replace title
    title_pattern = r'<title>.*?</title>'
    new_title = f'<title>{title}</title>'
    content = re.sub(title_pattern, new_title, content, flags=re.DOTALL)

    # Replace meta description
    desc_pattern = r'<meta name="description" content=".*?"/?>'
    new_desc = f'<meta name="description" content="{description}">'
    if re.search(desc_pattern, content):
        content = re.sub(desc_pattern, new_desc, content)
    else:
        content = re.sub(r'(<head>)', r'\1\n    ' + new_desc, content)

    with open(trends_path, "w", encoding="utf-8") as f:
        f.write(content)
    print("Metadata updated in trends.html")

if __name__ == "__main__":
    update_metadata()
