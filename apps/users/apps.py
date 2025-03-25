from django.apps import AppConfig


class UsersConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.users"
    
    # 시그널 보내
    def ready(self):
        import apps.users.signals