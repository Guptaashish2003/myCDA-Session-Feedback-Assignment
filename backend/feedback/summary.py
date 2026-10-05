# File: backend/feedback/summary.py
# Purpose: Instructor-facing anonymized aggregation (weighted rolling average).
# Contents:
#   - weighted_average(pairs): sum(weight * value) / sum(weight), or None without weight.
#   - valid_duration(session): reads duration_minutes from session_metadata; no invented default.
#   - compute_summary(per_session): pure maths: per-dimension and overall duration-weighted
#     averages plus total count.
#   - InstructorSummaryService.summarize(): takes the last N completed sessions, fetches only per-
#     session counts and averages (never student, submitter or note columns), computes the
#     summary, hides averages below the minimum review count and rounds to 2 decimals.

"""
Instructor-facing aggregation: weighted rolling average over the last N
completed sessions.

The maths lives in pure functions (no ORM) so it can be unit-tested with
plain numbers. The service only fetches aggregates -- it never selects
student, submitter or note columns, so there is nothing identifying to leak.
"""

from django.conf import settings
from django.db.models import Avg, Count

from classes.models import Session

from .models import SessionFeedback

DIMENSIONS = ("clarity", "engagement", "pace")


def summary_window():
    return getattr(settings, "FEEDBACK_SUMMARY_WINDOW", 10)


def min_responses():
    return getattr(settings, "FEEDBACK_SUMMARY_MIN_RESPONSES", 3)


def weighted_average(pairs):
    """sum(weight * value) / sum(weight); None when there is no weight."""
    pairs = list(pairs)
    total_weight = sum(weight for _, weight in pairs)
    if total_weight <= 0:
        return None
    return sum(value * weight for value, weight in pairs) / total_weight


def valid_duration(session):
    """Read duration straight from session_metadata; no silent default."""
    duration = (session.session_metadata or {}).get("duration_minutes")
    if isinstance(duration, bool) or not isinstance(duration, (int, float)) or duration <= 0:
        return None
    return duration


def compute_summary(per_session):
    """
    per_session: iterable of dicts
        {"duration": int, "count": int, "clarity": float, "engagement": float, "pace": float}
    where each dimension is that session's own average rating.
    """
    per_session = list(per_session)
    averages = {
        dim: weighted_average((s[dim], s["duration"]) for s in per_session)
        for dim in DIMENSIONS
    }
    overall_by_session = [
        (sum(s[dim] for dim in DIMENSIONS) / len(DIMENSIONS), s["duration"])
        for s in per_session
    ]
    averages["overall"] = weighted_average(overall_by_session)
    return {
        "averages": averages,
        "total_feedback_count": sum(s["count"] for s in per_session),
        "sessions_with_feedback": len(per_session),
    }


class InstructorSummaryService:
    def __init__(self, window=None, minimum=None):
        self.window = window or summary_window()
        self.minimum = minimum if minimum is not None else min_responses()

    def summarize(self, instructor=None):
        sessions = Session.objects.filter(status=Session.Status.COMPLETED)
        if instructor is not None:
            sessions = sessions.filter(class_obj__instructor=instructor)
        window_sessions = list(sessions.order_by("-scheduled_date", "-id")[: self.window])

        durations = {
            s.id: d for s in window_sessions if (d := valid_duration(s)) is not None
        }
        rows = (
            SessionFeedback.objects.filter(session_id__in=durations)
            .values("session_id")
            .annotate(
                count=Count("id"),
                clarity=Avg("rating_clarity"),
                engagement=Avg("rating_engagement"),
                pace=Avg("rating_pace"),
            )
        )
        per_session = [{**row, "duration": durations[row["session_id"]]} for row in rows]

        result = compute_summary(per_session)
        meets_threshold = result["total_feedback_count"] >= self.minimum
        averages = result["averages"]
        if not meets_threshold:
            # Too few reviews: even an anonymous average could point at one student.
            averages = {key: None for key in averages}

        return {
            "window_size": self.window,
            "sessions_in_window": len(window_sessions),
            "sessions_with_feedback": result["sessions_with_feedback"],
            "total_feedback_count": result["total_feedback_count"],
            "minimum_responses": self.minimum,
            "meets_anonymity_threshold": meets_threshold,
            "averages": {
                key: None if value is None else round(value, 2)
                for key, value in averages.items()
            },
        }
