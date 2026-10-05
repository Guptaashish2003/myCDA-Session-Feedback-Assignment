# File: backend/config/urls.py
# Purpose: Root URL configuration.
# Contents:
#   - urlpatterns: mounts /admin/, and the accounts, classes and feedback apps under /api/v1/.

from django.contrib import admin
from django.urls import path, include

urlpatterns = [
    path("admin/", admin.site.urls),
    path("api/v1/accounts/", include("accounts.urls")),
    path("api/v1/classes/", include("classes.urls")),
    path("api/v1/feedback/", include("feedback.urls")),
]
