#!/usr/bin/env python3
"""Keep the news page's search snippet stable and readable."""
import re
from pathlib import Path

path = Path(__file__).resolve().parent.parent / 'trends.html'
content = path.read_text(encoding='utf-8')
content = re.sub(r'<title>.*?</title>', '<title>Новости логистики и SCM | Дмитрий Герасимов</title>', content, count=1, flags=re.DOTALL)
content = re.sub(r'<meta name="description" content=".*?"\s*/?>', '<meta name="description" content="Новости логистики, транспорта, складов и управления цепями поставок из открытых источников.">', content, count=1)
path.write_text(content, encoding='utf-8')
