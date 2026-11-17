import json
import os
import time
from datetime import datetime, timedelta, timezone
from collections import Counter
from urllib.parse import urlencode

# Playwright is imported only when collecting, so the aggregation can be tested offline.

# -------------------------------------------------------------------
# 1. НАСТРОЙКИ
# -------------------------------------------------------------------
DATE_FROM = (datetime.now(timezone.utc) - timedelta(days=30)).strftime("%Y-%m-%d")

# Слова для поиска (сократили до 2 самых важных, чтобы не грузить браузер)
WAREHOUSE_QUERIES = ["склад", "кладовщик"]
TRANSPORT_QUERIES = ["доставка", "перевозка грузов"]

class HHCollectionError(RuntimeError):
    """A short, non-sensitive category suitable for a CI annotation."""
    def __init__(self, reason, page=None, status=None, api_error=None):
        super().__init__('HH collection failed')
        self.reason = reason
        self.page = page
        self.status = status
        self.api_error = api_error


def failure_annotation(exc):
    # Never include exception messages, response bodies, URLs, query text or credentials.
    allowed = {'http_error', 'no_response', 'invalid_response', 'incomplete_page',
               'timeout', 'browser_error', 'no_results'}
    reason = exc.reason if isinstance(exc, HHCollectionError) and exc.reason in allowed else 'other_error'
    parts = [f'reason={reason}']
    if isinstance(exc, HHCollectionError) and type(exc.page) is int and 1 <= exc.page <= 10000:
        parts.append(f'page={exc.page}')
    if isinstance(exc, HHCollectionError) and type(exc.status) is int and 100 <= exc.status <= 599:
        parts.append(f'http={exc.status}')
    if isinstance(exc, HHCollectionError) and isinstance(exc.api_error, str) and exc.api_error in {'captcha_required', 'bad_authorization', 'token_expired', 'token_revoked', 'application_not_found', 'user_auth_expected', 'api_access_payment'}:
        parts.append(f'api_error={exc.api_error}')
    return '::error title=HH analytics::' + ' '.join(parts)


def classify_api_error(response):
    """Return only a documented, allowlisted error category, never response text or URLs."""
    try:
        body = response.body()
        if len(body) > 16384:
            return None
        payload = json.loads(body)
        if not isinstance(payload, dict) or not isinstance(payload.get('errors'), list):
            return None
        allowed = {'captcha_required', 'bad_authorization', 'token_expired',
                   'token_revoked', 'application_not_found', 'user_auth_expected',
                   'api_access_payment'}
        for item in payload['errors'][:20]:
            if isinstance(item, dict):
                for key in ('value', 'type'):
                    value = item.get(key)
                    if isinstance(value, str) and value in allowed:
                        return value
    except Exception:
        pass
    return None


# -------------------------------------------------------------------
# 2. ФУНКЦИЯ СБОРА ЧЕРЕЗ БРАУЗЕР (САМАЯ ВАЖНАЯ)
# -------------------------------------------------------------------
def fetch_hh_data(keyword):
    all_items = []
    page = 0
    
    print(f"  🌐 Открываю браузер для поиска: '{keyword}'...")
    
    from playwright.sync_api import sync_playwright
    with sync_playwright() as p:
        # Запускаем браузер (в GitHub он работает в фоне)
        browser = p.chromium.launch(headless=True)
        context = browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        )
        page_browser = context.new_page()
        
        while True:
            # Формируем ссылку для перехода
            url = "https://api.hh.ru/vacancies?" + urlencode({"text": keyword, "date_from": DATE_FROM, "page": page, "per_page": 100})
            
            try:
                print(f"     🕵️ Загружаю страницу {page+1}...")
                
                # Переходим по ссылке и ждем загрузки
                response = page_browser.goto(url, wait_until="domcontentloaded", timeout=30000)
                
                # Проверяем, что сервер ответил нормально
                if response is None:
                    raise HHCollectionError('no_response', page=page + 1)
                if response.status != 200:
                    raise HHCollectionError('http_error', page=page + 1, status=response.status,
                                            api_error=classify_api_error(response))
                
                # Получаем JSON-данные со страницы
                data = page_browser.evaluate("() => JSON.parse(document.body.innerText)")
                if not isinstance(data, dict):
                    raise HHCollectionError('invalid_response', page=page + 1)
                items = data.get('items')
                pages = data.get('pages')
                if not isinstance(items, list) or type(pages) is not int or pages < 0:
                    raise HHCollectionError('invalid_response', page=page + 1)
                if page < pages and not items:
                    raise HHCollectionError('incomplete_page', page=page + 1)

                all_items.extend(items)
                page += 1
                print(f"     ✔ Страница {page} загружена. Всего сейчас: {len(all_items)}.")
                if page >= pages:
                    break
                # Пауза между запросами.
                time.sleep(2) 
                
            except HHCollectionError:
                raise
            except Exception as exc:
                reason = 'timeout' if type(exc).__name__ == 'TimeoutError' else 'browser_error'
                raise HHCollectionError(reason, page=page + 1) from exc
                
        browser.close()
            
    return all_items

