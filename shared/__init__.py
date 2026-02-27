"""
Shared module - общие компоненты для Bitrix24 Tools

Содержит:
- Config - загрузка конфигурации
- BitrixClient - HTTP клиент для Bitrix24 API
- BaseCollector - базовый класс для коллекторов
"""

from .config import Config, get_project_root
from .bitrix_client import BitrixClient
from .base_collector import BaseCollector

__all__ = [
    'Config',
    'BitrixClient',
    'BaseCollector',
    'get_project_root',
]
