from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from django.views.generic import TemplateView

urlpatterns = [
    # Фронтенд — главная страница
    path('', TemplateView.as_view(template_name='index.html'), name='home'),

    # Админка
    path('admin/', admin.site.urls),

    # API
    path('api/', include('api.urls')),
] + static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)

admin.site.site_header = "TheKubanych Portfolio"
admin.site.site_title = "Portfolio Admin"
admin.site.index_title = "Управление портфолио"