# -------------------------------------------------------------------
# 3. ФУНКЦИЯ ОБЪЕДИНЕНИЯ (ОСТАЛАСЬ БЕЗ ИЗМЕНЕНИЙ)
# -------------------------------------------------------------------
def collect_analytics(queries, output_filename):
    print(f"\n🔄 Запуск сбора для файла: {output_filename}")
    mega_list = []
    
    for query in queries:
        items = fetch_hh_data(query)
        mega_list.extend(items)
        
    unique_vacs = {v['id']: v for v in mega_list}.values()
    print(f"✅ Уникальных вакансий: {len(unique_vacs)}")
    
    if not unique_vacs:
        raise HHCollectionError('no_results')

    analytics = {
        "schema_version": 1,
        "source": "hh.ru API",
        "queries": list(queries),
        "date_from": DATE_FROM,
        "total_vacancies": len(unique_vacs),
        "salary_sample_size": 0,
        "salary_stats": {"avg": None, "min": None, "max": None},
        "top_skills": [],
        "experience_distribution": {"no_experience": 0, "between_1_and_3": 0, "between_3_and_6": 0, "more_than_6": 0},
        "avg_salary_by_region": {},
        "timeline": {},
        "updated_at": datetime.now(timezone.utc).isoformat()
    }

    salaries = []
    skills = Counter()
    for vac in unique_vacs:
        if vac.get('key_skills'):
            for skill in vac['key_skills']:
                name = skill.get('name')
                if isinstance(name, str) and name.strip():
                    skills[name.strip().lower()] += 1
        
        sal = vac.get('salary')
        if sal and isinstance(sal.get('from'), (int, float)) and not isinstance(sal['from'], bool) and 0 < sal['from'] < 1e10 and sal.get('currency') == 'RUR':
            salaries.append(sal['from'])
            
        region = vac.get('area', {}).get('name', 'Не указан')
        if sal and isinstance(sal.get('from'), (int, float)) and not isinstance(sal['from'], bool) and 0 < sal['from'] < 1e10 and sal.get('currency') == 'RUR':
            if region not in analytics['avg_salary_by_region']:
                analytics['avg_salary_by_region'][region] = []
            analytics['avg_salary_by_region'][region].append(sal['from'])
        
        exp = (vac.get('experience') or {}).get('id')
        if exp in analytics['experience_distribution']:
            analytics['experience_distribution'][exp] += 1

        pub_date = vac.get('published_at', '')[:10]
        analytics['timeline'][pub_date] = analytics['timeline'].get(pub_date, 0) + 1

    analytics['top_skills'] = [{"skill": k, "count": v} for k, v in skills.most_common(20)]
    analytics['salary_sample_size'] = len(salaries)

    for reg in analytics['avg_salary_by_region']:
        vals = analytics['avg_salary_by_region'][reg]
        analytics['avg_salary_by_region'][reg] = int(sum(vals) / len(vals))

    analytics['timeline'] = [{"date": k, "count": v} for k, v in sorted(analytics['timeline'].items())]

    if salaries:
        analytics['salary_stats'] = {
            "avg": int(sum(salaries) / len(salaries)),
            "min": min(salaries),
            "max": max(salaries)
        }

    return analytics


def main():
    # Both collections must succeed before either previously published file is replaced.
    outputs = {
        "hh_warehouse.json": collect_analytics(WAREHOUSE_QUERIES, "hh_warehouse.json"),
        "hh_transport.json": collect_analytics(TRANSPORT_QUERIES, "hh_transport.json"),
    }
    if os.environ.get('HH_DIAGNOSTIC_ONLY') == '1':
        print('Диагностика завершена: файлы не изменялись и публикация не выполнялась.')
        return
    os.makedirs("data", exist_ok=True)
    for filename, analytics in outputs.items():
        target = os.path.join("data", filename)
        temp = target + ".tmp"
        try:
            with open(temp, "w", encoding="utf-8") as f:
                json.dump(analytics, f, ensure_ascii=False, indent=2)
            os.replace(temp, target)
        finally:
            if os.path.exists(temp):
                os.unlink(temp)
        print(f"✅ {filename}: {analytics['total_vacancies']} вакансий")


def cli():
    try:
        main()
    except Exception as exc:
        print(failure_annotation(exc), flush=True)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(cli())
