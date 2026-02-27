#!/usr/bin/env python3
"""
Companies Collector - Собирает компании из Bitrix24 CRM

Собирает ВСЕ компании (клиенты, партнёры) с:
- ID
- Название (TITLE)
- Тип (COMPANY_TYPE)
- Отрасль (INDUSTRY)
- Email
- Телефон
- Сайт (WEB)
"""

import logging
from typing import Dict
from collections import Counter

from shared import BaseCollector

logger = logging.getLogger(__name__)


class CompaniesCollector(BaseCollector):
    """Собирает компании из Bitrix24 CRM"""

    def get_entity_name(self) -> str:
        return 'companies'

    def collect(self) -> Dict:
        """
        Собрать все компании из CRM

        Returns:
            Словарь с данными:
            {
                'source': 'bitrix24.crm.company.list',
                'total': 300,
                'stats': {...},
                'companies': [...]
            }
        """
        logger.info("Fetching companies from Bitrix24 CRM...")

        companies = self.bitrix.get_all('crm.company.list', {
            'select': ['*', 'UF_*'],
            'order': {'DATE_MODIFY': 'DESC'}
        })

        logger.info(f"Retrieved {len(companies)} companies")

        # Статистика по типам компаний
        types = Counter(company.get('COMPANY_TYPE', 'UNKNOWN') for company in companies)
        logger.info(f"Companies by type: {dict(types)}")

        # Статистика по отраслям (топ-10)
        industries = Counter(company.get('INDUSTRY', 'UNKNOWN') for company in companies)
        top_industries = dict(industries.most_common(10))
        logger.info(f"Top 10 industries: {top_industries}")

        return {
            'source': 'bitrix24.crm.company.list',
            'total': len(companies),
            'stats': {
                'by_type': dict(types),
                'top_industries': top_industries
            },
            'companies': companies
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

    print("=== Testing CompaniesCollector ===\n")

    try:
        collector = CompaniesCollector()
        result = collector.run()

        if result:
            print("\n✅ Companies collector test passed!")
        else:
            print("\n❌ Companies collector test failed!")
            exit(1)

    except Exception as e:
        print(f"\n❌ Companies collector test failed: {e}")
        import traceback
        traceback.print_exc()
        exit(1)
