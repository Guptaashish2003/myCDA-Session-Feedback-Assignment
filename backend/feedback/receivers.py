# File: backend/feedback/receivers.py
# Purpose: Signal handler that turns a completed session into notifications.
# Contents:
#   - notify_session_completed: on classes.signals.session_completed, publishes a
#     session_completed event to every enrolled student and linked parent; each recipient only
#     receives their own student ids.

from django.dispatch import receiver

from classes.signals import session_completed

from .notifications import broker
from .selectors import session_audience


@receiver(session_completed, dispatch_uid="feedback.notify_session_completed")
def notify_session_completed(sender, session, **kwargs):
    """Tell each enrolled student / linked parent that feedback is now open."""
    class_name = session.class_obj.name
    for user_id, student_ids in session_audience(session).items():
        broker.publish(
            user_id,
            {
                "type": "session_completed",
                "session_id": session.id,
                "class_name": class_name,
                "student_ids": student_ids,
                "message": f"{class_name} was completed. Feedback is now open.",
            },
        )
