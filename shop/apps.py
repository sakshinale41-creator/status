from django.apps import AppConfig


class ShopConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'shop'

    def ready(self):
        try:
            from django.contrib.auth.models import User
            # Check if admin user already exists, if not create one automatically
            if not User.objects.filter(username='admin').exists():
                User.objects.create_superuser('admin', '', 'admin123')
        except Exception:
            pass