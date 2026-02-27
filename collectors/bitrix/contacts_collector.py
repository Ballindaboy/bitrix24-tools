#!/usr/bin/env python3
"""
Contacts Collector - Собирает контакты из Bitrix24 CRM

Собирает ВСЕ контакты (клиенты, партнёры) с:
- ID
- Имя (NAME, LAST_NAME)
- Компания (COMPANY_ID)
- Email
- Телефон
- Должность (POST)
"""

import logging
from typing import Dict
from collections import Counter

from shared import BaseCollector

logger = logging.getLogger(__name__)


class ContactsCollector(BaseCollector):
    """Собирает контакты из Bitrix24 CRM"""

    def get_entity_name(self) -> str:
        return 'contacts'

    def collect(self) -> Dict:
        """
        Собрать все контакты из CRM

        Returns:
            Словарь с данными:
            {
                'source': 'bitrix24.crm.contact.list',
                'total': 500,
                'stats': {...},
                'contacts': [...]
            }
        """
        logger.info("Fetching contacts from Bitrix24 CRM...")

        contacts = self.bitrix.get_all('crm.contact.list', {
            'select': ['*', 'UF_*'],
            'order': {'DATE_MODIFY': 'DESC'}
        })

        logger.info(f"Retrieved {len(contacts)} contacts")

        # Статистика по типам
        types = Counter(contact.get('TYPE_ID', 'UNKNOWN') for contact in contacts)
        logger.info(f"Contacts by type: {dict(types)}")

        # Подсчёт контактов с email/phone
        with_email = sum(1 for c in contacts if c.get('EMAIL'))
        with_phone = sum(1 for c in contacts if c.get('PHONE'))
        logger.info(f"With email: {with_email}, with phone: {with_phone}")

        return {
            'source': 'bitrix24.crm.contact.list',
            'total': len(contacts),
            'stats': {
                'by_type': dict(types),
                'with_email': with_email,
                'with_phone': with_phone
            },
            'contacts': contacts
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

    print("=== Testing ContactsCollector ===\n")

    try:
        collector = ContactsCollector()
        result = collector.run()

        if result:
            print("\n✅ Contacts collector test passed!")
        else:
            print("\n❌ Contacts collector test failed!")
            exit(1)

    except Exception as e:
        print(f"\n❌ Contacts collector test failed: {e}")
        import traceback
        traceback.print_exc()
        exit(1)
