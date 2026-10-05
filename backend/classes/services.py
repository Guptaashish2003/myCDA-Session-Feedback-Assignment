# File: backend/classes/services.py
# Purpose: Business logic for completing a session (kept out of the view).
# Contents:
#   - SessionNotCompletable: raised when the session is not scheduled.
#   - complete_session(session, now): sets status=completed, stores completed_at in
#     session_metadata, saves, then sends the session_completed signal exactly once per
#     transition.

from django.utils import timezone

from .models import Session
from .signals import session_completed


class SessionNotCompletable(Exception):
    """Raised when a session is not in a state that can be completed."""


def complete_session(session, now=None):
    """
    Mark a scheduled session as completed and announce it.

    The completion time is recorded in `session_metadata["completed_at"]`
    (the metadata is the model's documented place for variable session
    data, so no schema change is needed). Idempotency: only a `scheduled`
    session can transition; the signal fires exactly once per transition.
    """
    if session.status != Session.Status.SCHEDULED:
        raise SessionNotCompletable(
            f"Only scheduled sessions can be completed (this one is {session.status})."
        )

    session.status = Session.Status.COMPLETED
    session.session_metadata = {
        **session.session_metadata,
        "completed_at": (now or timezone.now()).isoformat(),
    }
    session.save(update_fields=["status", "session_metadata", "updated_at"])
    session_completed.send(sender=Session, session=session)
    return session
