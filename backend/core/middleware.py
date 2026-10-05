# File: backend/core/middleware.py
# Purpose: Request audit middleware that exposes the current user through thread-local storage.
# Contents:
#   - RequestAuditMiddleware: stores request.user in a thread-local for the duration of a request
#     and clears it afterwards.
#   - get_current_user(): returns that user (or None). Limitation: it captures Django's session
#     user before DRF token auth runs, so for token requests it is anonymous; the feedback view
#     therefore passes created_by explicitly.

"""
Request audit middleware.

Attaches the authenticated user to thread-local storage so that
model-layer code (e.g. BaseModelSerializer.create) can access the
current user without passing `request` through every layer.

Usage in serializers / models:
    from core.middleware import get_current_user
    user = get_current_user()
"""

import threading

_thread_locals = threading.local()


def get_current_user():
    """Return the user attached by RequestAuditMiddleware, or None."""
    return getattr(_thread_locals, "user", None)


class RequestAuditMiddleware:
    """
    Stores the authenticated user in thread-local storage for the
    duration of the request. Downstream code can call
    `get_current_user()` to retrieve it.
    """

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        _thread_locals.user = getattr(request, "user", None)
        try:
            response = self.get_response(request)
        finally:
            # Clean up after the request to avoid leaking across threads
            _thread_locals.user = None
        return response
