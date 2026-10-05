# File: backend/feedback/apps.py
# Purpose: App configuration for feedback.
# Contents:
#   - FeedbackConfig.ready(): imports receivers so the session_completed signal handler is
#     connected at start-up.

from django.apps import AppConfig


class FeedbackConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "feedback"

    def ready(self):
        from . import receivers  # noqa: F401  (connects signal handlers)
