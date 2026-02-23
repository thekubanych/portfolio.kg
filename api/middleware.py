from datetime import date


class PageViewMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        response = self.get_response(request)
        skip = (
            request.method != 'GET' or
            request.path.startswith('/api/') or
            request.path.startswith('/admin/') or
            request.path.startswith('/static/') or
            request.path.startswith('/media/')
        )
        if not skip:
            self._record(request)
        return response

    def _record(self, request):
        try:
            from .models import PageView
            ip = request.META.get('HTTP_X_FORWARDED_FOR', '').split(',')[0].strip() \
                 or request.META.get('REMOTE_ADDR', '')
            pv, _ = PageView.objects.get_or_create(date=date.today())
            pv.count += 1
            if ip and ip not in pv.unique_ips:
                pv.unique_ips.append(ip)
            pv.save(update_fields=['count', 'unique_ips'])
        except Exception:
            pass
