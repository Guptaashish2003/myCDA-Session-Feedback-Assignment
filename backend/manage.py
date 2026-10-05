#!/usr/bin/env python
# File: backend/manage.py
# Purpose: Django's command-line entry point (runserver, migrate, test, seed_data, ...).
# Contents:
#   - main(): sets DJANGO_SETTINGS_MODULE=config.settings, then hands sys.argv to Django's
#     execute_from_command_line.
"""Django's command-line utility for administrative tasks."""
import os
import sys


def main():
    """Run administrative tasks."""
    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")
    try:
        from django.core.management import execute_from_command_line
    except ImportError as exc:
        raise ImportError(
            "Couldn't import Django. Are you sure it's installed and "
            "available on your PYTHONPATH environment variable? Did you "
            "forget to activate a virtual environment?"
        ) from exc
    execute_from_command_line(sys.argv)


if __name__ == "__main__":
    main()
