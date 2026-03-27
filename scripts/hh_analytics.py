#!/usr/bin/env python3
"""
Сбор аналитики рынка труда по логистике, транспорту и цепям поставок.
Собирает данные отдельно по ключевым профессиональным ролям.
Группирует регионы по федеральным округам, фильтрует зарплаты.
Сохраняет JSON с детальной статистикой.
"""

import requests
import json
import time
from collections import defaultdict, Counter
from datetime import datetime, timedelta
import os
import re

# ==================== Конфигурация ====================
# Профессиональные роли (каждой соответствует набор ключевых слов для поиска)
ROLES = {
    "логист": [
        "логист", "менеджер по логистике", "специалист по логистике", "логистика"
    ],
    "SCM": [
        "менеджер по цепям поставок", "специалист по цепям поставок", "supply chain manager", "SCM"
    ],
    "закупки": [
        "менеджер по закупкам", "специалист по закупкам", "снабжение", "закупки"
    ],
    "склад": [
        "кладовщик", "менеджер склада", "заведующий складом", "оператор склада", "склад"
    ],
    "транспорт": [
        "транспортная логистика", "диспетчер", "менеджер по транспорту", "экспедитор", "транспорт"
    ]
}

# Регионы: используем коды HH, но для группировки будем использовать название региона
# Основные города и области выделим отдельно, остальные сгруппируем по федеральным округам.
# Для простоты оставим только Москва, СПб, Московская область, Ленинградская область,
# а остальные объединим в "Другие регионы". При желании можно расширить.
MAJOR_REGIONS = {
    "Москва": "Москва",
    "Санкт-Петербург": "Санкт-Петербург",
    "Московская область": "Московская область",
    "Ленинградская область": "Ленинградская область"
}
# Остальные регионы будем группировать по федеральным округам (упрощённо – "Другие регионы")

# Параметры сбора
VACANCIES_PER_PAGE = 100
MAX_PAGES_PER_ROLE = 3   # собираем до 300 вакансий на роль (можно увеличить)
DELAY = 0.5

# Путь для сохранения результата
OUTPUT_FILE = "data/hh_analytics.json"

# ==================== Вспомогательные функции ====================
def safe_get(data, *keys, default=None):
    for key in keys:
        if isinstance(data, dict):
            data = data.get(key, default)
        else:
            return default
    return data

def parse_salary(salary_data):
    """
    Преобразует данные о зарплате в число (рубли). Возвращает None, если не удалось.
    """
    if not salary_data:
        return None
    currency = salary_data.get("currency")
    if currency not in ["RUR", "rub"]:
        return None
    salary_from = salary_data.get("from")
    salary_to = salary_data.get("to")
    if salary_from and salary_to:
        salary = (salary_from + salary_to) / 2
    elif salary_from:
        salary = salary_from
    elif salary_to:
        salary = salary_to
    else:
        return None
    return int(salary)

def extract_skills(vacancy):
    """Извлекает навыки из вакансии (поле key_skills)."""
    skills = []
    key_skills = vacancy.get("key_skills", [])
    for skill in key_skills:
        name = skill.get("name", "").strip()
        if name:
            skills.append(name)
    return skills

def get_experience(vacancy):
    """Извлекает требуемый опыт."""
    exp = vacancy.get("experience")
    if not exp:
        return "unknown"
    exp_id = exp.get("id")
    if exp_id == "noExperience":
        return "no_experience"
    elif exp_id == "between1And3":
        return "between_1_and_3"
    elif exp_id == "between3And6":
        return "between_3_and_6"
    elif exp_id == "moreThan6":
        return "more_than_6"
    else:
        return "unknown"

def get_region_group(area_name):
    """Группирует регион в одну из категорий."""
    if area_name in MAJOR_REGIONS:
        return area_name
    # Упрощённо: всё остальное – "Другие регионы"
    return "Другие регионы"

def fetch_vacancies_for_role(keywords, area=113, max_pages=MAX_PAGES_PER_ROLE):
    """
    Загружает вакансии по списку ключевых слов (объединяет через OR).
    Возвращает список уникальных вакансий.
    """
    # Формируем запрос: слова через OR
    query = " OR ".join(f'"{kw}"' for kw in keywords)
    base_url = "https://api.hh.ru/vacancies"
    params = {
        "text": query,
        "area": area,
        "per_page": VACANCIES_PER_PAGE,
        "page": 0,
        "only_with_salary": False,
    }
    all_vacancies = []
    seen_ids = set()
    for page in range(max_pages):
        params["page"] = page
        try:
            response = requests.get(base_url, params=params, timeout=10)
            if response.status_code != 200:
                print(f"Ошибка {response.status_code} при запросе {query}, страница {page}")
                break
            data = response.json()
            items = data.get("items", [])
            if not items:
                break
            for v in items:
                v_id = v.get("id")
                if v_id not in seen_ids:
                    seen_ids.add(v_id)
                    all_vacancies.append(v)
            if len(items) < VACANCIES_PER_PAGE:
                break
            time.sleep(DELAY)
        except Exception as e:
            print(f"Исключение при запросе {query}: {e}")
            break
    print(f"Для роли {keywords[0] if keywords else '?'} загружено {len(all_vacancies)} вакансий.")
    return all_vacancies

