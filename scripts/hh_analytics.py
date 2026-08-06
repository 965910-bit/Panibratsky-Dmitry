import requests
import json
import os
import time
from datetime import datetime, timedelta

# -------------------------------------------------------------------
# 1. НАСТРОЙКИ (Без CLIENT_ID — он нам больше не нужен)
# -------------------------------------------------------------------
DATE_FROM = (datetime.now() - timedelta(days=30)).strftime("%Y-%m-%d")

# Слова для поиска
WAREHOUSE_QUERIES = ["склад", "кладовщик"]
TRANSPORT_QUERIES = ["доставка", "перевозка грузов"]

# Заголовки, чтобы HH думал, что мы обычный пользователь
HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
}

# -------------------------------------------------------------------
# 2. ФУНКЦИЯ СБОРА (МЕДЛЕННАЯ И БЕЗОПАСНАЯ)
# -------------------------------------------------------------------
def fetch_all_pages(keyword):
    all_items = []
    page = 0
    per_page = 100
    
    print(f"  📥 Начинаю сбор по слову: '{keyword}'...")
    
    while True:
        # Убрали client_id из URL
        url = f"https://api.hh.ru/vacancies?text={keyword}&date_from={DATE_FROM}&page={page}&per_page={per_page}"
        
        try:
            # Отправляем запрос с заголовками браузера
            response = requests.get(url, headers=HEADERS)
            if response.status_code != 200:
                print(f"     ❌ Ошибка на странице {page+1}: {response.status_code}")
                break
                
            data = response.json()
            items = data.get('items', [])
            
            if not items:
                print(f"     ✅ По слову '{keyword}' собрано {len(all_items)} вакансий.")
                break
                
            all_items.extend(items)
            page += 1
            print(f"     ✔ Страница {page} загружена. Всего сейчас: {len(all_items)}.")
            
            # ДЕЛАЕМ БОЛЬШУЮ ПАУЗУ: 4 секунды между запросами
            time.sleep(4) 
            
        except Exception as e:
            print(f"     ❌ Критическая ошибка: {e}")
            break
            
    return all_items

# -------------------------------------------------------------------
# 3. ФУНКЦИЯ ОБЪЕДИНЕНИЯ И АНАЛИЗА
# -------------------------------------------------------------------
def process_and_save(queries, output_filename):
    print(f"\n🔄 Запуск сбора для файла: {output_filename}")
    mega_list = []
    
    for query in queries:
        items = fetch_all_pages(query)
        mega_list.extend(items)
        
    unique_vacs = {v['id']: v for v in mega_list}.values()
    print(f"✅ Уникальных вакансий после удаления дубликатов: {len(unique_vacs)}")
    
    if not unique_vacs:
        print("❌ Вакансий не найдено. Возможно, HH заблокировал запросы. Подождите 12-24 часа или попробуйте запустить позже.")
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
