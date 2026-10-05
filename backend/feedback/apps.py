from django.apps import AppConfig


class FeedbackConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "feedback"

    def ready(self):
        from . import receivers  # noqa: F401  (connects signal handlers)
