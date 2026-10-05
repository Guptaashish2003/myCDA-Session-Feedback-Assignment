"use client";

import { useAuth } from "@/contexts/AuthContext";
import ActiveClassesCard from "@/components/ActiveClassesCard";
import ProfileCard from "@/components/ProfileCard";
import { FeedbackProvider } from "@/components/feedback/FeedbackProvider";
import SubmitFeedbackCard from "@/components/feedback/SubmitFeedbackCard";
import FeedbackHistoryCard from "@/components/feedback/FeedbackHistoryCard";
import InstructorSummaryCard from "@/components/feedback/InstructorSummaryCard";
import CompleteSessionsCard from "@/components/feedback/CompleteSessionsCard";

/**
 * myCDA Dashboard
 *
 * Cards are rendered based on the user's role.
 * Add your feedback-related cards below, following the same pattern.
 */
export default function DashboardPage() {
  const { user } = useAuth();

  if (!user) return null;

  return (
    <div>
      <h1 className="mb-1 text-xl font-semibold text-gray-900">Dashboard</h1>
      <p className="mb-6 text-sm text-gray-500">
        Welcome back, {user.display_name}
      </p>

      <div className="grid gap-6 lg:grid-cols-2">
        {/* Visible to everyone */}
        <ActiveClassesCard />
        <ProfileCard />

        {/* Students & parents: submit feedback + see what was submitted */}
        {(user.role === "student" || user.role === "parent") && (
          <FeedbackProvider>
            <SubmitFeedbackCard />
            <FeedbackHistoryCard />
          </FeedbackProvider>
        )}

        {/* Instructors & admins: anonymized summary + closing out sessions */}
        {(user.role === "instructor" || user.role === "admin") && (
          <>
            <InstructorSummaryCard />
            <CompleteSessionsCard />
          </>
        )}
      </div>
    </div>
  );
}
