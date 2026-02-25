from __future__ import annotations

from django.db import models
from django.core.validators import MinValueValidator, MaxValueValidator
from django.db.models import Sum


class TelegramUser(models.Model):
    telegram_id = models.BigIntegerField(
        unique=True,
        db_index=True,
        verbose_name='Telegram ID'
    )
    first_name = models.CharField(max_length=100, verbose_name='Имя')
    last_name = models.CharField(max_length=100, blank=True, verbose_name='Фамилия')
    username = models.CharField(max_length=100, blank=True, verbose_name='Username')

    # Если используешь Telegram Login Widget: url фото может приходить/меняться
    photo_url = models.URLField(blank=True, verbose_name='Фото')

    # ВАЖНО: auth_date НЕ должен быть auto_now.
    # Заполняй из данных Telegram (обычно приходит unix time, конвертируешь в datetime).
    auth_date = models.DateTimeField(null=True, blank=True, verbose_name='Дата авторизации (TG)')

    # Последний успешный вход/использование (можно обновлять при логине)
    last_login_at = models.DateTimeField(null=True, blank=True, verbose_name='Последний вход')

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = 'Telegram пользователь'
        verbose_name_plural = 'Telegram пользователи'
        ordering = ['-created_at']

    def __str__(self):
        name = self.first_name
        if self.last_name:
            name += f' {self.last_name}'
        if self.username:
            name += f' (@{self.username})'
        return name

    @property
    def full_name(self):
        return f'{self.first_name} {self.last_name}'.strip()


class Skill(models.Model):
    CATEGORY_CHOICES = [
        ('backend', 'Backend'),
        ('database', 'Database'),
        ('tools', 'Tools'),
        ('other', 'Other'),
    ]

    name = models.CharField(max_length=100)
    icon = models.CharField(max_length=10, default='💻')
    percent = models.PositiveIntegerField(
        default=50,
        validators=[MinValueValidator(0), MaxValueValidator(100)],
        verbose_name='Уровень (%)'
    )
    category = models.CharField(max_length=20, choices=CATEGORY_CHOICES, default='backend')
    order = models.PositiveIntegerField(default=0, validators=[MinValueValidator(0)])
    is_active = models.BooleanField(default=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['order']
        verbose_name = 'Навык'
        verbose_name_plural = 'Навыки'
        constraints = [
            models.UniqueConstraint(fields=['name', 'category'], name='uniq_skill_name_category'),
        ]

    def __str__(self):
        return f"{self.icon} {self.name} ({self.percent}%)"


class Project(models.Model):
    STATUS_CHOICES = [
        ('active', 'В процессе'),
        ('done', 'Завершён'),
        ('planned', 'Планируется'),
    ]

    title = models.CharField(max_length=200)
    slug = models.SlugField(max_length=220, blank=True, db_index=True)
    short_description = models.CharField(max_length=255, blank=True)
    description = models.TextField()

    # Оставляем JSONField как у тебя (быстро и просто)
    stack = models.JSONField(default=list)

    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='active')
    github_url = models.URLField(blank=True)
    demo_url = models.URLField(blank=True)

    is_featured = models.BooleanField(default=False)
    order = models.PositiveIntegerField(default=0, validators=[MinValueValidator(0)])
    is_active = models.BooleanField(default=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['order', '-created_at']
        verbose_name = 'Проект'
        verbose_name_plural = 'Проекты'
        indexes = [
            models.Index(fields=['status']),
            models.Index(fields=['is_active']),
            models.Index(fields=['is_featured']),
        ]

    def __str__(self):
        return self.title


class ContactMessage(models.Model):
    STATUS_CHOICES = [
        ('new', 'Новое'),
        ('read', 'Прочитано'),
        ('replied', 'Отвечено'),
    ]

    SOURCE_CHOICES = [
        ('site', 'Сайт'),
        ('telegram', 'Telegram'),
        ('other', 'Другое'),
    ]

    telegram_user = models.ForeignKey(
        TelegramUser,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        verbose_name='Telegram user'
    )

    source = models.CharField(
        max_length=20,
        choices=SOURCE_CHOICES,
        default='site',
        verbose_name='Источник'
    )

    name = models.CharField(max_length=100)
    email = models.EmailField(blank=True)
    subject = models.CharField(max_length=200)
    message = models.TextField()

    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='new')
    replied_at = models.DateTimeField(null=True, blank=True, verbose_name='Когда ответили')

    ip_address = models.GenericIPAddressField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']
        verbose_name = 'Сообщение'
        verbose_name_plural = 'Сообщения'
        indexes = [
            models.Index(fields=['status']),
            models.Index(fields=['source']),
            models.Index(fields=['created_at']),
        ]

    def __str__(self):
        via = f' @{self.telegram_user.username}' if self.telegram_user and self.telegram_user.username else ''
        return f"{self.name}{via} — {self.subject}"


class PageView(models.Model):
    date = models.DateField(auto_now_add=True, db_index=True)
    count = models.PositiveIntegerField(default=0, validators=[MinValueValidator(0)])
    unique_ips = models.JSONField(default=list)  # лучше хранить хеши, но оставляю как у тебя

    class Meta:
        ordering = ['-date']
        verbose_name = 'Просмотры'
        verbose_name_plural = 'Просмотры по дням'

    def __str__(self):
        return f"{self.date} — {self.count} просмотров"

    @classmethod
    def get_total(cls) -> int:
        # быстрее, чем sum() в Python
        return int(cls.objects.aggregate(total=Sum('count'))['total'] or 0)

    @classmethod
    def get_unique_total(cls) -> int:
        # если unique_ips будет большим, лучше вынести в отдельную таблицу
        all_ips = set()
        for row in cls.objects.values_list('unique_ips', flat=True):
            if isinstance(row, list):
                all_ips.update(row)
        return len(all_ips)