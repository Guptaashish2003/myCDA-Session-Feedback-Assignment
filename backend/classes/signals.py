# File: backend/classes/signals.py
# Purpose: Domain signals emitted by the classes app.
# Contents:
#   - session_completed: Django Signal sent when a session becomes completed. Other apps
#     (feedback) subscribe, so classes never imports them.

"""
Domain signals emitted by the classes app.

Other apps (e.g. feedback) subscribe to these instead of the classes app
importing them -- classes stays unaware of who is listening.
"""

from django.dispatch import Signal

# Sent once when a session transitions into `completed`.
# Provides: session (classes.models.Session)
session_completed = Signal()
