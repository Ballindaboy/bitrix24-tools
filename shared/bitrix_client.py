#!/usr/bin/env python3
"""
Bitrix24 REST API Client

Единый HTTP клиент для всех Bitrix24 API запросов.
Поддерживает retry logic, автоматическую пагинацию, batch запросы.
"""

import time
import logging
import socket
import subprocess
from typing import Dict, List, Optional, Any

import requests
from requests.adapters import HTTPAdapter
from urllib3.util.connection import create_connection as _create_connection

from .config import Config


class SourceAddressAdapter(HTTPAdapter):
    """HTTP Adapter that binds to a specific source IP (for VPN bypass)"""

    def __init__(self, source_address, **kwargs):
        self.source_address = source_address
        super().__init__(**kwargs)

    def init_poolmanager(self, *args, **kwargs):
        kwargs['source_address'] = (self.source_address, 0)
        super().init_poolmanager(*args, **kwargs)


def get_en0_ip():
    """Get the IP address of en0 interface (for VPN bypass)"""
    try:
        result = subprocess.run(
            ['ipconfig', 'getifaddr', 'en0'],
            capture_output=True, text=True, timeout=5
        )
        if result.returncode == 0:
            return result.stdout.strip()
    except Exception:
        pass
    return None

# Настройка логирования
logger = logging.getLogger(__name__)


class BitrixClient:
    """Единый клиент для Bitrix24 REST API"""

    def __init__(self, webhook_url: Optional[str] = None):
        """
        Инициализация клиента

        Args:
            webhook_url: URL вебхука Bitrix24. Если не указан, загружается из Config
        """
        config = Config()

        # Получить webhook URL
        self.webhook_url = webhook_url or config.bitrix_webhook_url

        if not self.webhook_url:
            raise ValueError(
                "Bitrix24 credentials not found. "
                f"Please add to {config.env_path}:\n"
                "  BITRIX_WEBHOOK_URL=https://domain.bitrix24.ru/rest/1/token/\n"
                "or:\n"
                "  BITRIX_DOMAIN=domain.bitrix24.ru\n"
                "  BITRIX_WEBHOOK=1/token"
            )

        # Убедиться что URL заканчивается на /
        if not self.webhook_url.endswith('/'):
            self.webhook_url += '/'

        # HTTP session для переиспользования соединений
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'KB-Automation/2.0',
            'Content-Type': 'application/json'
        })

        # VPN bypass: bind to en0 interface if available
        en0_ip = get_en0_ip()
        if en0_ip:
            adapter = SourceAddressAdapter(en0_ip)
            self.session.mount('https://', adapter)
            self.session.mount('http://', adapter)
            logger.info(f"VPN bypass: binding to en0 ({en0_ip})")

        logger.info(f"BitrixClient initialized with webhook: {self.webhook_url[:50]}...")

    def call(self, method: str, params: Dict = None, retry: int = 3) -> Any:
        """
        Вызвать метод Bitrix24 API

        Args:
            method: Название метода API (например, 'crm.deal.list')
            params: Параметры запроса
            retry: Количество попыток при ошибке

        Returns:
            Результат API вызова

        Raises:
            Exception: При ошибке API или сети после всех попыток
        """
        url = f"{self.webhook_url}{method}.json"
        params = params or {}

        for attempt in range(retry):
            try:
                logger.debug(f"Calling {method} (attempt {attempt + 1}/{retry})")

                response = self.session.post(url, json=params, timeout=30)
                response.raise_for_status()

                data = response.json()

                # Проверить ошибки Bitrix24 API
                if 'error' in data:
                    error_msg = data.get('error_description', data['error'])
                    logger.error(f"Bitrix API error in {method}: {error_msg}")
                    raise Exception(f"Bitrix API error: {error_msg}")

                # Вернуть результат
                if 'result' in data:
                    return data['result']
                else:
                    return data

            except requests.exceptions.RequestException as e:
                logger.warning(f"Request failed (attempt {attempt + 1}/{retry}): {e}")

                if attempt < retry - 1:
                    # Exponential backoff: 1s, 2s, 4s
                    sleep_time = 2 ** attempt
                    logger.info(f"Retrying in {sleep_time}s...")
                    time.sleep(sleep_time)
                else:
                    logger.error(f"All {retry} attempts failed for {method}")
                    raise

    def call_batch(self, calls: Dict[str, str]) -> Dict:
        """
        Batch запрос (до 50 вызовов за раз)

        Args:
            calls: Словарь {key: method_call}
                   Например: {'deals': 'crm.deal.list?select[]=ID'}

        Returns:
            Словарь результатов {key: result}

        Raises:
            ValueError: Если количество вызовов > 50
        """
        if len(calls) > 50:
            raise ValueError(f"Batch size must be <= 50 (got {len(calls)})")

        logger.info(f"Executing batch request with {len(calls)} calls")

        result = self.call('batch', {
            'halt': 0,  # Продолжить выполнение при ошибке
            'cmd': calls
        })

        return result

    def get_all(self, method: str, params: Dict = None, max_pages: int = 1000) -> List[Dict]:
        """
        Получить все записи с автоматической пагинацией

        Bitrix24 возвращает максимум 50 записей за запрос.
        Этот метод автоматически делает несколько запросов для получения всех данных.

        Args:
            method: Название метода API
            params: Параметры запроса
            max_pages: Максимальное количество страниц (защита от бесконечного цикла)

        Returns:
            Список всех записей
        """
        params = params or {}
        all_items = []
        start = 0
        page = 1
        total = None

        while page <= max_pages:
            params['start'] = start

            logger.debug(f"Fetching page {page} (start={start})...")
            result = self.call(method, params)

            # Обработать разные форматы ответов Bitrix24
            items = []
            if isinstance(result, dict):
                # Извлечь total если доступен
                if 'total' in result:
                    total = int(result['total'])

                # Формат: {'items': [...], 'total': N}
                if 'items' in result:
                    items = result['items']
                # Формат: {'tasks': [...]} - для tasks.task.list
                elif 'tasks' in result:
                    items = result['tasks']
                # Формат: {'result': [...]}
                elif 'result' in result:
                    items = result['result'] if isinstance(result['result'], list) else [result['result']]
                else:
                    # Неожиданный формат - взять весь result
                    items = [result]
            elif isinstance(result, list):
                items = result
            else:
                items = [result]

            all_items.extend(items)

            # Проверяем условия выхода:
            # 1. Если total известен и мы получили все записи
            if total is not None and len(all_items) >= total:
                break
            # 2. Если получили меньше 50 записей - это последняя страница
            if len(items) < 50:
                break
            # 3. Если ничего не получили
            if len(items) == 0:
                break

            start += 50
            page += 1

        if page > max_pages:
            logger.warning(f"Reached max_pages limit ({max_pages}) for {method}")

        logger.info(f"Retrieved {len(all_items)} total items from {method} ({page} pages)")
        return all_items

    def test_connection(self) -> bool:
        """
        Проверить подключение к Bitrix24

        Returns:
            True если подключение успешно
        """
        try:
            result = self.call('profile')
            user_name = f"{result.get('NAME', '')} {result.get('LAST_NAME', '')}".strip()
            logger.info(f"✅ Connection successful. User: {user_name}")
            return True
        except Exception as e:
            logger.error(f"❌ Connection failed: {e}")
            return False


