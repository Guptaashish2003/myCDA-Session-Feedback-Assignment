import queue

from django.http import StreamingHttpResponse
from rest_framework import generics, status
from rest_framework.negotiation import DefaultContentNegotiation
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from accounts.models import User
from core.permissions import IsInstructorOrAdmin, IsStudentOrParent

from . import selectors
from .notifications import broker, format_sse
from .serializers import (
    EligibleSessionSerializer,
    FeedbackCreateSerializer,
    FeedbackSerializer,
    InstructorSummarySerializer,
)
from .summary import InstructorSummaryService

HEARTBEAT_SECONDS = 15


class FeedbackCreateView(generics.CreateAPIView):
    """POST: submit feedback as the student, or as a parent for a linked student."""

    serializer_class = FeedbackCreateSerializer
    permission_classes = [IsStudentOrParent]

    def perform_create(self, serializer):
        # The submitter always comes from the authenticated user, never the body.
        serializer.save(created_by=self.request.user)

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        self.perform_create(serializer)
        return Response(
            FeedbackSerializer(serializer.instance, context={"request": request}).data,
            status=status.HTTP_201_CREATED,
        )


class MyFeedbackListView(generics.ListAPIView):
    """GET: feedback for the current student, or for all of a parent's linked students."""

    serializer_class = FeedbackSerializer
    permission_classes = [IsStudentOrParent]

    def get_queryset(self):
        return selectors.feedback_visible_to(self.request.user)


class EligibleSessionListView(generics.ListAPIView):
    """GET: (student, session) pairs that can still be reviewed."""

    serializer_class = EligibleSessionSerializer
    permission_classes = [IsStudentOrParent]

    def get_queryset(self):
        return [
            {"student": student, "session": session}
            for student, session in selectors.eligible_session_pairs(self.request.user)
        ]


class InstructorSummaryView(APIView):
    """
    GET: anonymized weighted rolling average for the requesting instructor.
    Admins may pass ?instructor_id=X (omit it for all instructors).
    """

    permission_classes = [IsInstructorOrAdmin]

    def get(self, request):
        instructor = None
        raw_id = request.query_params.get("instructor_id")

        if request.user.role == User.Role.INSTRUCTOR:
            if raw_id not in (None, "", str(request.user.id)):
                return Response(
                    {"detail": "Instructors can only view their own summary."},
                    status=status.HTTP_403_FORBIDDEN,
                )
            instructor = request.user
        elif raw_id:
            try:
                instructor = User.objects.get(pk=int(raw_id), role=User.Role.INSTRUCTOR)
            except (ValueError, User.DoesNotExist):
                return Response(
                    {"instructor_id": "No instructor with this id."},
                    status=status.HTTP_400_BAD_REQUEST,
                )

        summary = InstructorSummaryService().summarize(instructor)
        return Response(InstructorSummarySerializer(summary).data)


class AnyAcceptContentNegotiation(DefaultContentNegotiation):
    """EventSource-style clients send `Accept: text/event-stream`, which no
    DRF renderer handles; the stream is built by hand, so skip negotiation."""

    def select_renderer(self, request, renderers, format_suffix=None):
        return renderers[0], renderers[0].media_type


class FeedbackEventsView(APIView):
    """
    GET: Server-Sent Events stream for the logged-in user. Emits a
    `session_completed` event when a class of theirs (or their child's) is
    marked completed, so the UI can offer the feedback form straight away.
    """

    permission_classes = [IsAuthenticated]
    content_negotiation_class = AnyAcceptContentNegotiation

    def get(self, request):
        user_id = request.user.id
        subscription = broker.subscribe(user_id)

        def stream():
            try:
                yield "retry: 3000\n\n: connected\n\n"
                while True:
                    try:
                        yield format_sse(subscription.get(timeout=HEARTBEAT_SECONDS))
                    except queue.Empty:
                        yield ": ping\n\n"
            finally:
                broker.unsubscribe(user_id, subscription)

        response = StreamingHttpResponse(stream(), content_type="text/event-stream")
        response["Cache-Control"] = "no-cache"
        response["X-Accel-Buffering"] = "no"
        return response
