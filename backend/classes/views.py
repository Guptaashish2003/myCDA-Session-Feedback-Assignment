# File: backend/classes/views.py
# Purpose: Class and session endpoints.
# Contents:
#   - ClassListView: classes visible to the user: own (instructor), enrolled (student), children's
#     (parent) or all (admin).
#   - SessionListView / MyEnrollmentsView: sessions of a class; enrolments scoped by role.
#   - CompleteSessionView (POST): instructor of the class (or admin) marks a session completed via
#     services.complete_session; 403 for other instructors, 400 if the session is not scheduled.

from django.shortcuts import get_object_or_404
from rest_framework import generics, status
from rest_framework.exceptions import PermissionDenied
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from core.permissions import IsStudentOrParent, IsInstructorOrAdmin
from accounts.models import FamilyLink
from .models import Class, Session, ClassEnrollment
from .serializers import ClassSerializer, SessionSerializer, EnrollmentSerializer
from .services import SessionNotCompletable, complete_session


class ClassListView(generics.ListAPIView):
    """List classes relevant to the current user."""

    serializer_class = ClassSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        user = self.request.user
        if user.role == "instructor":
            return Class.objects.filter(
                instructor=user, is_active=True
            ).prefetch_related("enrollments")
        elif user.role == "student":
            return Class.objects.filter(
                enrollments__student=user,
                enrollments__is_active=True,
                is_active=True,
            ).prefetch_related("enrollments")
        elif user.role == "parent":
            children = FamilyLink.objects.filter(
                parent=user
            ).values_list("student_id", flat=True)
            return Class.objects.filter(
                enrollments__student__in=children,
                enrollments__is_active=True,
                is_active=True,
            ).distinct().prefetch_related("enrollments")
        else:
            # Admin sees all
            return Class.objects.filter(
                is_active=True
            ).prefetch_related("enrollments")


class SessionListView(generics.ListAPIView):
    """List sessions for a specific class."""

    serializer_class = SessionSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        class_id = self.kwargs.get("class_id")
        return Session.objects.filter(
            class_obj_id=class_id
        ).select_related("class_obj", "class_obj__instructor")


class MyEnrollmentsView(generics.ListAPIView):
    """List the current student's (or parent's children's) enrollments."""

    serializer_class = EnrollmentSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        user = self.request.user
        if user.role == "student":
            return ClassEnrollment.objects.filter(
                student=user, is_active=True
            ).select_related("class_obj", "class_obj__instructor", "student")
        elif user.role == "parent":
            children = FamilyLink.objects.filter(
                parent=user
            ).values_list("student_id", flat=True)
            return ClassEnrollment.objects.filter(
                student__in=children, is_active=True
            ).select_related("class_obj", "class_obj__instructor", "student")
        elif user.role in ("instructor", "admin"):
            return ClassEnrollment.objects.filter(
                is_active=True
            ).select_related("class_obj", "class_obj__instructor", "student")
        return ClassEnrollment.objects.none()


class CompleteSessionView(APIView):
    """
    POST: the session's instructor (or an admin) marks it completed.
    Emits the `session_completed` signal, which downstream apps use to
    notify the enrolled students and their parents.
    """

    permission_classes = [IsInstructorOrAdmin]

    def post(self, request, session_id):
        session = get_object_or_404(
            Session.objects.select_related("class_obj", "class_obj__instructor"),
            pk=session_id,
        )
        if (
            request.user.role != "admin"
            and session.class_obj.instructor_id != request.user.id
        ):
            raise PermissionDenied("You can only complete sessions of your own classes.")

        try:
            complete_session(session)
        except SessionNotCompletable as exc:
            return Response({"detail": str(exc)}, status=status.HTTP_400_BAD_REQUEST)

        return Response(SessionSerializer(session).data, status=status.HTTP_200_OK)
