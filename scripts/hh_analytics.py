import json
import os
import time
from datetime import datetime, timedelta
from playwright.sync_api import sync_playwright

# -------------------------------------------------------------------
# 1. НАСТРОЙКИ
# -------------------------------------------------------------------
DATE_FROM = (datetime.now() - timedelta(days=30)).strftime("%Y-%m-%d")

# Слова для поиска (сократили до 2 самых важных, чтобы не грузить браузер)
WAREHOUSE_QUERIES = ["склад", "кладовщик"]
TRANSPORT_QUERIES = ["доставка", "перевозка грузов"]

# -------------------------------------------------------------------
# 2. ФУНКЦИЯ СБОРА ЧЕРЕЗ БРАУЗЕР (САМАЯ ВАЖНАЯ)
# -------------------------------------------------------------------
def fetch_hh_data(keyword):
    all_items = []
    page = 0
    
    print(f"  🌐 Открываю браузер для поиска: '{keyword}'...")
    
    with sync_playwright() as p:
        # Запускаем браузер (в GitHub он работает в фоне)
        browser = p.chromium.launch(headless=True)
        context = browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        )
        page_browser = context.new_page()
        
        while True:
            # Формируем ссылку для перехода
            url = f"https://api.hh.ru/vacancies?text={keyword}&date_from={DATE_FROM}&page={page}&per_page=100"
            
            try:
                print(f"     🕵️ Загружаю страницу {page+1}...")
                
                # Переходим по ссылке и ждем загрузки
                response = page_browser.goto(url, wait_until="domcontentloaded", timeout=30000)
                
                # Проверяем, что сервер ответил нормально
                if response.status != 200:
                    print(f"     ❌ Ошибка: {response.status}")
                    break
                
                # Получаем JSON-данные со страницы
                data = page_browser.evaluate("() => JSON.parse(document.body.innerText)")
                items = data.get('items', [])
                
                if not items:
                    print(f"     ✅ Все вакансии по слову '{keyword}' собраны. Итого: {len(all_items)}")
                    break
                
                all_items.extend(items)
                page += 1
                print(f"     ✔ Страница {page} загружена. Всего сейчас: {len(all_items)}.")
                
                # Пауза, чтобы не спамить (безопасная)
                time.sleep(2) 
                
            except Exception as e:
                print(f"     ❌ Критическая ошибка браузера: {e}")
                break
                
        browser.close()
            
    return all_items

# -------------------------------------------------------------------
# 3. ФУНКЦИЯ ОБЪЕДИНЕНИЯ (ОСТАЛАСЬ БЕЗ ИЗМЕНЕНИЙ)
# -------------------------------------------------------------------
def process_and_save(queries, output_filename):
    print(f"\n🔄 Запуск сбора для файла: {output_filename}")
    mega_list = []
    
    for query in queries:
        items = fetch_hh_data(query)
        mega_list.extend(items)
        
    unique_vacs = {v['id']: v for v in mega_list}.values()
    print(f"✅ Уникальных вакансий: {len(unique_vacs)}")
    
    if not unique_vacs:
        print("❌ Вакансий не найдено.")
        return

    analytics = {
        "total_vacancies": len(unique_vacs),
        "salary_stats": {"avg": 0, "min": 0, "max": 0},
        "top_skills": [],
        "experience_distribution": {"no_experience": 0, "between_1_and_3": 0, "between_3_and_6": 0, "more_than_6": 0},
        "avg_salary_by_region": {},
        "timeline": {},
        "updated_at": datetime.now().isoformat()
    }

    salaries = []
    for vac in unique_vacs:
        if vac.get('key_skills'):
            for skill in vac['key_skills']:
                name = skill['name'].lower()
                if name not in analytics:
                    analytics[name] = 0
                analytics[name] += 1
        
        sal = vac.get('salary')
        if sal and sal.get('from') and sal.get('currency') == 'RUR':
            salaries.append(sal['from'])
            
        region = vac.get('area', {}).get('name', 'Не указан')
        if sal and sal.get('from'):
            if region not in analytics['avg_salary_by_region']:
                analytics['avg_salary_by_region'][region] = []
            analytics['avg_salary_by_region'][region].append(sal['from'])
        
        exp = vac.get('experience', {}).get('id', 'no_experience')
        if exp in analytics['experience_distribution']:
            analytics['experience_distribution'][exp] += 1

        pub_date = vac.get('published_at', '')[:10]
        analytics['timeline'][pub_date] = analytics['timeline'].get(pub_date, 0) + 1

    sorted_skills = sorted([(k, v) for k, v in analytics.items() if k not in ['total_vacancies', 'salary_stats', 'top_skills', 'experience_distribution', 'avg_salary_by_region', 'timeline', 'updated_at']], key=lambda x: x[1], reverse=True)[:20]
    analytics['top_skills'] = [{"skill": k, "count": v} for k, v in sorted_skills]
    for k, v in sorted_skills:
        del analytics[k]

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

    os.makedirs("data", exist_ok=True)
    with open(f"data/{output_filename}", "w", encoding="utf-8") as f:
        json.dump(analytics, f, ensure_ascii=False, indent=2)
    
    print(f"✅ ГОТОВО! Файл {output_filename} сохранен.")
    print(f"   Вакансий: {analytics['total_vacancies']}")

# -------------------------------------------------------------------
# 4. ЗАПУСК
# -------------------------------------------------------------------
if __name__ == "__main__":
    process_and_save(WAREHOUSE_QUERIES, "hh_warehouse.json")
    process_and_save(TRANSPORT_QUERIES, "hh_transport.json")
    print("\n✅ ВСЕ ДАННЫЕ СОБРАНЫ. Скрипт завершил работу.")
