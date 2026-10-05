# File: backend/accounts/urls.py
# Purpose: URL routes for /api/v1/accounts/.
# Contents:
#   - urlpatterns: login/ -> LoginView, profile/ -> ProfileView.

from django.urls import path
from . import views

urlpatterns = [
    path("login/", views.LoginView.as_view(), name="login"),
    path("profile/", views.ProfileView.as_view(), name="profile"),
]
