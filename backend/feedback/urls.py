# This file is already included in config/urls.py at /api/v1/feedback/

from django.urls import path

from . import views

urlpatterns = [
    path("", views.FeedbackCreateView.as_view(), name="feedback-create"),
    path("my/", views.MyFeedbackListView.as_view(), name="feedback-my"),
    path(
        "eligible-sessions/",
        views.EligibleSessionListView.as_view(),
        name="feedback-eligible-sessions",
    ),
    path(
        "instructor-summary/",
        views.InstructorSummaryView.as_view(),
        name="feedback-instructor-summary",
    ),
    path("events/", views.FeedbackEventsView.as_view(), name="feedback-events"),
]
