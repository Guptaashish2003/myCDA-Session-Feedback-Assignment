# File: backend/docker_start.py
# Purpose: Container start-up script used by backend/Dockerfile: migrate, seed if needed, run the
#     server.
# Contents:
#   - main(): runs migrate; seeds depending on SEED_ON_START (if-empty seeds only when there are
#     no users, always re-seeds, never skips); optionally runs seed_feedback when
#     SEED_FEEDBACK=true.
#   - os.execvp: replaces this process with `manage.py runserver 0.0.0.0:$PORT --noreload` so the
#     server receives docker stop signals.

"""
Container start-up script: migrate, seed (when needed), then run the server.

Environment variables:
  SEED_ON_START   if-empty (default) | always | never
                  if-empty seeds only when there are no users yet, so restarting
                  the container keeps existing data. always wipes and re-seeds.
  SEED_FEEDBACK   false (default) | true -- also add the optional demo reviews.
  PORT            port to listen on (default 8000).
"""

import os
import sys

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")

import django
from django.core.management import call_command

django.setup()

from accounts.models import User  # noqa: E402  (needs django.setup() first)


def main():
    call_command("migrate", interactive=False)

    mode = os.environ.get("SEED_ON_START", "if-empty").lower()
    has_users = User.objects.exists()
    if mode == "always" or (mode == "if-empty" and not has_users):
        call_command("seed_data")
        if os.environ.get("SEED_FEEDBACK", "false").lower() == "true":
            call_command("seed_feedback")
    else:
        print(f"Skipping seed (SEED_ON_START={mode}, users present={has_users}).")

    port = os.environ.get("PORT", "8000")
    sys.stdout.flush()
    # exec so the dev server receives SIGTERM from `docker stop`
    os.execvp(
        sys.executable,
        [sys.executable, "manage.py", "runserver", f"0.0.0.0:{port}", "--noreload"],
    )


if __name__ == "__main__":
    main()
