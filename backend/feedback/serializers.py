# File: backend/feedback/serializers.py
# Purpose: Serializers for the feedback API (separate shapes for submit, history and instructors).
# Contents:
#   - FeedbackCreateSerializer: write serializer: student optional (defaults to self for students,
#     required for parents), runs FeedbackSubmissionPolicy in validate(), maps rule errors to 400
#     / 403 and a race IntegrityError to the duplicate message; created_by is not writable.
#   - FeedbackSerializer: student/parent-facing review with class name, date, ratings, note and
#     submitter display name.
#   - EligibleSessionSerializer: a (student, session) pair that can still be reviewed.
#   - InstructorSummarySerializer (+ SummaryAveragesSerializer): plain serializers with no model:
#     an explicit whitelist of aggregate numbers, so no student, submitter or note can leak.

from django.db import IntegrityError
from django.utils import timezone
from rest_framework import serializers
from rest_framework.exceptions import PermissionDenied

from accounts.models import User
from accounts.serializers import UserMinimalSerializer
from classes.models import Session
from core.serializers import BaseModelSerializer, ReadOnlyBaseSerializer

from .models import NOTE_MAX_LENGTH, SessionFeedback
from .policies import (
    FeedbackSubmissionPolicy,
    NotAllowed,
    RuleViolation,
    SubmissionContext,
)
from .summary import DIMENSIONS

RATING_FIELDS = ["rating_clarity", "rating_engagement", "rating_pace"]
DUPLICATE_MESSAGE = "Feedback already submitted for this session."


class FeedbackCreateSerializer(BaseModelSerializer):
    """
    Write serializer. `created_by` (the submitter) is NOT a writable field:
    the view supplies it from the authenticated user. `student` is optional
    so a student can omit it (defaults to themselves); a parent must send it.
    """

    student = serializers.PrimaryKeyRelatedField(
        queryset=User.objects.filter(role=User.Role.STUDENT), required=False
    )
    note = serializers.CharField(
        required=False, allow_blank=True, max_length=NOTE_MAX_LENGTH
    )

    class Meta:
        model = SessionFeedback
        fields = ["id", "session", "student", *RATING_FIELDS, "note"]
        # Duplicates are reported by FeedbackSubmissionPolicy with a friendly
        # message; DRF's auto UniqueTogetherValidator would force `student`.
        validators = []

    def __init__(self, *args, policy=None, **kwargs):
        super().__init__(*args, **kwargs)
        self._policy = policy or FeedbackSubmissionPolicy()

    def validate(self, attrs):
        actor = self.context["request"].user
        student = attrs.get("student")
        if student is None:
            if actor.role != User.Role.STUDENT:
                raise serializers.ValidationError(
                    {"student": "Select which student this feedback is for."}
                )
            student = actor
            attrs["student"] = student

        ctx = SubmissionContext(
            actor=actor, student=student, session=attrs["session"], now=timezone.now()
        )
        try:
            self._policy.validate(ctx)
        except NotAllowed as exc:
            raise PermissionDenied(exc.message)
        except RuleViolation as exc:
            raise serializers.ValidationError({exc.field: exc.message})
        return attrs

    def create(self, validated_data):
        try:
            return super().create(validated_data)
        except IntegrityError:
            # Lost a race with a concurrent submission for the same (session, student).
            raise serializers.ValidationError({"session": DUPLICATE_MESSAGE})


class FeedbackSerializer(ReadOnlyBaseSerializer):
    """Student/parent-facing representation of a submitted review."""

    class_name = serializers.CharField(source="session.class_obj.name", read_only=True)
    session_date = serializers.DateTimeField(source="session.scheduled_date", read_only=True)
    topic = serializers.CharField(source="session.topic", read_only=True)
    student_display = UserMinimalSerializer(source="student", read_only=True)

    class Meta:
        model = SessionFeedback
        fields = [
            "id",
            "session",
            "class_name",
            "session_date",
            "topic",
            "student",
            "student_display",
            *RATING_FIELDS,
            "note",
            "created_by_display",
            "created_at",
            "updated_at",
        ]


class EligibleSessionSerializer(serializers.Serializer):
    """A (student, session) pair that can still receive feedback."""

    session = serializers.IntegerField(source="session.id")
    class_name = serializers.CharField(source="session.class_obj.name")
    scheduled_date = serializers.DateTimeField(source="session.scheduled_date")
    topic = serializers.CharField(source="session.topic")
    duration_minutes = serializers.IntegerField(source="session.duration_minutes")
    student = serializers.IntegerField(source="student.id")
    student_display = UserMinimalSerializer(source="student")


class SummaryAveragesSerializer(serializers.Serializer):
    """Weighted averages per dimension. Declared explicitly -- a whitelist."""

    clarity = serializers.FloatField(allow_null=True)
    engagement = serializers.FloatField(allow_null=True)
    pace = serializers.FloatField(allow_null=True)
    overall = serializers.FloatField(allow_null=True)


class InstructorSummarySerializer(serializers.Serializer):
    """
    Instructor-facing aggregate. This is a plain Serializer with NO model
    behind it: there is no student, submitter or note field to expose, now
    or by accident when the model grows.
    """

    window_size = serializers.IntegerField()
    sessions_in_window = serializers.IntegerField()
    sessions_with_feedback = serializers.IntegerField()
    total_feedback_count = serializers.IntegerField()
    minimum_responses = serializers.IntegerField()
    meets_anonymity_threshold = serializers.BooleanField()
    averages = SummaryAveragesSerializer()
