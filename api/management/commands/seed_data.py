from django.core.management.base import BaseCommand
from api.models import Skill, Project


class Command(BaseCommand):
    help = 'Начальные данные'

    def handle(self, *args, **kwargs):
        skills = [
            {'name': 'Python', 'icon': '🐍', 'percent': 75, 'category': 'backend', 'order': 1},
            {'name': 'FastAPI', 'icon': '⚡', 'percent': 65, 'category': 'backend', 'order': 2},
            {'name': 'Django', 'icon': '🎸', 'percent': 60, 'category': 'backend', 'order': 3},
            {'name': 'PostgreSQL', 'icon': '🗄️', 'percent': 60, 'category': 'database', 'order': 4},
            {'name': 'Git', 'icon': '🐙', 'percent': 70, 'category': 'tools', 'order': 5},
            {'name': 'Linux', 'icon': '🐧', 'percent': 55, 'category': 'tools', 'order': 6},
        ]
        for s in skills:
            Skill.objects.get_or_create(name=s['name'], defaults=s)

        projects = [
            {
                'title': 'Backend API приложение', 'order': 1, 'is_featured': True,
                'description': 'Серверная часть с авторизацией, БД и Swagger документацией.',
                'stack': ['Python', 'FastAPI', 'PostgreSQL'], 'status': 'active',
            },
            {
                'title': 'Telegram Bot', 'order': 2,
                'description': 'Бот на aiogram с inline-кнопками и внешними API.',
                'stack': ['Python', 'aiogram'], 'status': 'done',
            },
            {
                'title': 'Портфолио сайт', 'order': 3,
                'description': 'Этот сайт — фронтенд + Django бэкенд с API.',
                'stack': ['Django', 'HTML', 'CSS', 'JS'], 'status': 'done',
            },
        ]
        for p in projects:
            Project.objects.get_or_create(title=p['title'], defaults=p)

        self.stdout.write(self.style.SUCCESS('✅ Данные загружены!'))
