/**
 * File: frontend/src/components/feedback/CompleteSessionsCard.tsx
 * Purpose: Instructor tool for closing out sessions.
 * Contents:
 *   - CompleteSessionsCard: lists the instructor's scheduled sessions (classes then sessions) and
 *     posts to /classes/sessions/<id>/complete/, which notifies students and parents in real time.
 */
"use client";

import { useCallback, useEffect, useState } from "react";
import { toast } from "sonner";
import { Button } from "@/components/ui/button";
import CardStatus from "@/components/CardStatus";
import DashboardCard from "@/components/DashboardCard";
import { api } from "@/lib/api";
import { apiErrorMessages, formatDate } from "@/lib/feedback";
import type { ClassItem, PaginatedResponse, Session } from "@/lib/types";

/**
 * Instructor tool: mark a session completed. The backend then pushes a
 * server-sent event to the enrolled students and their parents so the
 * feedback form opens for them straight away.
 */
export default function CompleteSessionsCard() {
  const [sessions, setSessions] = useState<Session[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [completing, setCompleting] = useState<number | null>(null);

  const load = useCallback(async () => {
    try {
      const classes = await api.get<PaginatedResponse<ClassItem>>("/classes/?page_size=100");
      const perClass = await Promise.all(
        classes.results.map((cls) =>
          api.get<PaginatedResponse<Session>>(`/classes/${cls.id}/sessions/?page_size=100`)
        )
      );
      setSessions(
        perClass
          .flatMap((page) => page.results)
          .filter((session) => session.status === "scheduled")
          .sort((a, b) => a.scheduled_date.localeCompare(b.scheduled_date))
      );
    } catch {
      setError("Could not load your sessions.");
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    load();
  }, [load]);

  async function complete(session: Session) {
    setCompleting(session.id);
    try {
      await api.post(`/classes/sessions/${session.id}/complete/`);
      setSessions((prev) => prev.filter((item) => item.id !== session.id));
      toast.success(`${session.class_name} marked completed. Students and parents were notified.`);
    } catch (e) {
      toast.error(apiErrorMessages(e)[0]);
    } finally {
      setCompleting(null);
    }
  }

  return (
    <DashboardCard
      title="Close Out Sessions"
      subtitle="Marking a session completed opens feedback for its students"
      flush
    >
      <div className={loading || error || sessions.length === 0 ? "px-5 py-4" : ""}>
        <CardStatus
          loading={loading}
          error={error}
          empty={sessions.length === 0}
          emptyMessage="No scheduled sessions to complete."
        >
          <ul className="divide-y divide-gray-100">
            {sessions.map((session) => (
              <li key={session.id} className="flex items-center justify-between gap-3 px-5 py-3">
                <div>
                  <p className="text-sm font-medium text-gray-900">{session.class_name}</p>
                  <p className="text-xs text-gray-500">
                    {formatDate(session.scheduled_date)}
                    {session.topic ? ` · ${session.topic}` : ""}
                  </p>
                </div>
                <Button
                  size="sm"
                  variant="outline"
                  disabled={completing === session.id}
                  onClick={() => complete(session)}
                >
                  Mark completed
                </Button>
              </li>
            ))}
          </ul>
        </CardStatus>
      </div>
    </DashboardCard>
  );
}