# Тестирование
if __name__ == '__main__':
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )

    print("=== Testing BitrixClient ===\n")

    try:
        # Создать клиента
        client = BitrixClient()

        # Тест 1: Проверка подключения
        print("\n1. Testing connection...")
        if not client.test_connection():
            print("❌ Connection test failed")
            exit(1)

        # Тест 2: Получить текущего пользователя
        print("\n2. Getting current user...")
        user = client.call('profile')
        print(f"   User: {user.get('NAME')} {user.get('LAST_NAME')}")
        print(f"   Email: {user.get('EMAIL')}")

        # Тест 3: Получить список сделок (первые 5)
        print("\n3. Getting deals (first 5)...")
        deals = client.call('crm.deal.list', {
            'order': {'DATE_CREATE': 'DESC'},
            'filter': {},
            'select': ['ID', 'TITLE', 'OPPORTUNITY'],
            'start': 0
        })

        if isinstance(deals, list):
            print(f"   Retrieved {len(deals)} deals")
            for deal in deals[:5]:
                title = deal.get('TITLE', 'No title')
                amount = deal.get('OPPORTUNITY', 0)
                print(f"   - Deal #{deal['ID']}: {title} - {amount} RUB")

        print("\n✅ All tests passed!")

    except Exception as e:
        print(f"\n❌ Tests failed: {e}")
        import traceback
        traceback.print_exc()
        exit(1)
