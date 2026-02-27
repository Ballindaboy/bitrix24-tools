#!/usr/bin/env python3
"""
Activity Collector - Собирает ленту активности из Bitrix24

Собирает события из живой ленты за последние 7 дней:
- Новые сделки
- Обновления задач
- Посты и комментарии
"""

import logging
from typing import Dict
from datetime import datetime, timedelta
from collections import Counter

from shared import BaseCollector

logger = logging.getLogger(__name__)


class ActivityCollector(BaseCollector):
    """Собирает ленту активности за последние 7 дней"""

    def get_entity_name(self) -> str:
        return 'activity'

    def collect(self) -> Dict:
        """
        Собрать активность за 7 дней

        Returns:
            Словарь с данными:
            {
                'source': 'bitrix24.livefeed',
                'period': 'last 7 days',
                'total': 42,
                'activities': [...]
            }
        """
        logger.info("Fetching activity feed for last 7 days...")

        cutoff_date = datetime.now() - timedelta(days=7)
        activities = []

        try:
            activities = self.bitrix.get_all('log.blogpost.get', {
                'filter': {
                    '>DATE_PUBLISH': cutoff_date.isoformat()
                }
            })

            logger.info(f"Retrieved {len(activities)} activity items via log.blogpost.get")

        except Exception as e:
            logger.warning(f"log.blogpost.get failed: {e}")

            try:
                activities = self.bitrix.get_all('crm.activity.list', {
                    'filter': {
                        '>CREATED': cutoff_date.strftime('%Y-%m-%d')
                    },
                    'select': ['*']
                })

                logger.info(f"Retrieved {len(activities)} activities via crm.activity.list")

            except Exception as e2:
                logger.error(f"Both activity methods failed: {e2}")
                activities = []

        total = len(activities)

        if total > 0:
            activity_types = Counter()
            for activity in activities:
                activity_type = (
                    activity.get('TYPE', '') or
                    activity.get('TYPE_ID', '') or
                    activity.get('ENTITY_TYPE', '') or
                    'unknown'
                )
                activity_types[activity_type] += 1

            logger.info(f"Activities by type: {dict(activity_types)}")

            activities_by_date = Counter()
            for activity in activities:
                date_field = (
                    activity.get('DATE_PUBLISH', '') or
                    activity.get('CREATED', '') or
                    activity.get('DATE_CREATE', '')
                )
                if date_field:
                    activity_date = date_field.split(' ')[0] if ' ' in date_field else date_field[:10]
                    activities_by_date[activity_date] += 1

            logger.info(f"Activities by date: {dict(sorted(activities_by_date.items()))}")
        else:
            logger.info("No activities found for the period")
            activity_types = {}
            activities_by_date = {}

        return {
            'source': 'bitrix24.livefeed',
            'period': 'last 7 days',
            'cutoff_date': cutoff_date.isoformat(),
            'total': total,
            'stats': {
                'by_type': dict(activity_types) if activity_types else {},
                'by_date': dict(sorted(activities_by_date.items())) if activities_by_date else {}
            },
            'activities': activities
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

    print("=== Testing Activity Collector ===\n")

    try:
        collector = ActivityCollector()
        collector.run()

        import json
        snapshot_path = collector.get_snapshot_path()

        with open(snapshot_path, 'r') as f:
            snapshot = json.load(f)

        print(f"\n✅ Snapshot created at: {snapshot_path}")
        print(f"   Period: {snapshot['period']}")
        print(f"   Total activities: {snapshot['total']}")
        if snapshot['total'] > 0:
            print(f"   Activities by type: {snapshot['stats']['by_type']}")

        print("\n✅ Activity collector test passed!")

    except Exception as e:
        print(f"\n❌ Activity collector test failed: {e}")
        import traceback
        traceback.print_exc()
        exit(1)
