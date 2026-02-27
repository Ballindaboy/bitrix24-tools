#!/usr/bin/env python3
"""
Base Collector - Базовый класс для всех коллекторов

Содержит общую логику сохранения snapshots в Bronze layer.
"""

import json
import logging
import shutil
from abc import ABC, abstractmethod
from pathlib import Path
from datetime import datetime
from typing import Dict

from .config import Config
from .bitrix_client import BitrixClient

logger = logging.getLogger(__name__)


class BaseCollector(ABC):
    """Базовый класс для всех коллекторов"""

    def __init__(self, bitrix_client: BitrixClient = None):
        """
        Инициализация коллектора

        Args:
            bitrix_client: Клиент Bitrix24 API (если None, создаётся новый)
        """
        self.bitrix = bitrix_client or BitrixClient()
        self.config = Config()

        # Путь к папке TEXDAR/bitrix24/
        self.raw_dir = self.config.bitrix_raw_dir

        logger.debug(f"Initialized {self.__class__.__name__}, RAW dir: {self.raw_dir}")

    @abstractmethod
    def collect(self) -> Dict:
        """
        Собрать данные из источника

        Должен вернуть словарь с данными для сохранения.
        Например:
        {
            'source': 'bitrix24.crm.deal.list',
            'total': 127,
            'deals': [...]
        }

        Returns:
            Словарь с данными
        """
        pass

    @abstractmethod
    def get_entity_name(self) -> str:
        """
        Название сущности (для имени папки)

        Returns:
            Строка: deals, tasks, contacts, calendar, activity
        """
        pass

    def get_snapshot_path(self) -> Path:
        """
        Путь к snapshot файлу (один актуальный на модуль)

        Returns:
            Path к файлу вида: TEXDAR/bitrix24/snapshots/deals.json
        """
        entity = self.get_entity_name()
        path = self.raw_dir / 'snapshots' / f'{entity}.json'
        return path

    def get_archive_path(self) -> Path:
        """
        Путь к архивной копии snapshot'а

        Returns:
            Path к файлу вида: TEXDAR/bitrix24/archive/2025-12-19/deals.json
        """
        date_str = datetime.now().strftime('%Y-%m-%d')
        entity = self.get_entity_name()
        path = self.raw_dir / 'archive' / date_str / f'{entity}.json'
        return path

    def save_snapshot(self, data: Dict):
        """
        Сохранить snapshot в JSON

        Архивирует старый snapshot (если есть), затем сохраняет новый.
        Один актуальный файл на модуль, история в archive/.

        Args:
            data: Данные для сохранения
        """
        path = self.get_snapshot_path()
        archive_path = self.get_archive_path()

        # Создать папки если не существуют
        path.parent.mkdir(parents=True, exist_ok=True)
        archive_path.parent.mkdir(parents=True, exist_ok=True)

        # Архивировать старый snapshot (если есть)
        if path.exists():
            shutil.copy2(path, archive_path)
            logger.debug(f"Archived old snapshot to {archive_path}")

        # Добавить метаданные
        snapshot = {
            'snapshot_date': datetime.now().isoformat(),
            'entity': self.get_entity_name(),
            **data
        }

        logger.info(f"Saving snapshot to {path}")

        # Сохранить в JSON
        with open(path, 'w', encoding='utf-8') as f:
            json.dump(snapshot, f, ensure_ascii=False, indent=2)

        file_size_kb = path.stat().st_size / 1024
        logger.info(f"✅ Snapshot saved: {file_size_kb:.1f} KB")

    def run(self) -> bool:
        """
        Выполнить сбор данных

        Returns:
            True если успешно
        """
        entity_name = self.get_entity_name()
        logger.info(f"=== Starting {entity_name} collector ===")

        try:
            # Собрать данные
            data = self.collect()

            # Сохранить snapshot
            self.save_snapshot(data)

            logger.info(f"✅ {entity_name} collector completed")
            return True

        except Exception as e:
            logger.error(f"❌ {entity_name} collector failed: {e}")
            raise
