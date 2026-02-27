#!/usr/bin/env python3
"""
CRM Collector - Собирает сделки из Bitrix24 CRM

Собирает ВСЕ сделки с:
- Всеми полями (включая custom UF_*)
- Связанными контактами
- Связанными компаниями
"""

import logging
from typing import Dict
from collections import Counter

from shared import BaseCollector

logger = logging.getLogger(__name__)


class CRMCollector(BaseCollector):
    """Собирает сделки из Bitrix24 CRM"""

    def get_entity_name(self) -> str:
        return 'deals'

    def collect(self) -> Dict:
        """
        Собрать все сделки из CRM

        Returns:
            Словарь с данными:
            {
                'source': 'bitrix24.crm.deal.list',
                'total': 127,
                'deals': [...]
            }
        """
        logger.info("Fetching deals from Bitrix24 CRM...")

        # Получить все сделки
        deals = self.bitrix.get_all('crm.deal.list', {
            'select': ['*', 'UF_*'],  # Все поля + custom fields
            'order': {'DATE_MODIFY': 'DESC'}
        })

        logger.info(f"Retrieved {len(deals)} deals")

        # Статистика по стадиям
        stages = Counter(deal.get('STAGE_ID', 'UNKNOWN') for deal in deals)
        logger.info(f"Deals by stage: {dict(stages)}")

        # Статистика по валютам
        currencies = Counter(deal.get('CURRENCY_ID', 'UNKNOWN') for deal in deals)
        logger.info(f"Deals by currency: {dict(currencies)}")

        # Общая сумма сделок
        total_amount = sum(
            float(deal.get('OPPORTUNITY', 0) or 0)
            for deal in deals
        )
        logger.info(f"Total deals amount: {total_amount:,.0f} RUB")

        return {
            'source': 'bitrix24.crm.deal.list',
            'total': len(deals),
            'stats': {
                'by_stage': dict(stages),
                'by_currency': dict(currencies),
                'total_amount': total_amount
            },
            'deals': deals
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

    print("=== Testing CRM Collector ===\n")

    try:
        collector = CRMCollector()
        collector.run()

        # Проверить созданный snapshot
        import json
        snapshot_path = collector.get_snapshot_path()

        with open(snapshot_path, 'r') as f:
            snapshot = json.load(f)

        print(f"\n✅ Snapshot created at: {snapshot_path}")
        print(f"   Total deals: {snapshot['total']}")
        print(f"   Total amount: {snapshot['stats']['total_amount']:,.0f} RUB")
        print(f"   Stages: {snapshot['stats']['by_stage']}")

        print("\n✅ CRM collector test passed!")

    except Exception as e:
        print(f"\n❌ CRM collector test failed: {e}")
        import traceback
        traceback.print_exc()
        exit(1)
