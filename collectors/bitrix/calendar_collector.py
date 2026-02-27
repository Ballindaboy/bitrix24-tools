#!/usr/bin/env python3
"""
Calendar Collector - Собирает события календаря из Bitrix24

Собирает события на ближайшие 7 дней:
- Все поля событий
- Участники (attendees)
- Описания встреч
"""

import logging
from typing import Dict
from datetime import datetime, timedelta
from collections import Counter

from shared import BaseCollector

logger = logging.getLogger(__name__)


class CalendarCollector(BaseCollector):
    """Собирает события календаря на +7 дней"""

    def get_entity_name(self) -> str:
        return 'calendar'

    def collect(self) -> Dict:
        """
        Собрать события на ближайшие 7 дней

        Returns:
            Словарь с данными:
            {
                'source': 'calendar.event.get',
                'period': '2025-12-19 to 2025-12-26',
                'total': 15,
                'events': [...]
            }
        """
        today = datetime.now()
        end_date = today + timedelta(days=7)

        logger.info(f"Fetching calendar events from {today.date()} to {end_date.date()}...")

        events = []

        try:
            # Метод: calendar.event.get
            # ВАЖНО: ownerId должен быть конкретным ID пользователя
            events = self.bitrix.call('calendar.event.get', {
                'type': 'user',
                'ownerId': 1,  # ID владельца базы знаний (Наиль Мусин)
                'from': today.strftime('%Y-%m-%d'),
                'to': end_date.strftime('%Y-%m-%d')
            })

            if isinstance(events, list):
                logger.info(f"Retrieved {len(events)} events via calendar.event.get")
            elif isinstance(events, dict) and 'events' in events:
                events = events['events']
                logger.info(f"Retrieved {len(events)} events via calendar.event.get")
            else:
                logger.warning(f"Unexpected format from calendar.event.get: {type(events)}")
                events = []

        except Exception as e:
            logger.warning(f"calendar.event.get failed: {e}")

            try:
                events = self.bitrix.call('calendar.meeting.get', {
                    'from': today.strftime('%Y-%m-%d'),
                    'to': end_date.strftime('%Y-%m-%d')
                })

                if isinstance(events, list):
                    logger.info(f"Retrieved {len(events)} events via calendar.meeting.get")
                else:
                    events = []

            except Exception as e2:
                logger.error(f"Both calendar methods failed: {e2}")
                events = []

        # Статистика
        total = len(events)

        if total > 0:
            event_types = Counter(event.get('EVENT_TYPE', 'unknown') for event in events)
            logger.info(f"Events by type: {dict(event_types)}")

            events_by_date = Counter()
            for event in events:
                date_from = event.get('DATE_FROM', '')
                if date_from:
                    event_date = date_from.split(' ')[0] if ' ' in date_from else date_from
                    events_by_date[event_date] += 1

            logger.info(f"Events by date: {dict(sorted(events_by_date.items()))}")
        else:
            logger.info("No events found for the period")
            event_types = {}
            events_by_date = {}

        return {
            'source': 'bitrix24.calendar',
            'period': f"{today.date()} to {end_date.date()}",
            'total': total,
            'stats': {
                'by_type': dict(event_types) if event_types else {},
                'by_date': dict(sorted(events_by_date.items())) if events_by_date else {}
            },
            'events': events
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

    print("=== Testing Calendar Collector ===\n")

    try:
        collector = CalendarCollector()
        collector.run()

        import json
        snapshot_path = collector.get_snapshot_path()

        with open(snapshot_path, 'r') as f:
            snapshot = json.load(f)

        print(f"\n✅ Snapshot created at: {snapshot_path}")
        print(f"   Period: {snapshot['period']}")
        print(f"   Total events: {snapshot['total']}")
        if snapshot['total'] > 0:
            print(f"   Events by date: {snapshot['stats']['by_date']}")

        print("\n✅ Calendar collector test passed!")

    except Exception as e:
        print(f"\n❌ Calendar collector test failed: {e}")
        import traceback
        traceback.print_exc()
        exit(1)
