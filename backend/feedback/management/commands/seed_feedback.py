# File: backend/feedback/management/commands/seed_feedback.py
# Purpose: `python manage.py seed_feedback`: optional demo reviews (run after seed_data).
# Contents:
#   - Command.handle(): adds reviews for completed sessions that are already outside the feedback
#     window, so the instructor summary has data while the open sessions stay reviewable for
#     manual tests.

"""
OPTIONAL demo data: python manage.py seed_feedback

Run after `seed_data`. Adds reviews for already-completed sessions so the
instructor summary has something to aggregate. It never touches the
students' still-open (eligible) sessions, so the submission form can still
be exercised with the test accounts -- see TEST_ACCOUNTS.md.
"""

import random

from django.core.management.base import BaseCommand

from accounts.models import FamilyLink
from classes.models import ClassEnrollment, Session
from feedback.models import SessionFeedback
from feedback.policies import is_within_feedback_window


class Command(BaseCommand):
    help = "Add demo feedback for older completed sessions (run after seed_data)"

    def handle(self, *args, **options):
        rng = random.Random(7)
        created = 0
        for session in Session.objects.filter(status=Session.Status.COMPLETED).select_related(
            "class_obj"
        ):
            # Leave the sessions that are still open for review untouched.
            if is_within_feedback_window(session):
                continue
            enrolled = ClassEnrollment.objects.filter(
                class_obj=session.class_obj, is_active=True
            ).select_related("student")
            for enrollment in enrolled:
                student = enrollment.student
                parent_link = FamilyLink.objects.filter(student=student).first()
                _, was_created = SessionFeedback.objects.get_or_create(
                    session=session,
                    student=student,
                    defaults={
                        "created_by": parent_link.parent if parent_link else student,
                        "rating_clarity": rng.randint(3, 5),
                        "rating_engagement": rng.randint(2, 5),
                        "rating_pace": rng.randint(2, 5),
                        "note": "Demo feedback" if rng.random() < 0.5 else "",
                    },
                )
                created += was_created
        self.stdout.write(self.style.SUCCESS(f"Created {created} demo feedback entries."))
