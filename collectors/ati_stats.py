import requests
from bs4 import BeautifulSoup
import json
import re
from datetime import datetime

class ATIStatsCollector:
    def __init__(self):
        self.headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
        }

    def fetch_indexes(self):
        url = "https://ati.su/statistics/indexes"
        try:
            resp = requests.get(url, headers=self.headers, timeout=10)
            resp.raise_for_status()
            soup = BeautifulSoup(resp.text, 'html.parser')
            # Пример парсинга (нужно уточнить реальную структуру)
            values = []
            for item in soup.select(".index-value"):
                values.append(item.text.strip())
            return {"timestamp": datetime.now().isoformat(), "values": values}
        except Exception as e:
            print(f"ATI error: {e}")
            return None
