#!/usr/bin/env python3
"""
Bitrix24 Tools — Collector

Сбор данных из Bitrix24 в локальные снапшоты.

Использование:
    python collect.py --all           # Собрать всё
    python collect.py --quick         # Быстрый набор (tasks, calendar, crm, chats)
    python collect.py --module tasks  # Конкретный модуль
    python collect.py --list          # Показать модули
"""

import sys
import logging
import argparse
from pathlib import Path
from datetime import datetime
from typing import List, Dict

sys.path.insert(0, str(Path(__file__).parent))

from collectors.bitrix import (
    CRMCollector,
    TasksCollector,
    TaskCommentsCollector,
    CalendarCollector,
    ActivityCollector,
    UsersCollector,
    ContactsCollector,
    ChatsCollector,
    CompaniesCollector,
    DepartmentsCollector,
    CallsCollector,
)

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


COLLECTORS = {
    'crm': ('CRM сделки', CRMCollector),
    'tasks': ('Задачи', TasksCollector),
    'task_comments': ('Комментарии к задачам', TaskCommentsCollector),
    'calendar': ('Календарь', CalendarCollector),
    'activity': ('Активность', ActivityCollector),
    'users': ('Пользователи', UsersCollector),
    'contacts': ('Контакты', ContactsCollector),
    'chats': ('Чаты', ChatsCollector),
    'companies': ('Компании', CompaniesCollector),
    'departments': ('Отделы', DepartmentsCollector),
    'calls': ('Звонки', CallsCollector),
}

GROUPS = {
    'quick': ['tasks', 'calendar', 'activity', 'crm', 'chats'],
    'hourly': ['tasks', 'task_comments', 'calendar', 'activity', 'chats', 'calls'],
    'all': list(COLLECTORS.keys()),
}


def list_modules():
    print("\nДоступные модули:\n")
    for name, (desc, _) in COLLECTORS.items():
        print(f"  {name:15} — {desc}")
    print("\nГруппы:")
    for group, modules in GROUPS.items():
        print(f"  {group:15} — {', '.join(modules)}")
    print()


def run_collector(name: str) -> Dict:
    if name not in COLLECTORS:
        logger.error(f"Неизвестный модуль: {name}")
        return {'success': False, 'error': f'Unknown module: {name}'}

    desc, collector_class = COLLECTORS[name]
    logger.info(f"Запуск: {desc}")

    start = datetime.now()
    try:
        collector = collector_class()
        collector.run()
        duration = (datetime.now() - start).total_seconds()
        logger.info(f"{name} завершён за {duration:.1f}с")
        return {'success': True, 'module': name, 'duration': duration}
    except Exception as e:
        duration = (datetime.now() - start).total_seconds()
        logger.error(f"{name} ошибка: {e}")
        return {'success': False, 'module': name, 'duration': duration, 'error': str(e)}


def run_modules(modules: List[str]) -> Dict:
    results = {'modules': [], 'success': 0, 'failed': 0}
    total_start = datetime.now()

    for module in modules:
        result = run_collector(module)
        results['modules'].append(result)
        if result['success']:
            results['success'] += 1
        else:
            results['failed'] += 1

    results['total_duration'] = (datetime.now() - total_start).total_seconds()
    return results


def print_summary(results: Dict):
    print("\n" + "=" * 50)
    print("ИТОГИ СБОРА")
    print("=" * 50)

    for r in results['modules']:
        status = "OK" if r['success'] else "FAIL"
        print(f"  [{status}] {r['module']:15} ({r['duration']:.1f}с)")

    print("-" * 50)
    print(f"  Успешно: {results['success']}, Ошибок: {results['failed']}")
    print(f"  Время: {results['total_duration']:.1f}с")
    print("=" * 50 + "\n")


def main():
    parser = argparse.ArgumentParser(description='Bitrix24 Collector')
    parser.add_argument('--all', '-a', action='store_true', help='Собрать всё')
    parser.add_argument('--quick', '-q', action='store_true', help='Быстрый набор')
    parser.add_argument('--hourly', action='store_true', help='Часовой набор')
    parser.add_argument('--module', '-m', type=str, help='Конкретный модуль')
    parser.add_argument('--list', '-l', action='store_true', help='Показать модули')

    args = parser.parse_args()

    if args.list:
        list_modules()
        return

    modules = []
    if args.all:
        modules = GROUPS['all']
    elif args.quick:
        modules = GROUPS['quick']
    elif args.hourly:
        modules = GROUPS['hourly']
    elif args.module:
        modules = [args.module]

    if not modules:
        parser.print_help()
        print("\nУкажите модули: --all, --quick, --module <name>")
        return

    print(f"\nЗапуск: {', '.join(modules)}\n")
    results = run_modules(modules)
    print_summary(results)

    sys.exit(0 if results['failed'] == 0 else 1)


if __name__ == '__main__':
    main()
