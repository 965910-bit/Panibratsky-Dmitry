#!/usr/bin/env python3
"""
Улучшенный сборщик аналитики с hh.ru.
Собирает данные отдельно по профессиональным ролям, фильтрует выбросы зарплат,
группирует регионы, строит распределение опыта и динамику.
Результат сохраняется в data/hh_analytics.json.
"""

import requests
import json
import time
from collections import defaultdict, Counter
from datetime import datetime, timedelta
import os
import re

# ==================== КОНФИГУРАЦИЯ ====================
# Профессиональные роли (ключевые слова, привязанные к конкретной должности)
ROLES = [
    {"name": "Логист", "keywords": ["логист", "менеджер по логистике", "специалист по логистике"]},
    {"name": "SCM / Цепи поставок", "keywords": ["менеджер по цепям поставок", "специалист по цепям поставок", "supply chain manager", "SCM"]},
    {"name": "Закупки / Снабжение", "keywords": ["менеджер по закупкам", "специалист по закупкам", "снабжение", "закупки"]},
    {"name": "Склад", "keywords": ["кладовщик", "начальник склада", "менеджер склада", "склад"]},
    {"name": "Транспорт", "keywords": ["транспортная логистика", "диспетчер", "менеджер по транспорту", "водитель"]},
]

# Параметры сбора
VACANCIES_PER_PAGE = 100   # макс. 100
MAX_PAGES_PER_ROLE = 5     # до 500 вакансий на роль (для Москвы, чтобы быстрее)
DELAY = 0.5                # задержка между запросами

# Регионы (коды hh.ru)
REGIONS = {
    1: "Москва",
    2: "Санкт-Петербург",
    113: "Россия"  # общий поиск по РФ, но для детализации используем регионы из вакансий
}

# Фильтр зарплат (убираем аномалии)
MIN_SALARY = 20000
MAX_SALARY = 500000

# Путь для сохранения
OUTPUT_FILE = "data/hh_analytics.json"

# ==================== ВСПОМОГАТЕЛЬНЫЕ ФУНКЦИИ ====================
def safe_get(data, *keys, default=None):
    for key in keys:
        if isinstance(data, dict):
            data = data.get(key, default)
        else:
            return default
    return data

def parse_salary(salary_data):
    """Преобразует зарплату в рублях, отсекает аномалии."""
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
    salary = int(salary)
    if salary < MIN_SALARY or salary > MAX_SALARY:
        return None
    return salary

def extract_skills(vacancy):
    skills = []
    key_skills = vacancy.get("key_skills", [])
    for skill in key_skills:
        skills.append(skill.get("name", "").strip())
    return skills

def get_experience(vacancy):
    exp = vacancy.get("experience")
    if not exp:
        return "unknown"
    exp_id = exp.get("id")
    mapping = {
        "noExperience": "no_experience",
        "between1And3": "between_1_and_3",
        "between3And6": "between_3_and_6",
        "moreThan6": "more_than_6"
    }
    return mapping.get(exp_id, "unknown")

def get_region_name(area):
    """Возвращает нормализованное название региона (город/область)."""
    if not area:
        return "unknown"
    name = area.get("name", "")
    # Упрощаем: если есть "Москва" – оставляем, иначе пробуем взять область
    if "Москва" in name:
        return "Москва"
    if "Санкт-Петербург" in name:
        return "Санкт-Петербург"
    # Убираем уточнения в скобках
    name = re.sub(r"\s*\(.*?\)", "", name).strip()
    # Слишком длинные названия обрезаем
    if len(name) > 20:
        name = name[:20]
    return name

# ==================== СБОР ВАКАНСИЙ ПО РОЛЯМ ====================
def fetch_vacancies_for_role(role_name, keywords, area=1):
    """
    Собирает вакансии для одной роли (поиск по ключевым словам через OR).
    Возвращает список вакансий.
    """
    # Формируем запрос: ключевые слова через OR
    query = " OR ".join([f'"{kw}"' for kw in keywords])
    base_url = "https://api.hh.ru/vacancies"
    params = {
        "text": query,
        "area": area,           # Москва для основного сбора (быстрее и репрезентативно)
        "per_page": VACANCIES_PER_PAGE,
        "only_with_salary": False
    }
    all_vacancies = []
    for page in range(MAX_PAGES_PER_ROLE):
        params["page"] = page
        try:
            resp = requests.get(base_url, params=params, timeout=10)
            if resp.status_code != 200:
                break
            data = resp.json()
            items = data.get("items", [])
            if not items:
                break
            all_vacancies.extend(items)
            if len(items) < VACANCIES_PER_PAGE:
                break
            time.sleep(DELAY)
        except Exception as e:
            print(f"Ошибка при сборе {role_name}, страница {page}: {e}")
            break
    print(f"Роль '{role_name}': собрано {len(all_vacancies)} вакансий")
    return all_vacancies

