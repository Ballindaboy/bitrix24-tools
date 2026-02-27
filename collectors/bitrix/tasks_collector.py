#!/usr/bin/env python3
"""
Tasks Collector - Собирает задачи из Bitrix24

Собирает задачи за последний год:
- Все поля задач
- Теги, чек-листы, наблюдатели
- Фильтр по CHANGED_DATE (обновлённые за последние 365 дней)
"""

import logging
from typing import Dict
from collections import Counter
from datetime import datetime, timedelta

from shared import BaseCollector

logger = logging.getLogger(__name__)


class TasksCollector(BaseCollector):
    """Собирает задачи из Bitrix24 (обновлённые за последний год)"""

    def get_entity_name(self) -> str:
        return 'tasks'

    def collect(self) -> Dict:
        """
        Собрать задачи за последний год (обновлённые)

        Returns:
            Словарь с данными:
            {
                'source': 'tasks.task.list',
                'filter': '>=CHANGED_DATE: YYYY-MM-DD',
                'total': 1234,
                'tasks': [...]
            }
        """
        # Вычислить дату год назад
        one_year_ago = datetime.now() - timedelta(days=365)
        filter_date = one_year_ago.strftime('%Y-%m-%dT00:00:00')

        logger.info(f"Fetching tasks from Bitrix24 (changed >= {filter_date})...")

        # Получить задачи за последний год
        tasks = self.bitrix.get_all('tasks.task.list', {
            'filter': {
                '>=CHANGED_DATE': filter_date
            },
            'select': ['*']
        })

        logger.info(f"Retrieved {len(tasks)} tasks")

        # Статистика по статусам
        status_map = {
            '1': 'NEW',
            '2': 'PENDING',
            '3': 'IN_PROGRESS',
            '4': 'WAITING_REVIEW',
            '5': 'COMPLETED',
            '6': 'DEFERRED',
            '7': 'DECLINED'
        }

        statuses = Counter()
        for task in tasks:
            status_id = str(task.get('status', '0'))
            status_name = status_map.get(status_id, f'UNKNOWN_{status_id}')
            statuses[status_name] += 1

        logger.info(f"Tasks by status: {dict(statuses)}")

        # Статистика по приоритетам
        priority_map = {'0': 'LOW', '1': 'NORMAL', '2': 'HIGH'}
        priorities = Counter()
        for task in tasks:
            priority_id = str(task.get('priority', '1'))
            priority_name = priority_map.get(priority_id, f'UNKNOWN_{priority_id}')
            priorities[priority_name] += 1

        logger.info(f"Tasks by priority: {dict(priorities)}")

        # Топ ответственных
        responsible = Counter()
        for task in tasks:
            resp_id = task.get('responsible', {})
            if isinstance(resp_id, dict):
                resp_name = resp_id.get('name', 'Unknown')
            else:
                resp_name = str(resp_id)
            responsible[resp_name] += 1

        top_responsible = dict(responsible.most_common(10))
        logger.info(f"Top 10 responsible: {top_responsible}")

        return {
            'source': 'tasks.task.list',
            'filter': f'>=CHANGED_DATE: {filter_date}',
            'total': len(tasks),
            'stats': {
                'by_status': dict(statuses),
                'by_priority': dict(priorities),
                'top_responsible': top_responsible
            },
            'tasks': tasks
        }


# Тестирование
if __name__ == '__main__':
    import sys
    from pathlib import Path
    sys.path.insert(0, str(Path(__file__).parent.parent.parent))

    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )

    print("=== Testing Tasks Collector ===\n")

    try:
        collector = TasksCollector()
        collector.run()

        import json
        snapshot_path = collector.get_snapshot_path()

        with open(snapshot_path, 'r') as f:
            snapshot = json.load(f)

        print(f"\n✅ Snapshot created at: {snapshot_path}")
        print(f"   Total tasks: {snapshot['total']}")
        print(f"   Statuses: {snapshot['stats']['by_status']}")
        print(f"   Priorities: {snapshot['stats']['by_priority']}")

        print("\n✅ Tasks collector test passed!")

    except Exception as e:
        print(f"\n❌ Tasks collector test failed: {e}")
        import traceback
        traceback.print_exc()
        exit(1)
