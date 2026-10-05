# File: backend/config/wsgi.py
# Purpose: WSGI entry point for production-style servers.
# Contents:
#   - application: the WSGI callable created by get_wsgi_application() after setting the settings
#     module.

import os
from django.core.wsgi import get_wsgi_application

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")
application = get_wsgi_application()
