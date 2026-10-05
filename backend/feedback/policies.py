"""
Submission rules for session feedback.

Each rule is a small class with one reason to change (SRP). The policy
runs a list of rules, so adding a rule never edits existing ones (OCP),
and anything exposing `check(ctx)` can be plugged in (LSP / DIP).
"""

from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Protocol, Sequence

from django.conf import settings
from django.utils import timezone
from django.utils.dateparse import parse_datetime

from accounts.models import FamilyLink, User
from classes.models import ClassEnrollment, Session

from .models import SessionFeedback


def feedback_window_days():
    return getattr(settings, "FEEDBACK_WINDOW_DAYS", 30)


def session_completed_at(session: Session) -> datetime:
    """When the session was completed.

    `complete_session()` records `completed_at` in the session metadata;
    sessions completed before that existed (e.g. seed data) fall back to
    their scheduled date.
    """
    raw = (session.session_metadata or {}).get("completed_at")
    parsed = parse_datetime(raw) if isinstance(raw, str) else None
    if parsed is not None and timezone.is_naive(parsed):
        parsed = timezone.make_aware(parsed)
    return parsed or session.scheduled_date


def is_within_feedback_window(session: Session, now=None) -> bool:
    now = now or timezone.now()
    return session_completed_at(session) >= now - timedelta(days=feedback_window_days())


class RuleViolation(Exception):
    """A submission rule failed -> HTTP 400 on `field`."""

    def __init__(self, message, field="non_field_errors"):
        super().__init__(message)
        self.message = message
        self.field = field


class NotAllowed(RuleViolation):
    """The actor may not act for this student -> HTTP 403."""


@dataclass(frozen=True)
class SubmissionContext:
    actor: User
    student: User
    session: Session
    now: datetime


class SubmissionRule(Protocol):
    def check(self, ctx: SubmissionContext) -> None: ...


class ActorCanActForStudent:
    """Only the student themselves, or a parent linked via FamilyLink."""

    def check(self, ctx):
        if ctx.actor.id == ctx.student.id and ctx.actor.role == User.Role.STUDENT:
            return
        if (
            ctx.actor.role == User.Role.PARENT
            and FamilyLink.objects.filter(parent=ctx.actor, student=ctx.student).exists()
        ):
            return
        raise NotAllowed(
            "You can only submit feedback for yourself or for a student linked to you.",
            field="student",
        )


class StudentEnrolledInClass:
    def check(self, ctx):
        enrolled = ClassEnrollment.objects.filter(
            class_obj_id=ctx.session.class_obj_id,
            student=ctx.student,
            is_active=True,
        ).exists()
        if not enrolled:
            raise RuleViolation(
                "This student is not enrolled in the class this session belongs to.",
                field="session",
            )


class SessionIsCompleted:
    def check(self, ctx):
        if ctx.session.status != Session.Status.COMPLETED:
            raise RuleViolation(
                "Feedback can only be submitted for completed sessions.",
                field="session",
            )


class SessionWithinWindow:
    def check(self, ctx):
        if not is_within_feedback_window(ctx.session, ctx.now):
            raise RuleViolation(
                f"Feedback is closed: this session was completed more than "
                f"{feedback_window_days()} days ago.",
                field="session",
            )


class NotAlreadySubmitted:
    """Uniqueness is per (session, student) -- not per submitter."""

    def check(self, ctx):
        if SessionFeedback.objects.filter(session=ctx.session, student=ctx.student).exists():
            raise RuleViolation(
                "Feedback already submitted for this session.",
                field="session",
            )


DEFAULT_RULES: Sequence[SubmissionRule] = (
    ActorCanActForStudent(),
    StudentEnrolledInClass(),
    SessionIsCompleted(),
    SessionWithinWindow(),
    NotAlreadySubmitted(),
)


class FeedbackSubmissionPolicy:
    def __init__(self, rules: Sequence[SubmissionRule] = DEFAULT_RULES):
        self._rules = rules

    def validate(self, ctx: SubmissionContext) -> None:
        for rule in self._rules:
            rule.check(ctx)
