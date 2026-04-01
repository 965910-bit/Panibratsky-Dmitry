import json
import os
import requests
from concurrent.futures import ThreadPoolExecutor, as_completed

def check_url(url):
    try:
        r = requests.get(url, timeout=10, allow_redirects=True)
        return url, r.status_code < 400
    except Exception:
        return url, False

def main():
    news_file = os.path.join(os.path.dirname(__file__), "..", "data", "news.json")
    if not os.path.exists(news_file):
        print("news.json not found")
        return

    with open(news_file, "r", encoding="utf-8") as f:
        news = json.load(f)

    to_check = [(i, item) for i, item in enumerate(news) if not item.get('dead')]
    if not to_check:
        print("No new links to check")
        return

    print(f"Checking {len(to_check)} links...")
    with ThreadPoolExecutor(max_workers=10) as executor:
        futures = {executor.submit(check_url, item['link']): idx for idx, item in to_check}
        for future in as_completed(futures):
            idx = futures[future]
            url, alive = future.result()
            if not alive:
                print(f"Broken link: {url}")
                news[idx]['dead'] = True

    with open(news_file, "w", encoding="utf-8") as f:
        json.dump(news, f, ensure_ascii=False, indent=2)

    print("Done")

if __name__ == "__main__":
    main()
