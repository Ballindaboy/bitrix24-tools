"""
Bitrix24 Collectors - коллекторы данных из Bitrix24

Все коллекторы наследуются от BaseCollector и используют BitrixClient.
"""

from .crm_collector import CRMCollector
from .tasks_collector import TasksCollector
from .task_comments_collector import TaskCommentsCollector
from .calendar_collector import CalendarCollector
from .activity_collector import ActivityCollector
from .users_collector import UsersCollector
from .contacts_collector import ContactsCollector
from .chats_collector import ChatsCollector
from .disk_collector import DiskCollector
from .companies_collector import CompaniesCollector
from .departments_collector import DepartmentsCollector
from .calls_collector import CallsCollector
from .livefeed_collector import LivefeedCollector

__all__ = [
    'CRMCollector',
    'TasksCollector',
    'TaskCommentsCollector',
    'CalendarCollector',
    'ActivityCollector',
    'UsersCollector',
    'ContactsCollector',
    'ChatsCollector',
    'DiskCollector',
    'CompaniesCollector',
    'DepartmentsCollector',
    'CallsCollector',
    'LivefeedCollector',
]
