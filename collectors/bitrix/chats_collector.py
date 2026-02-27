#!/usr/bin/env python3
"""
Chats Collector - Собирает чаты из Bitrix24

Собирает:
- Список недавних чатов/диалогов
- Сообщения из каждого чата (последние 100)
- Метаданные чатов (участники, название, тип)
"""

import logging
import time
from typing import Dict, List
from collections import Counter

from shared import BaseCollector

logger = logging.getLogger(__name__)


class ChatsCollector(BaseCollector):
    """Собирает чаты из Bitrix24"""

    def __init__(self, limit_chats=50, limit_messages=100):
        """
        Args:
            limit_chats: Максимальное количество чатов для сбора
            limit_messages: Максимальное количество сообщений на чат
        """
        super().__init__()
        self.limit_chats = limit_chats
        self.limit_messages = limit_messages

    def get_entity_name(self) -> str:
        return 'chats'

    def get_chat_messages(self, dialog_id: str) -> List[Dict]:
        """
        Получить сообщения из чата

        Args:
            dialog_id: ID диалога (например: chat123 или user456)

        Returns:
            Список сообщений
        """
        try:
            result = self.bitrix.call('im.dialog.messages.get', {
                'DIALOG_ID': dialog_id,
                'LIMIT': self.limit_messages
            })

            messages = result.get('messages', []) if isinstance(result, dict) else []
            logger.debug(f"Retrieved {len(messages)} messages from {dialog_id}")

            time.sleep(0.2)
            return messages

        except Exception as e:
            logger.warning(f"Failed to get messages for {dialog_id}: {e}")
            return []

    def collect(self) -> Dict:
        """
        Собрать чаты и сообщения из Bitrix24

        Returns:
            Словарь с данными:
            {
                'source': 'bitrix24.im',
                'total_chats': 50,
                'total_messages': 2345,
                'chats': [...]
            }
        """
        logger.info(f"Fetching recent chats (limit: {self.limit_chats})...")

        try:
            recent = self.bitrix.call('im.recent.list', {
                'LIMIT': self.limit_chats
            })

            chats_list = recent.get('items', []) if isinstance(recent, dict) else []
            logger.info(f"Retrieved {len(chats_list)} recent chats")

        except Exception as e:
            logger.error(f"Failed to get recent chats: {e}")
            return {
                'source': 'bitrix24.im',
                'error': str(e),
                'total_chats': 0,
                'total_messages': 0,
                'chats': []
            }

        chats_data = []
        total_messages = 0
        chat_types = Counter()

        for i, chat in enumerate(chats_list, 1):
            chat_type = chat.get('type', 'unknown')
            chat_name = chat.get('title', 'Unknown')

            if chat_type == 'user':
                dialog_id = str(chat.get('id', ''))
            elif chat_type == 'chat':
                dialog_id = f"chat{chat.get('chat_id', '')}"
            else:
                dialog_id = str(chat.get('id', chat.get('chat_id', '')))

            logger.info(f"[{i}/{len(chats_list)}] Processing chat: {chat_name} ({dialog_id})")

            messages = self.get_chat_messages(dialog_id)
            total_messages += len(messages)
            chat_types[chat_type] += 1

            chats_data.append({
                'dialogId': dialog_id,
                'type': chat_type,
                'title': chat_name,
                'counter': chat.get('counter', 0),
                'message': chat.get('message', {}),
                'user': chat.get('user', {}),
                'messages': messages,
                'messages_count': len(messages)
            })

        logger.info(f"Total chats: {len(chats_data)}, Total messages: {total_messages}")
        logger.info(f"Chats by type: {dict(chat_types)}")

        return {
            'source': 'bitrix24.im',
            'total_chats': len(chats_data),
            'total_messages': total_messages,
            'limit_chats': self.limit_chats,
            'limit_messages_per_chat': self.limit_messages,
            'stats': {
                'by_type': dict(chat_types)
            },
            'chats': chats_data
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

    print("=== Testing ChatsCollector ===\n")

    try:
        collector = ChatsCollector(limit_chats=10, limit_messages=50)
        result = collector.run()

        if result:
            print("\n✅ Chats collector test passed!")
        else:
            print("\n❌ Chats collector test failed!")
            exit(1)

    except Exception as e:
        print(f"\n❌ Chats collector test failed: {e}")
        import traceback
        traceback.print_exc()
        exit(1)