def aggregate_role_data(vacancies):
    """
    Агрегирует данные для одной роли.
    Возвращает словарь с:
        total_vacancies
        salary_stats (avg, min, max, count)
        salary_by_region
        skills_counter
        experience_counter
        timeline (последние 30 дней)
    """
    salaries = []
    salaries_by_region = defaultdict(list)
    skills_counter = Counter()
    experience_counter = Counter()
    timeline = defaultdict(int)

    for v in vacancies:
        # Дата публикации
        pub_date = v.get("published_at")
        if pub_date:
            date_key = pub_date[:10]
            timeline[date_key] += 1

        # Зарплата
        salary_data = v.get("salary")
        salary = parse_salary(salary_data)
        if salary:
            # Фильтруем аномалии: от 20 тыс. до 500 тыс. руб.
            if 20000 <= salary <= 500000:
                salaries.append(salary)
                region_name = safe_get(v, "area", "name", default="unknown")
                region_group = get_region_group(region_name)
                salaries_by_region[region_group].append(salary)

        # Навыки
        skills = extract_skills(v)
        for skill in skills:
            skills_counter[skill] += 1

        # Опыт
        exp = get_experience(v)
        experience_counter[exp] += 1

    # Статистика зарплат
    salary_stats = {}
    if salaries:
        salary_stats = {
            "avg": int(sum(salaries) / len(salaries)),
            "min": min(salaries),
            "max": max(salaries),
            "count": len(salaries)
        }
    else:
        salary_stats = {"avg": 0, "min": 0, "max": 0, "count": 0}

    # Средняя зарплата по регионам
    avg_salary_by_region = {}
    for region, salary_list in salaries_by_region.items():
        if salary_list:
            avg_salary_by_region[region] = int(sum(salary_list) / len(salary_list))
    # Сортируем
    avg_salary_by_region = dict(sorted(avg_salary_by_region.items(), key=lambda x: x[1], reverse=True))

    # Топ навыков (10)
    top_skills = skills_counter.most_common(10)

    # Динамика (последние 30 дней)
    cutoff = datetime.now() - timedelta(days=30)
    filtered_timeline = {d: c for d, c in timeline.items() if datetime.strptime(d, "%Y-%m-%d") >= cutoff}
    timeline_list = [{"date": d, "count": c} for d, c in sorted(filtered_timeline.items())]

    return {
        "total_vacancies": len(vacancies),
        "salary_stats": salary_stats,
        "avg_salary_by_region": avg_salary_by_region,
        "top_skills": [{"skill": skill, "count": count} for skill, count in top_skills],
        "experience_distribution": [{"experience": exp, "count": count} for exp, count in experience_counter.items()],
        "timeline": timeline_list
    }

def main():
    print("Начинаем сбор вакансий по ролям...")
    all_data = {}
    for role_name, keywords in ROLES.items():
        print(f"\nОбрабатываем роль: {role_name}")
        vacancies = fetch_vacancies_for_role(keywords, area=113, max_pages=MAX_PAGES_PER_ROLE)
        if vacancies:
            all_data[role_name] = aggregate_role_data(vacancies)
        else:
            all_data[role_name] = None

    # Общая статистика (по всем ролям)
    # Собираем все вакансии вместе
    all_vacancies = []
    for role_name, keywords in ROLES.items():
        # повторно загружать не будем, но можно было бы объединить уже загруженные.
        # Для простоты загрузим общий набор по ключевым словам всех ролей.
        all_keywords = []
        for kw_list in ROLES.values():
            all_keywords.extend(kw_list)
        query = " OR ".join(f'"{kw}"' for kw in all_keywords)
        # Загрузим до 500 вакансий для общей картины
        all_vacancies = fetch_vacancies_for_role(all_keywords, area=113, max_pages=5)
    # Используем только первые 500 (если больше)
    all_vacancies = all_vacancies[:500]
    overall = aggregate_role_data(all_vacancies) if all_vacancies else None

    result = {
        "roles": all_data,
        "overall": overall,
        "updated_at": datetime.now().isoformat()
    }

    # Сохраняем JSON
    os.makedirs(os.path.dirname(OUTPUT_FILE), exist_ok=True)
    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        json.dump(result, f, ensure_ascii=False, indent=2)
    print(f"\nДанные сохранены в {OUTPUT_FILE}")

if __name__ == "__main__":
    main()
