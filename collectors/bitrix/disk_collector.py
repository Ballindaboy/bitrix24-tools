#!/usr/bin/env python3
"""
Disk Collector - Собирает структуру Bitrix Диска

Собирает:
- Список хранилищ (storages)
- Дерево папок (рекурсивно до 5 уровней)
- Метаданные файлов (имя, размер, дата, расширение)
- БЕЗ содержимого файлов (только структура)
"""

import logging
import time
from typing import Dict, List
from collections import Counter

from shared import BaseCollector

logger = logging.getLogger(__name__)


class DiskCollector(BaseCollector):
    """Собирает структуру Bitrix Диска"""

    def __init__(self, max_depth=5):
        """
        Args:
            max_depth: Максимальная глубина рекурсии для папок (по умолчанию 5)
        """
        super().__init__()
        self.max_depth = max_depth

    def get_entity_name(self) -> str:
        return 'disk'

    def get_folder_children(self, folder_id: str, depth: int = 0) -> List[Dict]:
        """
        Рекурсивно получить содержимое папки

        Args:
            folder_id: ID папки
            depth: Текущая глубина рекурсии

        Returns:
            Список элементов (папки и файлы) с вложенной структурой
        """
        if depth >= self.max_depth:
            logger.debug(f"Max depth {self.max_depth} reached for folder {folder_id}")
            return []

        try:
            items = self.bitrix.call('disk.folder.getchildren', {'id': folder_id})
            time.sleep(0.3)

            result = []
            for item in items:
                item_data = {
                    'ID': item.get('ID'),
                    'NAME': item.get('NAME'),
                    'TYPE': item.get('TYPE'),
                    'SIZE': item.get('SIZE'),
                    'CREATE_TIME': item.get('CREATE_TIME'),
                    'UPDATE_TIME': item.get('UPDATE_TIME'),
                    'CREATED_BY': item.get('CREATED_BY'),
                }

                if item.get('TYPE') == 'folder':
                    item_data['children'] = self.get_folder_children(item['ID'], depth + 1)
                    item_data['children_count'] = len(item_data['children'])
                else:
                    name = item.get('NAME', '')
                    if '.' in name:
                        item_data['EXTENSION'] = name.split('.')[-1].lower()

                result.append(item_data)

            return result

        except Exception as e:
            logger.warning(f"Failed to get children for folder {folder_id}: {e}")
            return []

    def collect(self) -> Dict:
        """
        Собрать структуру Bitrix Диска

        Returns:
            Словарь с данными:
            {
                'source': 'bitrix24.disk.storage.getlist',
                'total_storages': 49,
                'stats': {...},
                'storages': [...]
            }
        """
        logger.info("Fetching Bitrix Disk structure...")

        storages = self.bitrix.call('disk.storage.getlist')
        logger.info(f"Retrieved {len(storages)} storages")

        storages_data = []
        total_folders = 0
        total_files = 0

        for i, storage in enumerate(storages, 1):
            storage_id = storage['ID']
            storage_name = storage.get('NAME', 'Unknown')
            storage_type = storage.get('ENTITY_TYPE', 'unknown')

            logger.info(f"[{i}/{len(storages)}] Processing storage: {storage_name} (ID: {storage_id})")

            try:
                children = self.bitrix.call('disk.storage.getchildren', {'id': storage_id})
                time.sleep(0.3)

                processed_children = []
                for item in children:
                    item_data = {
                        'ID': item.get('ID'),
                        'NAME': item.get('NAME'),
                        'TYPE': item.get('TYPE'),
                        'SIZE': item.get('SIZE'),
                        'CREATE_TIME': item.get('CREATE_TIME'),
                        'UPDATE_TIME': item.get('UPDATE_TIME'),
                    }

                    if item.get('TYPE') == 'folder':
                        item_data['children'] = self.get_folder_children(item['ID'], depth=1)
                        item_data['children_count'] = len(item_data['children'])
                        total_folders += 1
                    else:
                        total_files += 1
                        name = item.get('NAME', '')
                        if '.' in name:
                            item_data['EXTENSION'] = name.split('.')[-1].lower()

                    processed_children.append(item_data)

                storages_data.append({
                    'ID': storage_id,
                    'NAME': storage_name,
                    'ENTITY_TYPE': storage_type,
                    'MODULE_ID': storage.get('MODULE_ID'),
                    'ENTITY_ID': storage.get('ENTITY_ID'),
                    'children': processed_children,
                    'children_count': len(processed_children)
                })

            except Exception as e:
                logger.error(f"Failed to process storage {storage_name}: {e}")
                storages_data.append({
                    'ID': storage_id,
                    'NAME': storage_name,
                    'ENTITY_TYPE': storage_type,
                    'error': str(e)
                })

        logger.info(f"Total folders: {total_folders}, Total files: {total_files}")

        storage_types = Counter(s.get('ENTITY_TYPE') for s in storages)
        logger.info(f"Storage types: {dict(storage_types)}")

        return {
            'source': 'bitrix24.disk.storage.getlist',
            'total_storages': len(storages),
            'total_folders': total_folders,
            'total_files': total_files,
            'max_depth': self.max_depth,
            'stats': {
                'by_type': dict(storage_types)
            },
            'storages': storages_data
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

    print("=== Testing DiskCollector ===\n")

    try:
        collector = DiskCollector(max_depth=2)
        result = collector.run()

        if result:
            print("\n✅ Disk collector test passed!")
        else:
            print("\n❌ Disk collector test failed!")
            exit(1)

    except Exception as e:
        print(f"\n❌ Disk collector test failed: {e}")
        import traceback
        traceback.print_exc()
        exit(1)
