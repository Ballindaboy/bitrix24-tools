#!/usr/bin/env python3
"""
Departments Collector - Собирает структуру отделов из Bitrix24

Собирает ВСЕ отделы компании с:
- ID
- Название (NAME)
- Родительский отдел (PARENT)
- Руководитель отдела (UF_HEAD)
- Сортировка (SORT)
"""

import logging
from typing import Dict, List
from collections import defaultdict

from shared import BaseCollector

logger = logging.getLogger(__name__)


class DepartmentsCollector(BaseCollector):
    """Собирает структуру отделов из Bitrix24"""

    def get_entity_name(self) -> str:
        return 'departments'

    def build_hierarchy(self, departments: List[Dict]) -> Dict:
        """
        Построить иерархию отделов для статистики

        Args:
            departments: Список отделов

        Returns:
            Словарь со статистикой по уровням
        """
        dept_levels = defaultdict(int)
        dept_dict = {d['ID']: d for d in departments}

        def get_level(dept_id: str) -> int:
            if dept_id in dept_levels:
                return dept_levels[dept_id]

            dept = dept_dict.get(dept_id)
            if not dept or 'PARENT' not in dept:
                dept_levels[dept_id] = 0
                return 0

            level = 1 + get_level(dept['PARENT'])
            dept_levels[dept_id] = level
            return level

        for dept in departments:
            get_level(dept['ID'])

        levels_count = defaultdict(int)
        for level in dept_levels.values():
            levels_count[level] += 1

        return {
            'max_depth': max(dept_levels.values()) if dept_levels else 0,
            'by_level': dict(sorted(levels_count.items()))
        }

    def collect(self) -> Dict:
        """
        Собрать структуру отделов компании

        Returns:
            Словарь с данными:
            {
                'source': 'bitrix24.department.get',
                'total': 18,
                'stats': {...},
                'departments': [...]
            }
        """
        logger.info("Fetching departments from Bitrix24...")

        departments = self.bitrix.get_all('department.get', {})

        logger.info(f"Retrieved {len(departments)} departments")

        # Статистика по руководителям
        with_head = sum(1 for d in departments if d.get('UF_HEAD'))
        without_head = len(departments) - with_head

        logger.info(f"With head: {with_head}, Without head: {without_head}")

        # Построить иерархию
        hierarchy = self.build_hierarchy(departments)
        logger.info(f"Max depth: {hierarchy['max_depth']}, Levels: {hierarchy['by_level']}")

        # Подсчитать корневые отделы
        root_count = sum(1 for d in departments if 'PARENT' not in d)

        return {
            'source': 'bitrix24.department.get',
            'total': len(departments),
            'stats': {
                'with_head': with_head,
                'without_head': without_head,
                'root_departments': root_count,
                'hierarchy': hierarchy
            },
            'departments': departments
        }


# Тестирование
if __name__ == '__main__':
    import sys
    from pathlib import Path
    sys.path.insert(0, str(Path(__file__).parent.parent.parent))

    logging.basicConfig(
        level=logging.INFO,
        format='%(levelname)s:%(name)s:%(message)s'
    )

    print("=== Testing DepartmentsCollector ===\n")

    try:
        collector = DepartmentsCollector()
        result = collector.run()

        if result:
            print("\n✅ Departments collector test passed!")
        else:
            print("\n❌ Departments collector test failed!")
            exit(1)

    except Exception as e:
        print(f"\n❌ Departments collector test failed: {e}")
        import traceback
        traceback.print_exc()
        exit(1)
