import hashlib
import hmac
import time
import requests
from datetime import date, timedelta
from django.conf import settings
from django.core.cache import cache
from django.core.mail import send_mail
from django.http import FileResponse, Http404
from rest_framework import status
from rest_framework.decorators import api_view
from rest_framework.response import Response
from .models import Skill, Project, ContactMessage, PageView, TelegramUser, WorkExperience, ResumeFile
from .serializers import SkillSerializer, ProjectSerializer, ContactMessageSerializer, WorkExperienceSerializer


# ── Skills ──
@api_view(['GET'])
def skills_list(request):
    return Response(SkillSerializer(Skill.objects.filter(is_active=True), many=True).data)


# ── Projects ──
@api_view(['GET'])
def projects_list(request):
    return Response(ProjectSerializer(Project.objects.filter(is_active=True), many=True).data)

@api_view(['GET'])
def project_detail(request, pk):
    try:
        project = Project.objects.get(pk=pk, is_active=True)
    except Project.DoesNotExist:
        return Response({'error': 'Не найден'}, status=status.HTTP_404_NOT_FOUND)
    return Response(ProjectSerializer(project).data)


# ── Telegram Auth ──
@api_view(['POST'])
def telegram_auth(request):
    """
    Принимает данные от Telegram Login Widget,
    проверяет подпись и сохраняет/обновляет пользователя.
    """
    data = request.data.copy()
    received_hash = data.pop('hash', None)

    if not received_hash:
        return Response({'error': 'Нет hash'}, status=status.HTTP_400_BAD_REQUEST)

    # Проверяем что данные свежие (не старше 24 часов)
    auth_date = int(data.get('auth_date', 0))
    if time.time() - auth_date > 86400:
        return Response({'error': 'Данные устарели'}, status=status.HTTP_400_BAD_REQUEST)

    # Проверяем подпись Telegram
    bot_token = settings.TELEGRAM_BOT_TOKEN
    if not bot_token:
        return Response({'error': 'Бот не настроен'}, status=status.HTTP_400_BAD_REQUEST)

    secret_key = hashlib.sha256(bot_token.encode()).digest()
    check_string = '\n'.join(f'{k}={v}' for k, v in sorted(data.items()))
    expected_hash = hmac.new(secret_key, check_string.encode(), hashlib.sha256).hexdigest()

    if not hmac.compare_digest(expected_hash, received_hash):
        return Response({'error': 'Неверная подпись'}, status=status.HTTP_403_FORBIDDEN)

    # Сохраняем пользователя
    tg_user, created = TelegramUser.objects.update_or_create(
        telegram_id=int(data['id']),
        defaults={
            'first_name': data.get('first_name', ''),
            'last_name': data.get('last_name', ''),
            'username': data.get('username', ''),
            'photo_url': data.get('photo_url', ''),
        }
    )

    return Response({
        'success': True,
        'user': {
            'id': tg_user.telegram_id,
            'name': tg_user.full_name,
            'username': tg_user.username,
            'photo_url': tg_user.photo_url,
        }
    })


# ── Contact Form ──
@api_view(['POST'])
def contact_send(request):
    data = request.data.copy()
    telegram_user_id = data.pop('telegram_user_id', None)
    data.pop('website', None)  # honeypot, уже проверен в сериализаторе

    # Rate limiting
    ip = _get_ip(request)
    cache_key = f"contact_{ip}"
    attempts = cache.get(cache_key, [])
    now = time.time()
    window = getattr(settings, 'CONTACT_RATE_WINDOW', 600)
    limit = getattr(settings, 'CONTACT_RATE_LIMIT', 3)
    attempts = [t for t in attempts if now - t < window]
    if len(attempts) >= limit:
        return Response(
            {'error': 'Слишком много сообщений. Подожди несколько минут.'},
            status=status.HTTP_429_TOO_MANY_REQUESTS
        )

    # Email необязателен если вошёл через Telegram
    if not data.get('email'):
        data['email'] = ''

    serializer = ContactMessageSerializer(data=data)
    if not serializer.is_valid():
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    tg_user = None
    if telegram_user_id:
        try:
            tg_user = TelegramUser.objects.get(telegram_id=int(telegram_user_id))
        except TelegramUser.DoesNotExist:
            pass

    msg = ContactMessage.objects.create(
        ip_address=ip,
        telegram_user=tg_user,
        source='telegram' if tg_user else 'site',
        **{k: v for k, v in serializer.validated_data.items() if k != 'website'}
    )

    attempts.append(now)
    cache.set(cache_key, attempts, window)

    _notify_telegram(msg)

    try:
        if data.get('email') and settings.EMAIL_HOST_USER:
            send_mail(
                subject=f'[Portfolio] {msg.subject}',
                message=f'От: {msg.name} <{msg.email}>\n\n{msg.message}',
                from_email=settings.EMAIL_HOST_USER,
                recipient_list=[settings.CONTACT_EMAIL],
                fail_silently=True,
            )
    except Exception:
        pass

    return Response(
        {'success': True, 'message': 'Сообщение отправлено! Отвечу как можно скорее 🚀'},
        status=status.HTTP_201_CREATED
    )


# ── Experience ──
@api_view(['GET'])
def experience_list(request):
    items = WorkExperience.objects.filter(is_active=True)
    return Response(WorkExperienceSerializer(items, many=True, context={'request': request}).data)


# ── CV Download ──
@api_view(['GET'])
def cv_download(request):
    """Возвращает URL активного CV или 404."""
    cv = ResumeFile.objects.filter(is_active=True).order_by('-updated_at').first()
    if not cv or not cv.file:
        return Response({'url': None}, status=status.HTTP_404_NOT_FOUND)
    from django.conf import settings
    url = request.build_absolute_uri(cv.file.url)
    return Response({'url': url})


# ── Stats ──
@api_view(['GET'])
def page_views_stats(request):
    today = date.today()
    last_7 = []
    for i in range(6, -1, -1):
        d = today - timedelta(days=i)
        try:
            count = PageView.objects.get(date=d).count
        except PageView.DoesNotExist:
            count = 0
        last_7.append({'date': str(d), 'views': count})
    try:
        today_views = PageView.objects.get(date=today).count
    except PageView.DoesNotExist:
        today_views = 0
    return Response({
        'total_views': PageView.get_total(),
        'unique_visitors': PageView.get_unique_total(),
        'today_views': today_views,
        'last_7_days': last_7,
    })


def _get_ip(request):
    x = request.META.get('HTTP_X_FORWARDED_FOR')
    return x.split(',')[0].strip() if x else request.META.get('REMOTE_ADDR')


def _notify_telegram(msg):
    token = settings.TELEGRAM_BOT_TOKEN
    chat_id = settings.TELEGRAM_CHAT_ID
    if not token or not chat_id:
        return
    tg_info = ''
    if msg.telegram_user:
        u = msg.telegram_user
        tg_info = f'\n🔗 *Telegram:* [{u.full_name}](tg://user?id={u.telegram_id})'
        if u.username:
            tg_info += f' @{u.username}'
    text = (
        f"📬 *Новое сообщение с портфолио!*\n\n"
        f"👤 *Имя:* {msg.name}{tg_info}\n"
        f"📧 *Email:* {msg.email or '—'}\n"
        f"📝 *Тема:* {msg.subject}\n\n"
        f"💬 *Сообщение:*\n{msg.message}"
    )
    try:
        requests.post(
            f'https://api.telegram.org/bot{token}/sendMessage',
            json={'chat_id': chat_id, 'text': text, 'parse_mode': 'Markdown'},
            timeout=5
        )
    except Exception:
        pass
