#!/usr/bin/env python3
"""
Users Collector - Собирает пользователей (сотрудников) из Bitrix24

Собирает ВСЕХ пользователей с:
- ID
- Имя (NAME, LAST_NAME)
- Должность (WORK_POSITION)
- Email
- Телефон
- Статус (ACTIVE)
- Отдел (UF_DEPARTMENT)
"""

import logging
from typing import Dict
from collections import Counter

from shared import BaseCollector

logger = logging.getLogger(__name__)


class UsersCollector(BaseCollector):
    """Собирает пользователей из Bitrix24"""

    def get_entity_name(self) -> str:
        return 'users'

    def collect(self) -> Dict:
        """
        Собрать всех пользователей Bitrix24

        Returns:
            Словарь с данными:
            {
                'source': 'bitrix24.user.get',
                'total': 60,
                'stats': {...},
                'users': [...]
            }
        """
        logger.info("Fetching users from Bitrix24...")

        users = self.bitrix.get_all('user.get', {
            'ADMIN_MODE': True
        })

        logger.info(f"Retrieved {len(users)} users")

        # Статистика по статусу
        active_count = sum(1 for u in users if u.get('ACTIVE', False))
        inactive_count = len(users) - active_count

        logger.info(f"Active users: {active_count}, Inactive: {inactive_count}")

        # Статистика по должностям (топ-10)
        positions = Counter(
            u.get('WORK_POSITION', 'Не указано')
            for u in users
            if u.get('ACTIVE', False)
        )
        top_positions = dict(positions.most_common(10))
        logger.info(f"Top 10 positions: {top_positions}")

        return {
            'source': 'bitrix24.user.get',
            'total': len(users),
            'stats': {
                'active': active_count,
                'inactive': inactive_count,
                'top_positions': top_positions
            },
            'users': users
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

    print("=== Testing UsersCollector ===\n")

    try:
        collector = UsersCollector()
        result = collector.run()

        if result:
            print("\n✅ Users collector test passed!")
        else:
            print("\n❌ Users collector test failed!")
            exit(1)

    except Exception as e:
        print(f"\n❌ Users collector test failed: {e}")
        import traceback
        traceback.print_exc()
        exit(1)
