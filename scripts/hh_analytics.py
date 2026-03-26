#!/usr/bin/env python3
"""
Скрипт для сбора аналитики рынка труда по логистике, транспорту и цепям поставок.
Использует открытый API HeadHunter (https://api.hh.ru).
Собирает вакансии по ключевым словам, агрегирует данные по зарплатам, навыкам, регионам, опыту.
Сохраняет результат в JSON для дальнейшей визуализации в кабинете.
Запускается по расписанию через GitHub Actions.
"""

import requests
import json
import time
from collections import defaultdict, Counter
from datetime import datetime, timedelta
import os
import re

# ==================== Конфигурация ====================
# Ключевые слова для поиска (охватывают всю область SCM, логистики, транспорта)
KEYWORDS = [
    "логист",
    "менеджер по цепям поставок",
    "специалист по цепям поставок",
    "снабжение",
    "закупки",
    "склад",
    "транспортная логистика",
    "SCM",
    "supply chain manager",
    "менеджер по закупкам",
    "менеджер по логистике",
    "кладовщик",
    "диспетчер",
    "логистика",
    "цепи поставок",
    "управление запасами",
    "транспорт",
    "экспедитор",
]

# Регионы: коды областей HH (Москва, СПб, Россия в целом)
# Полный список: https://api.hh.ru/areas
REGIONS = {
    1: "Москва",
    2: "Санкт-Петербург",
    113: "Россия"  # вся страна
}

# Параметры сбора
VACANCIES_PER_PAGE = 100   # максимальное значение для API (не более 100)
MAX_PAGES_PER_KEYWORD = 3   # собираем до 300 вакансий на ключевое слово (можно увеличить до 5-10)
DELAY = 0.5                 # задержка между запросами, чтобы не превысить лимиты API

# Путь для сохранения результата
OUTPUT_FILE = "data/hh_analytics.json"

# ==================== Вспомогательные функции ====================
def safe_get(data, *keys, default=None):
    """Безопасное получение значения из вложенного словаря."""
    for key in keys:
        if isinstance(data, dict):
            data = data.get(key, default)
        else:
            return default
    return data

def parse_salary(salary_data):
    """
    Преобразует данные о зарплате из API в числовое значение (в рублях).
    Возвращает None, если зарплата не указана.
    """
    if not salary_data:
        return None
    # Если зарплата указана в валюте, отличной от RUR, конвертируем (грубо: все в рубли)
    currency = salary_data.get("currency")
    if currency not in ["RUR", "rub"]:
        # Для простоты пропускаем вакансии в иностранной валюте
        return None
    # Берём среднее между from и to, если указаны оба, иначе то, что есть
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
    """
    Извлекает требуемые навыки из вакансии.
    Сначала пытается взять из поля key_skills, если нет – из описания (description).
    """
    skills = []
    # Проверяем наличие key_skills (структура: [{"name": "..."}])
    key_skills = vacancy.get("key_skills", [])
    for skill in key_skills:
        skills.append(skill.get("name", "").strip())
    # Если skills не найдены, можно добавить простой парсинг из description (не обязательно)
    # Но для простоты пока только key_skills.
    return skills

def get_experience(vacancy):
    """
    Извлекает требуемый опыт из вакансии.
    Возвращает строку: "no_experience", "between_1_and_3", "between_3_and_6", "more_than_6"
    """
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

def fetch_vacancies(keyword, area=113):
    """
    Загружает вакансии для заданного ключевого слова и региона.
    Возвращает список вакансий (словарей).
    """
    base_url = "https://api.hh.ru/vacancies"
    params = {
        "text": keyword,
        "area": area,
        "per_page": VACANCIES_PER_PAGE,
        "page": 0,
        "only_with_salary": False,  # можно установить True, если нужны только с зарплатой
    }
    all_vacancies = []
    total_found = None
    for page in range(MAX_PAGES_PER_KEYWORD):
        params["page"] = page
        try:
            response = requests.get(base_url, params=params, timeout=10)
            if response.status_code != 200:
                print(f"Ошибка при запросе для {keyword}, страница {page}: {response.status_code}")
                break
            data = response.json()
            if total_found is None:
                total_found = data.get("found", 0)
                print(f"По ключевому слову '{keyword}' найдено {total_found} вакансий.")
            items = data.get("items", [])
            if not items:
                break
            all_vacancies.extend(items)
            # Если получено меньше, чем запрошено, это последняя страница
            if len(items) < VACANCIES_PER_PAGE:
                break
            time.sleep(DELAY)
        except Exception as e:
            print(f"Ошибка при загрузке вакансий для {keyword}, страница {page}: {e}")
            break
    print(f"Для '{keyword}' загружено {len(all_vacancies)} вакансий.")
    return all_vacancies

