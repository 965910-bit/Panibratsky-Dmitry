import requests
import json
import os
import time
from datetime import datetime, timedelta

# -------------------------------------------------------------------
# 1. ВАШИ КЛЮЧИ И НАСТРОЙКИ
# -------------------------------------------------------------------
CLIENT_ID = "JRUEH60T2VRLA1BE0GTC5F3IL31MTS08R4HNQBDNLQCBG35IBA25ABR5DK2IHTQO" 
DATE_FROM = (datetime.now() - timedelta(days=30)).strftime("%Y-%m-%d")

# По 5 запросов на каждую тему, чтобы выкачать МАКСИМУМ (до 2000 на каждый запрос)
WAREHOUSE_QUERIES = [
    "склад", "складская логистика", "кладовщик", "заведующий складом", "комплектация заказов"
]

TRANSPORT_QUERIES = [
    "транспортная логистика", "доставка", "перевозка грузов", "диспетчер", "логист"
]

# -------------------------------------------------------------------
# 2. ФУНКЦИЯ БЕСКОНЕЧНОГО СБОРА (ЛИСТАЕТ СТРАНИЦЫ ПОКА НЕ КОНЧАТСЯ)
# -------------------------------------------------------------------
def fetch_all_pages(keyword):
    all_items = []
    page = 0
    per_page = 100  # Максимум, что отдает HH за раз
    
    print(f"  📥 Начинаю сбор по слову: '{keyword}'...")
    
    while True:
        url = f"https://api.hh.ru/vacancies?text={keyword}&date_from={DATE_FROM}&page={page}&per_page={per_page}&client_id={CLIENT_ID}"
        
        try:
            response = requests.get(url)
            if response.status_code != 200:
                print(f"     ❌ Ошибка на странице {page+1}: {response.status_code}")
                break
                
            data = response.json()
            items = data.get('items', [])
            
            # Если вакансий на странице нет — значит, всё скачали
            if not items:
                print(f"     ✅ По слову '{keyword}' собрано {len(all_items)} вакансий.")
                break
                
            all_items.extend(items)
            page += 1
            print(f"     ✔ Страница {page} загружена. Всего сейчас: {len(all_items)} вакансий.")
            
            # Пауза, чтобы HH не заблокировал нас
            time.sleep(0.5) 
            
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
    
    # 1. Проходим по каждому запросу и качаем ВСЁ
    for query in queries:
        items = fetch_all_pages(query)
        mega_list.extend(items)
        
    # 2. Удаляем дубликаты по ID
    unique_vacs = {v['id']: v for v in mega_list}.values()
    print(f"✅ Уникальных вакансий после удаления дубликатов: {len(unique_vacs)}")
    
    if not unique_vacs:
        print("❌ Вакансий не найдено.")
        return

    # 3. Создаем структуру для анализа
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
        # Навыки
        if vac.get('key_skills'):
            for skill in vac['key_skills']:
                name = skill['name'].lower()
                if name not in analytics:
                    analytics[name] = 0
                analytics[name] += 1
        
        # Зарплаты (только рубли)
        sal = vac.get('salary')
        if sal and sal.get('from') and sal.get('currency') == 'RUR':
            salaries.append(sal['from'])
            
        # Регионы
        region = vac.get('area', {}).get('name', 'Не указан')
        if sal and sal.get('from'):
            if region not in analytics['avg_salary_by_region']:
                analytics['avg_salary_by_region'][region] = []
            analytics['avg_salary_by_region'][region].append(sal['from'])
        
        # Опыт
        exp = vac.get('experience', {}).get('id', 'no_experience')
        if exp in analytics['experience_distribution']:
            analytics['experience_distribution'][exp] += 1

        # Дата публикации
        pub_date = vac.get('published_at', '')[:10]
        analytics['timeline'][pub_date] = analytics['timeline'].get(pub_date, 0) + 1

    # Обработка топ-20 навыков
    sorted_skills = sorted(
        [(k, v) for k, v in analytics.items() if k not in ['total_vacancies', 'salary_stats', 'top_skills', 'experience_distribution', 'avg_salary_by_region', 'timeline', 'updated_at']], 
        key=lambda x: x[1], reverse=True
    )[:20]
    analytics['top_skills'] = [{"skill": k, "count": v} for k, v in sorted_skills]
    for k, v in sorted_skills:
        del analytics[k]

    # Средняя зарплата по регионам
    for reg in analytics['avg_salary_by_region']:
        vals = analytics['avg_salary_by_region'][reg]
        analytics['avg_salary_by_region'][reg] = int(sum(vals) / len(vals))

    # График по дням
    analytics['timeline'] = [{"date": k, "count": v} for k, v in sorted(analytics['timeline'].items())]

    # Общая статистика по зарплатам
    if salaries:
        analytics['salary_stats'] = {
            "avg": int(sum(salaries) / len(salaries)),
            "min": min(salaries),
            "max": max(salaries)
        }

    # 4. Сохранение
    os.makedirs("data", exist_ok=True)
    with open(f"data/{output_filename}", "w", encoding="utf-8") as f:
        json.dump(analytics, f, ensure_ascii=False, indent=2)
    
    print(f"✅ ГОТОВО! Файл {output_filename} сохранен.")
    print(f"   Итоговое количество вакансий: {analytics['total_vacancies']}")
    print(f"   Средняя зарплата: {analytics['salary_stats']['avg']} руб.")

# -------------------------------------------------------------------
# 4. ЗАПУСК
# -------------------------------------------------------------------
if __name__ == "__main__":
    process_and_save(WAREHOUSE_QUERIES, "hh_warehouse.json")
    process_and_save(TRANSPORT_QUERIES, "hh_transport.json")
    print("\n✅ ВСЕ ДАННЫЕ СОБРАНЫ. Скрипт завершил работу.")
