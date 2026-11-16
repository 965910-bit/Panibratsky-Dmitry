"""Check news links conservatively: outages and bot blocks are not broken links."""
import json
import os
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
import requests

NEWS_FILE = Path(__file__).resolve().parent.parent / 'data' / 'news.json'


def check_url(url):
    try:
        response = requests.get(url, timeout=10, allow_redirects=True, stream=True)
        try:
            if response.status_code in (404, 410):
                return 'missing'
            if response.status_code < 400:
                return 'alive'
            return 'unknown'
        finally:
            response.close()
    except requests.RequestException:
        return 'unknown'


def main():
    if not NEWS_FILE.exists():
        raise FileNotFoundError(NEWS_FILE)
    news = json.loads(NEWS_FILE.read_text(encoding='utf-8'))
    # Recheck previously marked items so a transient 404 can recover.
    to_check = [(i, item['link']) for i, item in enumerate(news) if isinstance(item.get('link'), str) and item['link'].startswith(('http://', 'https://'))]
    changed = False
    with ThreadPoolExecutor(max_workers=10) as executor:
        futures = {executor.submit(check_url, url): i for i, url in to_check}
        for future in as_completed(futures):
            item = news[futures[future]]
            status = future.result()
            if status == 'missing' and not item.get('dead'):
                item['dead'] = True
                changed = True
            elif status == 'alive' and item.pop('dead', None) is not None:
                changed = True
    if changed:
        temp = NEWS_FILE.with_suffix('.json.tmp')
        try:
            temp.write_text(json.dumps(news, ensure_ascii=False, indent=2), encoding='utf-8')
            os.replace(temp, NEWS_FILE)
        finally:
            temp.unlink(missing_ok=True)
    print(f'Checked {len(to_check)} links; modified: {changed}')

if __name__ == '__main__':
    main()
