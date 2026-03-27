#!/usr/bin/env python3
"""
Улучшенный сборщик аналитики с hh.ru.
Теперь получает навыки через дополнительный запрос к каждой вакансии.
Группирует регионы по городам, нормализует названия.
"""

import requests
import json
import time
from collections import defaultdict, Counter
from datetime import datetime, timedelta
import os
import re

# ==================== КОНФИГУРАЦИЯ ====================
ROLES = [
    {"name": "Логист", "keywords": ["логист", "менеджер по логистике", "специалист по логистике"]},
    {"name": "SCM / Цепи поставок", "keywords": ["менеджер по цепям поставок", "специалист по цепям поставок", "supply chain manager", "SCM"]},
    {"name": "Закупки / Снабжение", "keywords": ["менеджер по закупкам", "специалист по закупкам", "снабжение", "закупки"]},
    {"name": "Склад", "keywords": ["кладовщик", "начальник склада", "менеджер склада", "склад"]},
    {"name": "Транспорт", "keywords": ["транспортная логистика", "диспетчер", "менеджер по транспорту", "водитель"]},
]

VACANCIES_PER_PAGE = 100
MAX_PAGES_PER_ROLE = 10      # до 1000 вакансий на роль
DELAY = 0.5
MIN_SALARY = 20000
MAX_SALARY = 500000
OUTPUT_FILE = "data/hh_analytics.json"

# ==================== ФУНКЦИИ ====================
def safe_get(data, *keys, default=None):
    for key in keys:
        if isinstance(data, dict):
            data = data.get(key, default)
        else:
            return default
    return data

def parse_salary(salary_data):
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

def normalize_region(area):
    """Приводит название региона к нормализованному виду (город/область)."""
    if not area:
        return "unknown"
    name = area.get("name", "")
    # Обработка Москвы и области
    if "Москва" in name:
        if "Московская область" in name or "область" in name:
            return "Московская область"
        return "Москва"
    if "Санкт-Петербург" in name:
        return "Санкт-Петербург"
    if "Ленинградская область" in name:
        return "Ленинградская область"
    # Убираем уточнения в скобках
    name = re.sub(r"\s*\(.*?\)", "", name).strip()
    # Если название длинное, обрезаем
    if len(name) > 25:
        name = name[:25]
    return name

def fetch_skills(vacancy_id):
    """Получает список навыков для конкретной вакансии."""
    url = f"https://api.hh.ru/vacancies/{vacancy_id}"
    try:
        resp = requests.get(url, timeout=5)
        if resp.status_code == 200:
            data = resp.json()
            key_skills = data.get("key_skills", [])
            return [skill.get("name", "").strip() for skill in key_skills]
    except Exception:
        pass
    return []

def fetch_vacancies_for_role(role_name, keywords, area=1):
    """
    Собирает вакансии для роли, а затем для каждой запрашивает навыки.
    Возвращает список вакансий с обогащёнными данными.
    """
    query = " OR ".join([f'"{kw}"' for kw in keywords])
    base_url = "https://api.hh.ru/vacancies"
    params = {
        "text": query,
        "area": area,
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
            # Добавляем в список пока без навыков
            for item in items:
                item["skills"] = []
            all_vacancies.extend(items)
            if len(items) < VACANCIES_PER_PAGE:
                break
            time.sleep(DELAY)
        except Exception as e:
            print(f"Ошибка при сборе {role_name}, страница {page}: {e}")
            break

    print(f"Роль '{role_name}': собрано {len(all_vacancies)} вакансий, загружаем навыки...")
    # Загружаем навыки для каждой вакансии (можно распараллелить, но для простоты последовательно)
    for idx, vac in enumerate(all_vacancies):
        vac_id = vac.get("id")
        if vac_id:
            skills = fetch_skills(vac_id)
            vac["skills"] = skills
        if idx % 50 == 0:
            print(f"  Обработано {idx}/{len(all_vacancies)}")
        time.sleep(0.2)  # щадящий режим
    return all_vacancies

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
            region = normalize_region(v.get("area"))
            salaries_by_region[region].append(salary)

        # Навыки
        for skill in v.get("skills", []):
            if skill:
                skills_counter[skill] += 1

        # Регион
        region = normalize_region(v.get("area"))
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

def main():
    print("Сбор аналитики hh.ru по ролям (с получением навыков)...")
    all_roles_data = {}
    total_vacancies = 0

    for role in ROLES:
        role_name = role["name"]
        keywords = role["keywords"]
        print(f"\n--- Сбор для роли: {role_name} ---")
        vacancies = fetch_vacancies_for_role(role_name, keywords, area=1)
        if vacancies:
            role_data = aggregate_role_data(vacancies)
            all_roles_data[role_name] = role_data
            total_vacancies += len(vacancies)

    # Общая агрегация (собираем все вакансии из всех ролей, без дублирования)
    # Для простоты соберём их заново, объединив списки (но они уже есть в ролях, можно просто объединить)
    # Я сделаю новую агрегацию, объединив все собранные вакансии из ролей (чтобы не дублировать запросы)
    all_vacancies = []
    for role in ROLES:
        role_vac = fetch_vacancies_for_role(role["name"], role["keywords"], area=1)
        all_vacancies.extend(role_vac)
    overall_data = aggregate_role_data(all_vacancies)

    result = {
        "updated_at": datetime.now().isoformat(),
        "total_vacancies": total_vacancies,
        "roles": all_roles_data,
        "overall": overall_data
    }

    os.makedirs(os.path.dirname(OUTPUT_FILE), exist_ok=True)
    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        json.dump(result, f, ensure_ascii=False, indent=2)
    print(f"\nСохранено в {OUTPUT_FILE}")

if __name__ == "__main__":
    main()
