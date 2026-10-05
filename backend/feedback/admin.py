# File: backend/feedback/admin.py
# Purpose: Django admin registration for feedback.
# Contents:
#   - SessionFeedbackAdmin: lists reviews with ratings and filters by class.
# Register your model(s) here for the Django admin.

from django.contrib import admin

from .models import SessionFeedback


@admin.register(SessionFeedback)
class SessionFeedbackAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "session",
        "student",
        "created_by",
        "rating_clarity",
        "rating_engagement",
        "rating_pace",
        "created_at",
    )
    list_filter = ("session__class_obj",)
    raw_id_fields = ("session", "student", "created_by")
