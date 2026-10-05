"""Read-side queries. Views and serializers call these; they never build
ad-hoc querysets about "who may see what" themselves."""

from django.utils import timezone

from accounts.models import FamilyLink, User
from classes.models import ClassEnrollment, Session

from .models import SessionFeedback
from .policies import is_within_feedback_window


def represented_students(user):
    """Students this user may act for: themselves (student) or linked children (parent)."""
    if user.role == User.Role.STUDENT:
        return User.objects.filter(pk=user.pk)
    if user.role == User.Role.PARENT:
        return User.objects.filter(family_parents__parent=user, role=User.Role.STUDENT)
    return User.objects.none()


def feedback_visible_to(user):
    """Feedback for the students this user represents (student-facing view)."""
    return (
        SessionFeedback.objects.filter(student__in=represented_students(user))
        .select_related("session", "session__class_obj", "student", "created_by")
        .order_by("-created_at", "-id")
    )


def eligible_session_pairs(user, now=None):
    """
    (student, session) pairs the user can still review: enrolled, completed,
    inside the feedback window, not yet reviewed. Mirrors the submission rules.
    """
    now = now or timezone.now()
    students = list(represented_students(user))
    if not students:
        return []

    enrollments = list(
        ClassEnrollment.objects.filter(student__in=students, is_active=True).values_list(
            "student_id", "class_obj_id"
        )
    )
    reviewed = set(
        SessionFeedback.objects.filter(student__in=students).values_list(
            "student_id", "session_id"
        )
    )
    class_ids = {class_id for _, class_id in enrollments}
    sessions = list(
        Session.objects.filter(class_obj_id__in=class_ids, status=Session.Status.COMPLETED)
        .select_related("class_obj")
        .order_by("-scheduled_date")
    )
    students_by_id = {s.id: s for s in students}

    pairs = []
    for student_id, class_id in enrollments:
        for session in sessions:
            if (
                session.class_obj_id == class_id
                and (student_id, session.id) not in reviewed
                and is_within_feedback_window(session, now)
            ):
                pairs.append((students_by_id[student_id], session))
    pairs.sort(key=lambda p: (p[1].scheduled_date, p[1].id), reverse=True)
    return pairs


def session_audience(session):
    """
    {user_id: [student_ids]} -- who should hear that this session was completed:
    every actively enrolled student, and their linked parents (for those students).
    """
    student_ids = list(
        ClassEnrollment.objects.filter(
            class_obj_id=session.class_obj_id, is_active=True
        ).values_list("student_id", flat=True)
    )
    audience = {student_id: [student_id] for student_id in student_ids}
    for parent_id, student_id in FamilyLink.objects.filter(
        student_id__in=student_ids
    ).values_list("parent_id", "student_id"):
        audience.setdefault(parent_id, []).append(student_id)
    return audience
