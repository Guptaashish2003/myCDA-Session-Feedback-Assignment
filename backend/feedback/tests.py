# File: backend/feedback/tests.py
# Purpose: 34 tests for the feedback feature.
# Contents:
#   - SubmissionTests: student/parent submission, linked-parent rule, rating and note limits,
#     status and 30-day rules, per-student duplicates, enrolment.
#   - ListingTests: history scoping and ordering, eligible sessions.
#   - WeightedAverageTests / InstructorSummaryTests: weighted-average maths, last-10 window, no
#     default duration, anonymous response keys, minimum-review threshold, per-instructor scope,
#     admin filter.
#   - SessionCompletedEventTests: who is notified, parent payload, completion permissions, SSE
#     endpoint.

from datetime import timedelta

from django.test import SimpleTestCase, TestCase
from django.utils import timezone
from rest_framework import status
from rest_framework.test import APIClient

from accounts.models import FamilyLink, User
from classes.models import Class, ClassEnrollment, Session

from .models import SessionFeedback
from .notifications import broker
from .summary import InstructorSummaryService, compute_summary, weighted_average

RATINGS = {"rating_clarity": 4, "rating_engagement": 5, "rating_pace": 3}


def make_user(username, role):
    return User.objects.create_user(
        username=username,
        email=f"{username}@cda.test",
        password=None,  # tests authenticate via force_authenticate; skip slow hashing
        role=role,
        first_name=username.title(),
    )


def make_session(cls, days_ago=3, status_="completed", duration=60, **metadata):
    return Session.objects.create(
        class_obj=cls,
        scheduled_date=timezone.now() - timedelta(days=days_ago),
        status=status_,
        session_metadata={"duration_minutes": duration, "topic_covered": "T", **metadata},
    )


class FeedbackFixtureMixin:
    """Mirrors the TEST_ACCOUNTS.md cast on a smaller scale."""

    def setUp(self):
        self.sarah = make_user("sarah", "instructor")
        self.marcus = make_user("marcus", "instructor")
        self.admin = make_user("boss", "admin")
        self.james = make_user("james", "parent")
        self.priya = make_user("priya", "parent")
        self.emma = make_user("emma", "student")
        self.liam = make_user("liam", "student")
        self.anika = make_user("anika", "student")
        self.zara = make_user("zara", "student")
        FamilyLink.objects.create(parent=self.james, student=self.emma)
        FamilyLink.objects.create(parent=self.james, student=self.liam)
        FamilyLink.objects.create(parent=self.priya, student=self.anika)

        self.ld = Class.objects.create(name="LD", instructor=self.sarah)
        self.pf = Class.objects.create(name="PF", instructor=self.marcus)
        for student in (self.emma, self.liam, self.anika):
            ClassEnrollment.objects.create(class_obj=self.ld, student=student)
        for student in (self.zara, self.emma):
            ClassEnrollment.objects.create(class_obj=self.pf, student=student)

        self.session = make_session(self.ld)

    def client_for(self, user):
        client = APIClient()
        client.force_authenticate(user=user)
        return client

    def submit(self, user, session=None, **extra):
        body = {"session": (session or self.session).id, **RATINGS, **extra}
        return self.client_for(user).post("/api/v1/feedback/", body, format="json")


