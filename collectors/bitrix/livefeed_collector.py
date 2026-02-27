#!/usr/bin/env python3
"""
Livefeed Collector - Собирает ленту новостей из Bitrix24

Собирает посты из ленты (log.blogpost) за последний год:
- Посты, комментарии, голосования
- Автор, получатели, файлы
"""

import logging
from typing import Dict
from collections import Counter
from datetime import datetime, timedelta

from shared import BaseCollector

logger = logging.getLogger(__name__)


class LivefeedCollector(BaseCollector):
    """Собирает ленту новостей из Bitrix24"""

    def get_entity_name(self) -> str:
        return 'livefeed'

    def collect(self) -> Dict:
        """
        Собрать посты из ленты за последний год

        Returns:
            Словарь с данными:
            {
                'source': 'log.blogpost.get',
                'filter': '>=DATE_PUBLISH: YYYY-MM-DD',
                'total': 1234,
                'posts': [...]
            }
        """
        # Вычислить дату год назад
        one_year_ago = datetime.now() - timedelta(days=365)
        filter_date = one_year_ago.strftime('%Y-%m-%dT00:00:00')

        logger.info(f"Fetching livefeed posts from Bitrix24 (since {filter_date})...")

        # Получить посты ленты
        # log.blogpost.get возвращает посты с пагинацией
        posts = self.bitrix.get_all('log.blogpost.get', {
            'FILTER': {
                '>=DATE_PUBLISH': filter_date
            }
        })

        logger.info(f"Retrieved {len(posts)} posts")

        # Статистика по авторам
        authors = Counter()
        for post in posts:
            author_id = post.get('AUTHOR_ID', 'Unknown')
            author_name = post.get('AUTHOR_NAME', f'User {author_id}')
            authors[author_name] += 1

        top_authors = dict(authors.most_common(10))
        logger.info(f"Top 10 authors: {top_authors}")

        # Статистика по типам постов
        post_types = Counter()
        for post in posts:
            post_code = post.get('POST_CODE', 'UNKNOWN')
            post_types[post_code] += 1

        logger.info(f"Posts by type: {dict(post_types)}")

        # Статистика по месяцам
        by_month = Counter()
        for post in posts:
            date_str = post.get('DATE_PUBLISH', '')
            if date_str:
                try:
                    # Формат: "2026-02-19T15:30:00+03:00" или "2026-02-19 15:30:00"
                    date_part = date_str[:7]  # YYYY-MM
                    by_month[date_part] += 1
                except:
                    pass

        logger.info(f"Posts by month: {dict(sorted(by_month.items()))}")

        return {
            'source': 'log.blogpost.get',
            'filter': f'>=DATE_PUBLISH: {filter_date}',
            'total': len(posts),
            'stats': {
                'top_authors': top_authors,
                'by_type': dict(post_types),
                'by_month': dict(sorted(by_month.items()))
            },
            'posts': posts
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

    print("=== Testing Livefeed Collector ===\n")

    try:
        collector = LivefeedCollector()
        collector.run()

        import json
        snapshot_path = collector.get_snapshot_path()

        with open(snapshot_path, 'r') as f:
            snapshot = json.load(f)

        print(f"\n✅ Snapshot created at: {snapshot_path}")
        print(f"   Total posts: {snapshot['total']}")
        print(f"   Top authors: {snapshot['stats']['top_authors']}")
        print(f"   By type: {snapshot['stats']['by_type']}")

        print("\n✅ Livefeed collector test passed!")

    except Exception as e:
        print(f"\n❌ Livefeed collector test failed: {e}")
        import traceback
        traceback.print_exc()
        exit(1)
