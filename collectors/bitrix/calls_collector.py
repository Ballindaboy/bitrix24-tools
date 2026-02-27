#!/usr/bin/env python3
"""
Calls Collector - Собирает статистику звонков из Bitrix24 Voximplant

Собирает звонки с записями для последующей транскрипции.
Использует voximplant.statistic.get API.
"""

import logging
from typing import Dict
from datetime import datetime, timedelta
from collections import Counter

from shared import BaseCollector

logger = logging.getLogger(__name__)


class CallsCollector(BaseCollector):
    """Собирает статистику звонков из Voximplant"""

    def get_entity_name(self) -> str:
        return 'calls'

    def collect(self, days: int = 30) -> Dict:
        """
        Собрать статистику звонков за период

        Args:
            days: Количество дней для выборки (по умолчанию 30)

        Returns:
            Словарь с данными:
            {
                'source': 'bitrix24.voximplant.statistic.get',
                'period_days': 30,
                'total': 150,
                'with_records': 42,
                'calls': [...]
            }
        """
        logger.info(f"Fetching call statistics for last {days} days...")

        # Формируем фильтр по дате
        start_date = (datetime.now() - timedelta(days=days)).strftime('%Y-%m-%d')

        calls = []

        try:
            # Используем voximplant.statistic.get
            calls = self.bitrix.get_all('voximplant.statistic.get', {
                'FILTER': {
                    '>CALL_START_DATE': start_date
                },
                'SORT': 'CALL_START_DATE',
                'ORDER': 'DESC'
            })

            logger.info(f"Retrieved {len(calls)} calls via voximplant.statistic.get")

        except Exception as e:
            logger.warning(f"voximplant.statistic.get failed: {e}")

            # Fallback: попробовать через CRM activities с типом "звонок"
            try:
                activities = self.bitrix.get_all('crm.activity.list', {
                    'filter': {
                        'TYPE_ID': 2,  # 2 = звонок
                        '>CREATED': start_date
                    },
                    'select': ['*']
                })

                logger.info(f"Retrieved {len(activities)} call activities via crm.activity.list")
                calls = activities

            except Exception as e2:
                logger.error(f"Both methods failed: {e2}")
                calls = []

        # Подсчёт статистики
        total = len(calls)

        # Звонки с записями
        with_records = [
            c for c in calls
            if c.get('RECORD_FILE_ID') or c.get('RECORD_URL')
        ]

        # Звонки с транскрипцией
        with_transcripts = [
            c for c in calls
            if c.get('TRANSCRIPT_ID')
        ]

        # Статистика по типам
        call_types = Counter()
        for call in calls:
            call_type = call.get('CALL_TYPE', 'unknown')
            # 1=исходящий, 2=входящий, 3=входящий с переадресацией, 4=callback
            type_name = {
                1: 'outgoing',
                2: 'incoming',
                3: 'incoming_redirect',
                4: 'callback',
                '1': 'outgoing',
                '2': 'incoming',
                '3': 'incoming_redirect',
                '4': 'callback'
            }.get(call_type, f'type_{call_type}')
            call_types[type_name] += 1

        # Статистика по дням
        calls_by_date = Counter()
        for call in calls:
            date_field = call.get('CALL_START_DATE', '') or call.get('CREATED', '')
            if date_field:
                call_date = date_field.split('T')[0] if 'T' in date_field else date_field[:10]
                calls_by_date[call_date] += 1

        # Общая длительность (в минутах)
        total_duration_sec = sum(
            int(c.get('CALL_DURATION', 0) or 0)
            for c in calls
        )
        total_duration_min = total_duration_sec / 60

        logger.info(f"Calls with records: {len(with_records)}")
        logger.info(f"Calls with transcripts: {len(with_transcripts)}")
        logger.info(f"Total duration: {total_duration_min:.0f} minutes")

        return {
            'source': 'bitrix24.voximplant.statistic.get',
            'period_days': days,
            'start_date': start_date,
            'total': total,
            'with_records': len(with_records),
            'with_transcripts': len(with_transcripts),
            'pending_transcription': len(with_records) - len(with_transcripts),
            'total_duration_minutes': round(total_duration_min, 1),
            'stats': {
                'by_type': dict(call_types),
                'by_date': dict(sorted(calls_by_date.items(), reverse=True)[:14])  # последние 14 дней
            },
            'calls': calls
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

    print("=== Testing Calls Collector ===\n")

    try:
        collector = CallsCollector()
        collector.run()

        import json
        snapshot_path = collector.get_snapshot_path()

        with open(snapshot_path, 'r') as f:
            snapshot = json.load(f)

        print(f"\n{'='*50}")
        print(f"Snapshot: {snapshot_path}")
        print(f"{'='*50}")
        print(f"Period: last {snapshot['period_days']} days (from {snapshot['start_date']})")
        print(f"Total calls: {snapshot['total']}")
        print(f"With records: {snapshot['with_records']}")
        print(f"With transcripts: {snapshot['with_transcripts']}")
        print(f"Pending transcription: {snapshot['pending_transcription']}")
        print(f"Total duration: {snapshot['total_duration_minutes']:.0f} minutes")

        if snapshot['stats']['by_type']:
            print(f"\nBy type: {snapshot['stats']['by_type']}")

        if snapshot['with_records'] > 0:
            print(f"\n[OK] Found {snapshot['with_records']} calls with records - can transcribe!")

            # Показать примеры звонков с записями
            calls_with_rec = [c for c in snapshot['calls'] if c.get('RECORD_FILE_ID')][:3]
            if calls_with_rec:
                print("\nSample calls with records:")
                for c in calls_with_rec:
                    print(f"  - ID: {c.get('CALL_ID')}, "
                          f"Duration: {c.get('CALL_DURATION')}s, "
                          f"File: {c.get('RECORD_FILE_ID')}")
        else:
            print(f"\n[WARNING] No calls with records found")

        print("\n[OK] Calls collector test passed!")

    except Exception as e:
        print(f"\n[ERROR] Calls collector test failed: {e}")
        import traceback
        traceback.print_exc()
        exit(1)
