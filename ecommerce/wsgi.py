import os
from django.core.wsgi import get_wsgi_application

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'ecommerce.settings')

# Automatic superuser creation when WSGI loads the app in production
try:
    import django
    django.setup()
    from django.contrib.auth.models import User
    if not User.objects.filter(username='admin').exists():
        User.objects.create_superuser('admin', '', 'admin123')
except Exception:
    pass

application = get_wsgi_application()