def collect_all_vacancies():
    """Собирает вакансии по всем ключевым словам и регионам (только Россия)."""
    all_vacancies = []
    seen_ids = set()  # для удаления дубликатов
    for keyword in KEYWORDS:
        # Для простоты собираем только по России (area=113)
        vacancies = fetch_vacancies(keyword, area=113)
        for v in vacancies:
            v_id = v.get("id")
            if v_id not in seen_ids:
                seen_ids.add(v_id)
                all_vacancies.append(v)
        time.sleep(DELAY)
    print(f"Всего собрано уникальных вакансий: {len(all_vacancies)}")
    return all_vacancies

def aggregate_data(vacancies):
    """
    Агрегирует данные по зарплатам, навыкам, регионам, опыту.
    Возвращает словарь с результатами.
    """
    salaries = []          # список зарплат (для среднего)
    salaries_by_region = defaultdict(list)
    salaries_by_experience = defaultdict(list)
    skills_counter = Counter()
    regions_counter = Counter()
    experience_counter = Counter()
    vacancies_by_date = defaultdict(int)  # по дням (для динамики)

    for v in vacancies:
        # Дата публикации (для динамики)
        published_at = v.get("published_at")
        if published_at:
            date_key = published_at[:10]  # YYYY-MM-DD
            vacancies_by_date[date_key] += 1

        # Зарплата
        salary_data = v.get("salary")
        salary = parse_salary(salary_data)
        if salary:
            salaries.append(salary)

            # Зарплата по регионам
            area = v.get("area", {})
            region_name = area.get("name", "unknown")
            salaries_by_region[region_name].append(salary)

            # Зарплата по опыту
            exp = get_experience(v)
            salaries_by_experience[exp].append(salary)

        # Навыки
        skills = extract_skills(v)
        for skill in skills:
            if skill:
                skills_counter[skill] += 1

        # Регионы
        area = v.get("area", {})
        region_name = area.get("name", "unknown")
        regions_counter[region_name] += 1

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
    for region, salary_list in salaries_by_region.items():
        if salary_list:
            avg_salary_by_region[region] = int(sum(salary_list) / len(salary_list))
    # Сортируем по убыванию
    avg_salary_by_region = dict(sorted(avg_salary_by_region.items(), key=lambda x: x[1], reverse=True))

    # Средняя зарплата по опыту
    avg_salary_by_experience = {}
    for exp, salary_list in salaries_by_experience.items():
        if salary_list:
            avg_salary_by_experience[exp] = int(sum(salary_list) / len(salary_list))

    # Топ навыков (10)
    top_skills = skills_counter.most_common(10)

    # Топ регионов (10)
    top_regions = regions_counter.most_common(10)

    # Динамика вакансий по датам (последние 30 дней)
    # Преобразуем словарь в список для удобства
    dates = sorted(vacancies_by_date.keys())
    # Ограничим последними 30 днями
    cutoff_date = (datetime.now() - timedelta(days=30)).strftime("%Y-%m-%d")
    filtered_dates = [d for d in dates if d >= cutoff_date]
    timeline = [{"date": d, "count": vacancies_by_date[d]} for d in filtered_dates]

    # Возвращаем агрегированный результат
    result = {
        "total_vacancies": len(vacancies),
        "salary_stats": salary_stats,
        "avg_salary_by_region": avg_salary_by_region,
        "avg_salary_by_experience": avg_salary_by_experience,
        "top_skills": [{"skill": skill, "count": count} for skill, count in top_skills],
        "top_regions": [{"region": region, "count": count} for region, count in top_regions],
        "experience_distribution": [{"experience": exp, "count": count} for exp, count in experience_counter.items()],
        "timeline": timeline,
        "updated_at": datetime.now().isoformat()
    }
    return result

def save_to_json(data, filepath):
    """Сохраняет результат в JSON."""
    os.makedirs(os.path.dirname(filepath), exist_ok=True)
    with open(filepath, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    print(f"Данные сохранены в {filepath}")

def main():
    print("Начинаем сбор вакансий...")
    vacancies = collect_all_vacancies()
    print("Агрегируем данные...")
    analytics = aggregate_data(vacancies)
    save_to_json(analytics, OUTPUT_FILE)
    print("Готово.")

if __name__ == "__main__":
    main()
