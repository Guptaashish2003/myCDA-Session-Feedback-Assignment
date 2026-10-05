from django.conf import settings
from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import models

from classes.models import Session

RATING_MIN = 1
RATING_MAX = 5
NOTE_MAX_LENGTH = 500


def rating_field(help_text):
    return models.PositiveSmallIntegerField(
        validators=[MinValueValidator(RATING_MIN), MaxValueValidator(RATING_MAX)],
        help_text=help_text,
    )


class SessionFeedback(models.Model):
    """
    A structured review of one completed session, written on behalf of
    one student.

    `student` is who the feedback represents; `created_by` is who typed it
    (the student, or a linked parent). They are kept apart so that:
      * uniqueness is per (session, student) -- a parent re-submitting for
        the same child is still a duplicate, and
      * `created_by` follows the project-wide audit-field convention used
        by `core.serializers.BaseModelSerializer`.

    The three dimensions are separate columns, not one blended score, so the
    instructor summary can average each of them independently.
    """

    session = models.ForeignKey(
        Session,
        on_delete=models.CASCADE,
        related_name="feedback_entries",
    )
    student = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="session_feedback",
        limit_choices_to={"role": "student"},
    )
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="submitted_feedback",
        help_text="The submitter: the student themselves or a linked parent.",
    )

    rating_clarity = rating_field("How clearly the instructor explained concepts.")
    rating_engagement = rating_field("How engaging the session was.")
    rating_pace = rating_field("Whether the pacing felt right.")
    note = models.TextField(blank=True, max_length=NOTE_MAX_LENGTH)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at", "-id"]
        unique_together = ("session", "student")
        constraints = [
            models.CheckConstraint(
                check=models.Q(rating_clarity__gte=RATING_MIN, rating_clarity__lte=RATING_MAX),
                name="feedback_rating_clarity_range",
            ),
            models.CheckConstraint(
                check=models.Q(rating_engagement__gte=RATING_MIN, rating_engagement__lte=RATING_MAX),
                name="feedback_rating_engagement_range",
            ),
            models.CheckConstraint(
                check=models.Q(rating_pace__gte=RATING_MIN, rating_pace__lte=RATING_MAX),
                name="feedback_rating_pace_range",
            ),
        ]

    @property
    def submitter(self):
        """Readable alias for the audit field `created_by`."""
        return self.created_by

    def __str__(self):
        return f"Feedback by/for {self.student_id} on session {self.session_id}"