class SubmissionTests(FeedbackFixtureMixin, TestCase):
    def test_student_submits_for_self_and_student_defaults(self):
        response = self.submit(self.emma, note="Great")
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        entry = SessionFeedback.objects.get()
        self.assertEqual(entry.student, self.emma)
        self.assertEqual(entry.created_by, self.emma)
        self.assertEqual(response.data["note"], "Great")

    def test_parent_submits_for_linked_child(self):
        response = self.submit(self.james, student=self.liam.id)
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        entry = SessionFeedback.objects.get()
        self.assertEqual(entry.student, self.liam)
        self.assertEqual(entry.created_by, self.james)

    def test_parent_must_choose_a_student(self):
        response = self.submit(self.james)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("student", response.data)

    def test_parent_cannot_submit_for_unlinked_student(self):
        response = self.submit(self.priya, student=self.emma.id)
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
        self.assertEqual(SessionFeedback.objects.count(), 0)

    def test_student_cannot_submit_for_another_student(self):
        response = self.submit(self.emma, student=self.liam.id)
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_submitter_in_body_is_ignored(self):
        response = self.submit(self.emma, created_by=self.liam.id, submitter=self.liam.id)
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(SessionFeedback.objects.get().created_by, self.emma)

    def test_unauthenticated_and_instructor_cannot_submit(self):
        body = {"session": self.session.id, **RATINGS}
        self.assertEqual(
            APIClient().post("/api/v1/feedback/", body, format="json").status_code,
            status.HTTP_401_UNAUTHORIZED,
        )
        self.assertEqual(self.submit(self.sarah).status_code, status.HTTP_403_FORBIDDEN)

    def test_rejects_scheduled_and_cancelled_sessions(self):
        for state in ("scheduled", "cancelled"):
            session = make_session(self.ld, status_=state)
            response = self.submit(self.emma, session=session)
            self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST, state)
            self.assertIn("completed", str(response.data["session"]))

    def test_rejects_session_completed_more_than_30_days_ago(self):
        old = make_session(self.ld, days_ago=31)
        self.assertEqual(self.submit(self.emma, session=old).status_code, 400)
        recent = make_session(self.ld, days_ago=29)
        self.assertEqual(self.submit(self.emma, session=recent).status_code, 201)

    def test_completed_at_metadata_overrides_scheduled_date(self):
        old_but_just_completed = make_session(
            self.ld, days_ago=60, completed_at=timezone.now().isoformat()
        )
        self.assertEqual(self.submit(self.emma, session=old_but_just_completed).status_code, 201)

    def test_duplicate_is_per_student_not_per_submitter(self):
        self.assertEqual(self.submit(self.emma).status_code, 201)
        # Same student, same session -- by the parent this time.
        response = self.submit(self.james, student=self.emma.id)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("already submitted", str(response.data["session"]))
        # The sibling is a different student: allowed.
        self.assertEqual(self.submit(self.james, student=self.liam.id).status_code, 201)

    def test_rejects_ratings_out_of_range(self):
        for bad in (0, 6, -1):
            response = self.submit(self.emma, rating_pace=bad)
            self.assertEqual(response.status_code, 400, bad)
            self.assertIn("rating_pace", response.data)

    def test_rejects_long_note(self):
        self.assertEqual(self.submit(self.emma, note="x" * 501).status_code, 400)
        self.assertEqual(self.submit(self.emma, note="x" * 500).status_code, 201)

    def test_rejects_student_not_enrolled_in_class(self):
        response = self.submit(self.zara, session=self.session)  # Zara is only in PF
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)


class ListingTests(FeedbackFixtureMixin, TestCase):
    def test_my_feedback_for_student_is_only_their_own(self):
        self.submit(self.emma)
        self.submit(self.liam)
        response = self.client_for(self.emma).get("/api/v1/feedback/my/")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["count"], 1)
        self.assertEqual(response.data["results"][0]["student"], self.emma.id)
        self.assertEqual({"count", "page", "page_size", "results"}, set(response.data))

    def test_my_feedback_for_parent_covers_all_linked_students_newest_first(self):
        self.submit(self.emma)
        self.submit(self.liam)
        self.submit(self.anika)  # not James's child
        response = self.client_for(self.james).get("/api/v1/feedback/my/")
        students = [row["student"] for row in response.data["results"]]
        self.assertEqual(students, [self.liam.id, self.emma.id])

    def test_instructor_cannot_use_my_feedback(self):
        self.assertEqual(
            self.client_for(self.sarah).get("/api/v1/feedback/my/").status_code, 403
        )

    def test_eligible_sessions_follow_the_rules(self):
        make_session(self.ld, status_="cancelled")
        make_session(self.ld, status_="scheduled")
        make_session(self.ld, days_ago=45)
        pf_session = make_session(self.pf)
        self.submit(self.emma)  # self.session is now reviewed by Emma

        response = self.client_for(self.emma).get("/api/v1/feedback/eligible-sessions/")
        self.assertEqual([row["session"] for row in response.data["results"]], [pf_session.id])

        james = self.client_for(self.james).get("/api/v1/feedback/eligible-sessions/")
        pairs = {(row["student"], row["session"]) for row in james.data["results"]}
        self.assertEqual(
            pairs,
            {(self.emma.id, pf_session.id), (self.liam.id, self.session.id)},
        )


