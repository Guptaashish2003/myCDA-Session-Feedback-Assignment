# File: backend/classes/admin.py
# Purpose: Django admin registration for classes.
# Contents:
#   - ClassAdmin / ClassEnrollmentAdmin / SessionAdmin: list and filter classes, enrolments and
#     sessions.

from django.contrib import admin
from .models import Class, ClassEnrollment, Session


@admin.register(Class)
class ClassAdmin(admin.ModelAdmin):
    list_display = ("name", "instructor", "is_active")
    list_filter = ("is_active",)


@admin.register(ClassEnrollment)
class ClassEnrollmentAdmin(admin.ModelAdmin):
    list_display = ("class_obj", "student", "is_active", "enrolled_at")


@admin.register(Session)
class SessionAdmin(admin.ModelAdmin):
    list_display = ("class_obj", "scheduled_date", "status")
    list_filter = ("status", "class_obj")
