"use client";

import { ShieldCheck } from "lucide-react";
import CardStatus from "@/components/CardStatus";
import DashboardCard from "@/components/DashboardCard";
import { StarRating } from "@/components/ui/star-rating";
import { useApiResource } from "@/hooks/useApiResource";
import type { InstructorSummary } from "@/lib/types";
import DimensionRatings from "./DimensionRatings";

export default function InstructorSummaryCard() {
  const { data, loading, error } = useApiResource<InstructorSummary>(
    "/feedback/instructor-summary/",
    "Could not load the feedback summary."
  );

  const averages = data?.averages;
  const overall = averages?.overall ?? null;

  return (
    <DashboardCard
      title="Session Feedback Summary"
      subtitle={
        data ? `Weighted average of your last ${data.window_size} completed sessions` : undefined
      }
    >
      <CardStatus
        loading={loading}
        error={error}
        empty={data?.total_feedback_count === 0}
        emptyMessage="No feedback has been submitted for your recent sessions yet."
      >
        {data && averages && (
          <div className="space-y-4">
            {!data.meets_anonymity_threshold ? (
              <p className="text-sm text-gray-600">
                {data.total_feedback_count} of {data.minimum_responses} reviews needed. Scores
                appear once enough reviews exist, so no single student can be identified.
              </p>
            ) : (
              <>
                <div className="flex items-center gap-4">
                  <span className="text-4xl font-semibold tabular-nums text-cda-navy">
                    {overall?.toFixed(1)}
                  </span>
                  <div>
                    <StarRating value={overall ?? 0} size="md" label="Overall" />
                    <p className="text-xs text-gray-500">Overall (out of 5)</p>
                  </div>
                </div>
                <DimensionRatings values={averages} showValue showBar />
              </>
            )}

            <p className="text-xs text-gray-500">
              {data.total_feedback_count} review{data.total_feedback_count !== 1 ? "s" : ""}{" "}
              across {data.sessions_with_feedback} session
              {data.sessions_with_feedback !== 1 ? "s" : ""}, weighted by session length.
            </p>

            <p className="flex items-start gap-1.5 rounded-md bg-gray-50 px-3 py-2 text-xs text-gray-600">
              <ShieldCheck className="mt-0.5 h-3.5 w-3.5 shrink-0 text-cda-mint" />
              Aggregated, anonymized scores. Individual reviews, notes and student or parent
              identities are never shown to instructors.
            </p>
          </div>
        )}
      </CardStatus>
    </DashboardCard>
  );
}