class WeightedAverageTests(SimpleTestCase):
    def test_weighted_average_matches_rubric_example(self):
        # 90 min @ 4.0 and 60 min @ 3.0 -> 3.6, not the simple mean 3.5
        self.assertAlmostEqual(weighted_average([(4.0, 90), (3.0, 60)]), 3.6)

    def test_no_weight_gives_none(self):
        self.assertIsNone(weighted_average([]))

    def test_compute_summary_per_dimension_and_overall(self):
        result = compute_summary(
            [
                {"duration": 90, "count": 2, "clarity": 4.0, "engagement": 5.0, "pace": 3.0},
                {"duration": 60, "count": 1, "clarity": 3.0, "engagement": 2.0, "pace": 3.0},
            ]
        )
        self.assertAlmostEqual(result["averages"]["clarity"], 3.6)
        self.assertAlmostEqual(result["averages"]["engagement"], 3.8)
        self.assertAlmostEqual(result["averages"]["pace"], 3.0)
        self.assertAlmostEqual(result["averages"]["overall"], (3.6 + 3.8 + 3.0) / 3)
        self.assertEqual(result["total_feedback_count"], 3)


class InstructorSummaryTests(FeedbackFixtureMixin, TestCase):
    URL = "/api/v1/feedback/instructor-summary/"

    def add_feedback(self, session, student, clarity, engagement=3, pace=3):
        return SessionFeedback.objects.create(
            session=session,
            student=student,
            created_by=student,
            rating_clarity=clarity,
            rating_engagement=engagement,
            rating_pace=pace,
            note="private words",
        )

    def test_weighted_not_simple_average(self):
        long_session = make_session(self.ld, days_ago=2, duration=90)
        short_session = make_session(self.ld, days_ago=1, duration=60)
        self.add_feedback(long_session, self.emma, clarity=4)
        self.add_feedback(short_session, self.emma, clarity=3)
        self.add_feedback(short_session, self.liam, clarity=3)

        data = self.client_for(self.sarah).get(self.URL).data
        self.assertEqual(data["averages"]["clarity"], 3.6)
        self.assertEqual(data["total_feedback_count"], 3)

    def test_only_last_ten_completed_sessions_count(self):
        self.session.delete()  # keep the window to exactly the sessions built here
        # Oldest session: terrible score; 10 newer sessions: perfect.
        oldest = make_session(self.ld, days_ago=100)
        self.add_feedback(oldest, self.emma, clarity=1, engagement=1, pace=1)
        for i in range(10):
            session = make_session(self.ld, days_ago=i + 1)
            self.add_feedback(session, self.emma, clarity=5, engagement=5, pace=5)

        data = self.client_for(self.sarah).get(self.URL).data
        self.assertEqual(data["averages"]["overall"], 5.0)
        self.assertEqual(data["total_feedback_count"], 10)
        self.assertEqual(data["sessions_in_window"], 10)

    def test_duration_comes_from_session_metadata(self):
        bad = make_session(self.ld, days_ago=2)
        bad.session_metadata = {"topic_covered": "no duration"}
        bad.save()
        good = make_session(self.ld, days_ago=1, duration=45)
        self.add_feedback(bad, self.emma, clarity=1)
        self.add_feedback(good, self.emma, clarity=5)
        self.add_feedback(good, self.liam, clarity=5)
        self.add_feedback(good, self.anika, clarity=5)
        data = self.client_for(self.sarah).get(self.URL).data
        self.assertEqual(data["averages"]["clarity"], 5.0)  # no default 60 min invented

    def test_response_is_anonymous(self):
        for student in (self.emma, self.liam, self.anika):
            self.add_feedback(self.session, student, clarity=4)

        raw = self.client_for(self.sarah).get(self.URL).content.decode()
        for needle in ("student", "submitter", "created_by", "note", "private words",
                       "emma", "Emma", "@cda.test"):
            self.assertNotIn(needle, raw, needle)
        keys = set(self.client_for(self.sarah).get(self.URL).data)
        self.assertEqual(
            keys,
            {
                "window_size", "sessions_in_window", "sessions_with_feedback",
                "total_feedback_count", "minimum_responses",
                "meets_anonymity_threshold", "averages",
            },
        )

    def test_averages_hidden_below_minimum_responses(self):
        self.add_feedback(self.session, self.emma, clarity=5)
        data = self.client_for(self.sarah).get(self.URL).data
        self.assertFalse(data["meets_anonymity_threshold"])
        self.assertEqual(data["total_feedback_count"], 1)
        self.assertTrue(all(v is None for v in data["averages"].values()))

    def test_each_instructor_sees_only_their_classes(self):
        pf_session = make_session(self.pf)
        self.add_feedback(pf_session, self.emma, clarity=2)
        self.add_feedback(pf_session, self.zara, clarity=2)
        for student in (self.emma, self.liam, self.anika):
            self.add_feedback(self.session, student, clarity=5)

        sarah = self.client_for(self.sarah).get(self.URL).data
        marcus = self.client_for(self.marcus).get(self.URL).data
        self.assertEqual(sarah["averages"]["clarity"], 5.0)
        self.assertEqual(sarah["total_feedback_count"], 3)
        self.assertEqual(marcus["total_feedback_count"], 2)
        self.assertFalse(marcus["meets_anonymity_threshold"])

    def test_permissions_and_admin_filter(self):
        for student in (self.emma, self.liam, self.anika):
            self.add_feedback(self.session, student, clarity=4)

        self.assertEqual(self.client_for(self.emma).get(self.URL).status_code, 403)
        self.assertEqual(self.client_for(self.james).get(self.URL).status_code, 403)
        self.assertEqual(APIClient().get(self.URL).status_code, 401)

        sarah_client = self.client_for(self.sarah)
        self.assertEqual(sarah_client.get(self.URL, {"instructor_id": self.marcus.id}).status_code, 403)
        self.assertEqual(sarah_client.get(self.URL, {"instructor_id": self.sarah.id}).status_code, 200)

        admin = self.client_for(self.admin)
        scoped = admin.get(self.URL, {"instructor_id": self.sarah.id}).data
        self.assertEqual(scoped["total_feedback_count"], 3)
        other = admin.get(self.URL, {"instructor_id": self.marcus.id}).data
        self.assertEqual(other["total_feedback_count"], 0)
        self.assertEqual(admin.get(self.URL, {"instructor_id": 99999}).status_code, 400)
        self.assertEqual(admin.get(self.URL).status_code, 200)

    def test_service_can_use_a_custom_window(self):
        for i in range(3):
            session = make_session(self.ld, days_ago=i + 1)
            self.add_feedback(session, self.emma, clarity=i + 1)
        data = InstructorSummaryService(window=1, minimum=1).summarize(self.sarah)
        self.assertEqual(data["averages"]["clarity"], 1.0)


