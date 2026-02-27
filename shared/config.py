#!/usr/bin/env python3
"""
Config - Загрузка конфигурации для Bitrix24 Tools

Пути и переменные окружения для коллекторов.
"""

import os
import logging
from pathlib import Path
from typing import Optional

from dotenv import load_dotenv

logger = logging.getLogger(__name__)


def get_project_root() -> Path:
    """Корень проекта bitrix24-tools"""
    return Path(__file__).parent.parent


class Config:
    """Конфигурация проекта"""

    _instance: Optional['Config'] = None
    _loaded: bool = False

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self):
        if Config._loaded:
            return

        self.project_root = get_project_root()

        # Загрузить .env из .private/.env или из корня
        env_paths = [
            self.project_root / '.private' / '.env',
            self.project_root / '.env',
        ]

        for env_path in env_paths:
            if env_path.exists():
                load_dotenv(env_path)
                logger.debug(f"Loaded .env from {env_path}")
                break
        else:
            logger.warning("No .env file found")

        Config._loaded = True

    # === Пути ===

    @property
    def snapshots_dir(self) -> Path:
        """Папка snapshots/"""
        return self.project_root / 'snapshots'

    @property
    def archive_dir(self) -> Path:
        """Папка archive/"""
        return self.project_root / 'archive'

    @property
    def private_dir(self) -> Path:
        """Папка .private/"""
        return self.project_root / '.private'

    @property
    def bitrix_raw_dir(self) -> Path:
        """Папка для Bitrix данных (snapshots и archive)"""
        return self.project_root

    # === Bitrix24 ===

    @property
    def bitrix_webhook_url(self) -> Optional[str]:
        """URL вебхука Bitrix24"""
        url = os.getenv('BITRIX_WEBHOOK_URL') or os.getenv('BITRIX24_WEBHOOK')

        if url and url.startswith('http'):
            return url

        domain = os.getenv('BITRIX_DOMAIN') or os.getenv('BITRIX24_DOMAIN')
        webhook = url or os.getenv('BITRIX_WEBHOOK') or os.getenv('BITRIX24_WEBHOOK_PATH')

        if domain and webhook:
            return f"https://{domain}/rest/{webhook.strip('/')}/"

        return None

    @property
    def bitrix_domain(self) -> Optional[str]:
        """Домен Bitrix24"""
        return os.getenv('BITRIX_DOMAIN') or os.getenv('BITRIX24_DOMAIN')

    # === Утилиты ===

    def get(self, key: str, default: str = None) -> Optional[str]:
        return os.getenv(key, default)

    def require(self, key: str) -> str:
        value = os.getenv(key)
        if not value:
            raise ValueError(f"Required env var {key} not found. Add to .env")
        return value


config = Config()