# ==================== АГРЕГАЦИЯ ПО РОЛЯМ ====================
def aggregate_role_data(vacancies):
    """Агрегирует данные для одного набора вакансий."""
    salaries = []
    salaries_by_region = defaultdict(list)
    skills_counter = Counter()
    regions_counter = Counter()
    experience_counter = Counter()
    timeline = defaultdict(int)

    for v in vacancies:
        # Дата
        pub_date = v.get("published_at")
        if pub_date:
            date_key = pub_date[:10]
            timeline[date_key] += 1

        # Зарплата
        salary = parse_salary(v.get("salary"))
        if salary:
            salaries.append(salary)
            region = get_region_name(v.get("area"))
            salaries_by_region[region].append(salary)

        # Навыки
        for skill in extract_skills(v):
            skills_counter[skill] += 1

        # Регион
        region = get_region_name(v.get("area"))
        regions_counter[region] += 1

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

    # Средняя зарплата по регионам (топ-10)
    avg_salary_by_region = {}
    for reg, sal_list in salaries_by_region.items():
        if sal_list:
            avg_salary_by_region[reg] = int(sum(sal_list) / len(sal_list))
    avg_salary_by_region = dict(sorted(avg_salary_by_region.items(), key=lambda x: x[1], reverse=True)[:10])

    # Топ навыков
    top_skills = skills_counter.most_common(10)

    # Топ регионов по количеству вакансий
    top_regions = regions_counter.most_common(10)

    # Динамика (последние 30 дней)
    dates = sorted(timeline.keys())
    cutoff = (datetime.now() - timedelta(days=30)).strftime("%Y-%m-%d")
    timeline_filtered = [{"date": d, "count": timeline[d]} for d in dates if d >= cutoff]

    # Распределение опыта
    exp_dist = [
        {"experience": exp, "count": count}
        for exp, count in experience_counter.items()
    ]

    return {
        "total_vacancies": len(vacancies),
        "salary_stats": salary_stats,
        "avg_salary_by_region": avg_salary_by_region,
        "top_skills": [{"skill": s, "count": c} for s, c in top_skills],
        "top_regions": [{"region": r, "count": c} for r, c in top_regions],
        "experience_distribution": exp_dist,
        "timeline": timeline_filtered
    }

# ==================== ГЛАВНАЯ ФУНКЦИЯ ====================
def main():
    print("Сбор аналитики hh.ru по ролям...")
    all_roles_data = {}
    total_vacancies = 0

    for role in ROLES:
        role_name = role["name"]
        keywords = role["keywords"]
        print(f"\n--- Сбор для роли: {role_name} ---")
        vacancies = fetch_vacancies_for_role(role_name, keywords, area=1)  # Москва
        if vacancies:
            role_data = aggregate_role_data(vacancies)
            all_roles_data[role_name] = role_data
            total_vacancies += len(vacancies)

    # Общая агрегация (все роли вместе)
    all_vacancies = []
    for role in ROLES:
        all_vacancies.extend(fetch_vacancies_for_role(role["name"], role["keywords"], area=1))
    overall_data = aggregate_role_data(all_vacancies)

    # Формируем итоговый JSON
    result = {
        "updated_at": datetime.now().isoformat(),
        "total_vacancies": total_vacancies,
        "roles": all_roles_data,
        "overall": overall_data
    }

    # Сохраняем
    os.makedirs(os.path.dirname(OUTPUT_FILE), exist_ok=True)
    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        json.dump(result, f, ensure_ascii=False, indent=2)
    print(f"\nСохранено в {OUTPUT_FILE}")

if __name__ == "__main__":
    main()
