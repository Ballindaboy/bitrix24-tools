#!/usr/bin/env python3
"""
Task Comments Collector - Собирает комментарии к задачам из Bitrix24

Собирает комментарии для активных задач:
- task.commentitem.getlist для каждой задачи
- Фильтр: задачи, изменённые за последние 90 дней
- Сортировка по дате

API: https://dev.1c-bitrix.ru/rest_help/tasks/task/commentitem/getlist.php
"""

import logging
import time
from typing import Dict, List
from collections import Counter
from datetime import datetime, timedelta

from shared import BaseCollector

logger = logging.getLogger(__name__)


class TaskCommentsCollector(BaseCollector):
    """Собирает комментарии к задачам из Bitrix24"""

    def __init__(self, days: int = 90, limit_tasks: int = None, bitrix_client=None):
        """
        Args:
            days: За сколько дней собирать (по CHANGED_DATE задач)
            limit_tasks: Ограничение количества задач (для тестов)
            bitrix_client: Клиент Bitrix24 API
        """
        super().__init__(bitrix_client)
        self.days = days
        self.limit_tasks = limit_tasks

    def get_entity_name(self) -> str:
        return 'task_comments'

    def get_task_comments(self, task_id: int) -> List[Dict]:
        """
        Получить комментарии к задаче

        Args:
            task_id: ID задачи

        Returns:
            Список комментариев
        """
        try:
            result = self.bitrix.call('task.commentitem.getlist', {
                'TASKID': task_id,
                'ORDER': {'POST_DATE': 'desc'}
            })

            # API возвращает dict с ключом 'result' или напрямую список
            if isinstance(result, dict):
                comments = result.get('result', [])
            elif isinstance(result, list):
                comments = result
            else:
                comments = []

            return comments

        except Exception as e:
            logger.warning(f"Failed to get comments for task {task_id}: {e}")
            return []

    def collect(self) -> Dict:
        """
        Собрать комментарии к активным задачам

        Returns:
            Словарь с данными:
            {
                'source': 'task.commentitem.getlist',
                'filter': 'tasks changed >= YYYY-MM-DD',
                'total_tasks': 500,
                'total_comments': 2345,
                'tasks_with_comments': [...]
            }
        """
        # Вычислить дату для фильтра
        filter_date = datetime.now() - timedelta(days=self.days)
        filter_date_str = filter_date.strftime('%Y-%m-%dT00:00:00')

        logger.info(f"Fetching tasks changed >= {filter_date_str}...")

        # 1. Получить список задач
        tasks = self.bitrix.get_all('tasks.task.list', {
            'filter': {
                '>=CHANGED_DATE': filter_date_str
            },
            'select': ['ID', 'TITLE', 'STATUS', 'RESPONSIBLE_ID']
        })

        logger.info(f"Retrieved {len(tasks)} tasks")

        # Ограничить если указано
        if self.limit_tasks:
            tasks = tasks[:self.limit_tasks]
            logger.info(f"Limited to {len(tasks)} tasks")

        # 2. Собрать комментарии для каждой задачи
        tasks_with_comments = []
        total_comments = 0
        comments_by_author = Counter()

        for i, task in enumerate(tasks, 1):
            task_id = task.get('id') or task.get('ID')
            task_title = task.get('title') or task.get('TITLE', 'Unknown')

            if i % 50 == 0:
                logger.info(f"Processing task {i}/{len(tasks)}...")

            comments = self.get_task_comments(task_id)

            if comments:
                total_comments += len(comments)

                # Статистика по авторам
                for comment in comments:
                    author = comment.get('AUTHOR_NAME', 'Unknown')
                    comments_by_author[author] += 1

                tasks_with_comments.append({
                    'task_id': task_id,
                    'task_title': task_title[:100],
                    'task_status': task.get('status') or task.get('STATUS'),
                    'comments_count': len(comments),
                    'comments': comments
                })

            # Задержка между запросами
            time.sleep(0.1)

        logger.info(f"Total comments: {total_comments}")
        logger.info(f"Tasks with comments: {len(tasks_with_comments)}")

        return {
            'source': 'task.commentitem.getlist',
            'filter': f'tasks changed >= {filter_date_str}',
            'total_tasks': len(tasks),
            'total_comments': total_comments,
            'tasks_with_comments_count': len(tasks_with_comments),
            'stats': {
                'top_commenters': dict(comments_by_author.most_common(20))
            },
            'tasks_with_comments': tasks_with_comments
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

    print("=== Testing Task Comments Collector ===\n")

    try:
        # Тест с небольшим лимитом
        collector = TaskCommentsCollector(days=30, limit_tasks=20)
        collector.run()

        import json
        snapshot_path = collector.get_snapshot_path()

        with open(snapshot_path, 'r') as f:
            snapshot = json.load(f)

        print(f"\n✅ Snapshot created at: {snapshot_path}")
        print(f"   Total tasks: {snapshot['total_tasks']}")
        print(f"   Total comments: {snapshot['total_comments']}")
        print(f"   Tasks with comments: {snapshot['tasks_with_comments_count']}")

        print("\n✅ Task comments collector test passed!")

    except Exception as e:
        print(f"\n❌ Task comments collector test failed: {e}")
        import traceback
        traceback.print_exc()
        exit(1)
