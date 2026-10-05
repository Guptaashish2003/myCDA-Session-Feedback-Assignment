# File: backend/classes/urls.py
# Purpose: URL routes for /api/v1/classes/.
# Contents:
#   - urlpatterns: '' list, <class_id>/sessions/, sessions/<session_id>/complete/, enrollments/.

from django.urls import path
from . import views

urlpatterns = [
    path("", views.ClassListView.as_view(), name="class-list"),
    path(
        "<int:class_id>/sessions/",
        views.SessionListView.as_view(),
        name="session-list",
    ),
    path(
        "sessions/<int:session_id>/complete/",
        views.CompleteSessionView.as_view(),
        name="session-complete",
    ),
    path(
        "enrollments/",
        views.MyEnrollmentsView.as_view(),
        name="my-enrollments",
    ),
]
