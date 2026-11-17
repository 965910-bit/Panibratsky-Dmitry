"""Check explicitly approved news hosts; failures and redirects are not broken links."""
import json
import os
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from urllib.parse import urlsplit
import requests

NEWS_FILE = Path(__file__).resolve().parent.parent / 'data' / 'news.json'
# Exact hostnames only. Add a host only after documenting permission for automated
# link checks and the permitted rate; a public page or RSS feed is not consent.
# Currently no host has been cleared. Paused ATI and Logistics 360 must not be added.
APPROVED_HOSTS = frozenset()


def approved_url(url):
    if not isinstance(url, str) or not url or url != url.strip():
        return False
    try:
        parsed = urlsplit(url)
        host = (parsed.hostname or '').lower().rstrip('.')
        return (parsed.scheme == 'https' and host in APPROVED_HOSTS and
                parsed.username is None and parsed.password is None and
                parsed.port in (None, 443))
    except ValueError:
        return False


def check_url(url):
    # Defense in depth even when invoked independently of main().
    if not approved_url(url):
        return 'unknown'
    try:
        response = requests.get(url, timeout=10, allow_redirects=False, stream=True)
        try:
            if response.status_code in (404, 410):
                return 'missing'
            if 200 <= response.status_code < 300:
                return 'alive'
            # A redirect may lead to an unapproved host. Never follow it automatically.
            return 'unknown'
        finally:
            response.close()
    except requests.RequestException:
        return 'unknown'


def main():
    if not NEWS_FILE.exists():
        raise FileNotFoundError(NEWS_FILE)
    news = json.loads(NEWS_FILE.read_text(encoding='utf-8'))
    if not isinstance(news, list):
        raise ValueError('Expected a news list')
    # Recheck previously marked items only when their host is approved.
    to_check = [(i, item['link']) for i, item in enumerate(news)
                if isinstance(item, dict) and approved_url(item.get('link'))]
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
    print(f'Checked {len(to_check)} approved links; skipped {len(news) - len(to_check)} entries; modified: {changed}')
    if not APPROVED_HOSTS:
        print('::warning::No approved hosts; link checks were skipped, not verified.')

if __name__ == '__main__':
    main()