class SessionCompletedEventTests(FeedbackFixtureMixin, TestCase):
    def complete(self, user, session):
        return self.client_for(user).post(f"/api/v1/classes/sessions/{session.id}/complete/")

    def test_completing_notifies_enrolled_students_and_their_parents_only(self):
        scheduled = make_session(self.ld, status_="scheduled")
        queues = {u.username: broker.subscribe(u.id) for u in
                  (self.emma, self.liam, self.anika, self.zara, self.james, self.priya, self.marcus)}
        self.addCleanup(lambda: [broker.unsubscribe(u.id, queues[u.username]) for u in
                        (self.emma, self.liam, self.anika, self.zara, self.james, self.priya, self.marcus)])

        response = self.complete(self.sarah, scheduled)
        self.assertEqual(response.status_code, 200)
        scheduled.refresh_from_db()
        self.assertEqual(scheduled.status, "completed")
        self.assertIn("completed_at", scheduled.session_metadata)

        for name in ("emma", "liam", "anika", "james", "priya"):
            event = queues[name].get_nowait()
            self.assertEqual(event["type"], "session_completed")
            self.assertEqual(event["session_id"], scheduled.id)
        self.assertEqual(queues["james"].qsize(), 0)
        for name in ("zara", "marcus"):  # not in the LD class
            self.assertTrue(queues[name].empty(), name)

    def test_parent_event_lists_only_their_children(self):
        scheduled = make_session(self.ld, status_="scheduled")
        q = broker.subscribe(self.james.id)
        self.addCleanup(broker.unsubscribe, self.james.id, q)
        self.complete(self.sarah, scheduled)
        self.assertCountEqual(q.get_nowait()["student_ids"], [self.emma.id, self.liam.id])

    def test_only_the_classes_instructor_or_admin_can_complete(self):
        scheduled = make_session(self.ld, status_="scheduled")
        self.assertEqual(self.complete(self.marcus, scheduled).status_code, 403)
        self.assertEqual(self.complete(self.emma, scheduled).status_code, 403)
        self.assertEqual(self.complete(self.admin, scheduled).status_code, 200)

    def test_cannot_complete_twice_or_a_cancelled_session(self):
        cancelled = make_session(self.ld, status_="cancelled")
        self.assertEqual(self.complete(self.sarah, cancelled).status_code, 400)
        self.assertEqual(self.complete(self.sarah, self.session).status_code, 400)

    def test_events_endpoint_requires_auth_and_streams(self):
        self.assertEqual(APIClient().get("/api/v1/feedback/events/").status_code, 401)
        client = self.client_for(self.emma)
        response = client.get("/api/v1/feedback/events/", HTTP_ACCEPT="text/event-stream")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response["Content-Type"], "text/event-stream")
        self.assertIn(b"retry", next(iter(response.streaming_content)))
        response.close()
