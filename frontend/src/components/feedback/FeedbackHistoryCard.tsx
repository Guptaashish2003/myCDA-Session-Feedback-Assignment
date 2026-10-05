/**
 * File: frontend/src/components/feedback/FeedbackHistoryCard.tsx
 * Purpose: Previously submitted feedback.
 * Contents:
 *   - FeedbackEntryItem: class, date, three read-only star rows, note and a 'Sending...' badge for
 *     optimistic entries.
 *   - FeedbackHistoryCard: flat list for students, grouped by student for parents.
 */
"use client";

import { Badge } from "@/components/ui/badge";
import CardStatus from "@/components/CardStatus";
import DashboardCard from "@/components/DashboardCard";
import { useAuth } from "@/contexts/AuthContext";
import { formatDate, fromRatingFields, groupBy } from "@/lib/feedback";
import type { FeedbackEntry } from "@/lib/types";
import DimensionRatings from "./DimensionRatings";
import { useFeedback } from "./FeedbackProvider";

function FeedbackEntryItem({ entry }: { entry: FeedbackEntry }) {
  return (
    <li className="space-y-2 px-5 py-3">
      <div className="flex items-start justify-between gap-2">
        <div>
          <p className="text-sm font-medium text-gray-900">{entry.class_name}</p>
          <p className="text-xs text-gray-500">{formatDate(entry.session_date)}</p>
        </div>
        {entry.pending && <Badge variant="secondary">Sending…</Badge>}
      </div>
      <DimensionRatings values={fromRatingFields(entry)} size="sm" />
      {entry.note && <p className="text-sm italic text-gray-600">&ldquo;{entry.note}&rdquo;</p>}
    </li>
  );
}

export default function FeedbackHistoryCard() {
  const { user } = useAuth();
  const { history, loading, error } = useFeedback();
  const isParent = user?.role === "parent";

  // Parents see one group per linked student; students see a single flat list.
  const groups = isParent
    ? Array.from(groupBy(history, (entry) => entry.student).values())
    : history.length > 0
      ? [history]
      : [];

  return (
    <DashboardCard
      title="My Feedback"
      subtitle={history.length > 0 ? `${history.length} submitted` : undefined}
      flush
    >
      <div className={loading || error || history.length === 0 ? "px-5 py-4" : ""}>
        <CardStatus
          loading={loading}
          error={error}
          empty={history.length === 0}
          emptyMessage="You haven't submitted any feedback yet."
        >
          {groups.map((entries) => (
            <section key={entries[0].student}>
              {isParent && (
                <h4 className="border-b border-gray-100 bg-gray-50 px-5 py-1.5 text-xs font-semibold uppercase tracking-wide text-gray-500">
                  {entries[0].student_display.display_name}
                </h4>
              )}
              <ul className="divide-y divide-gray-100">
                {entries.map((entry) => (
                  <FeedbackEntryItem key={entry.id} entry={entry} />
                ))}
              </ul>
            </section>
          ))}
        </CardStatus>
      </div>
    </DashboardCard>
  );
}
