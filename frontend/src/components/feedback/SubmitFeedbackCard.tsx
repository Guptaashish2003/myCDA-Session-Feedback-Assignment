/**
 * File: frontend/src/components/feedback/SubmitFeedbackCard.tsx
 * Purpose: Feedback submission form.
 * Contents:
 *   - SubmitFeedbackCard: parent student dropdown, session dropdown (only eligible sessions),
 *     three star rows, note with 500-character counter; submit is disabled until complete; clears
 *     optimistically and restores values plus server error messages on failure.
 */
"use client";

import { FormEvent, useState } from "react";
import { toast } from "sonner";
import { Alert, AlertDescription } from "@/components/ui/alert";
import { Button } from "@/components/ui/button";
import { Label } from "@/components/ui/label";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { Textarea } from "@/components/ui/textarea";
import CardStatus from "@/components/CardStatus";
import DashboardCard from "@/components/DashboardCard";
import {
  apiErrorMessages,
  emptyRatings,
  formatDate,
  NOTE_MAX_LENGTH,
  toRatingFields,
} from "@/lib/feedback";
import { useAuth } from "@/contexts/AuthContext";
import type { RatingKey } from "@/lib/types";
import DimensionRatings from "./DimensionRatings";
import { useFeedback } from "./FeedbackProvider";

export default function SubmitFeedbackCard() {
  const { user } = useAuth();
  const { students, eligible, loading, error, submit } = useFeedback();
  const isParent = user?.role === "parent";

  const [studentId, setStudentId] = useState<number | null>(null);
  const [sessionId, setSessionId] = useState<number | null>(null);
  const [ratings, setRatings] = useState(emptyRatings());
  const [note, setNote] = useState("");
  const [errors, setErrors] = useState<string[]>([]);

  const activeStudentId = studentId ?? students[0]?.id ?? null;
  const options = eligible.filter((item) => item.student === activeStudentId);
  const target = options.find((item) => item.session === sessionId);
  const complete = Boolean(target) && Object.values(ratings).every((value) => value > 0);

  const setRating = (key: RatingKey, value: number) =>
    setRatings((prev) => ({ ...prev, [key]: value }));

  async function onSubmit(event: FormEvent) {
    event.preventDefault();
    if (!target) return;

    const snapshot = { sessionId, ratings, note };
    setErrors([]);
    // Optimistic: clear the form now; the provider rolls the lists back on failure.
    setSessionId(null);
    setRatings(emptyRatings());
    setNote("");

    try {
      await submit(
        {
          session: target.session,
          ...(isParent ? { student: target.student } : {}),
          ...toRatingFields(snapshot.ratings),
          note: snapshot.note.trim(),
        },
        target
      );
      toast.success(`Feedback submitted for ${target.class_name}.`);
    } catch (e) {
      setSessionId(snapshot.sessionId);
      setRatings(snapshot.ratings);
      setNote(snapshot.note);
      setErrors(apiErrorMessages(e));
    }
  }

  return (
    <DashboardCard
      title="Leave Session Feedback"
      subtitle="Completed sessions from the last 30 days"
    >
      <CardStatus
        loading={loading}
        error={error}
        empty={students.length > 0 && eligible.length === 0}
        emptyMessage="You're all caught up — no sessions are waiting for feedback."
      >
        <form onSubmit={onSubmit} className="space-y-4">
          {isParent && (
            <div className="space-y-1.5">
              <Label htmlFor="feedback-student">Feedback for</Label>
              <Select
                value={activeStudentId?.toString() ?? ""}
                onValueChange={(value) => {
                  setStudentId(Number(value));
                  setSessionId(null);
                }}
              >
                <SelectTrigger id="feedback-student">
                  <SelectValue placeholder="Select a student" />
                </SelectTrigger>
                <SelectContent>
                  {students.map((student) => (
                    <SelectItem key={student.id} value={student.id.toString()}>
                      {student.display_name}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>
          )}

          <div className="space-y-1.5">
            <Label htmlFor="feedback-session">Session</Label>
            <Select
              value={sessionId?.toString() ?? ""}
              onValueChange={(value) => setSessionId(Number(value))}
              disabled={options.length === 0}
            >
              <SelectTrigger id="feedback-session">
                <SelectValue
                  placeholder={
                    options.length === 0 ? "No sessions awaiting feedback" : "Select a session"
                  }
                />
              </SelectTrigger>
              <SelectContent>
                {options.map((item) => (
                  <SelectItem key={item.session} value={item.session.toString()}>
                    {item.class_name} · {formatDate(item.scheduled_date)}
                    {item.topic ? ` · ${item.topic}` : ""}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
          </div>

          <DimensionRatings values={ratings} onChange={setRating} size="lg" showHints />

          <div className="space-y-1.5">
            <Label htmlFor="feedback-note">Note (optional)</Label>
            <Textarea
              id="feedback-note"
              value={note}
              maxLength={NOTE_MAX_LENGTH}
              onChange={(e) => setNote(e.target.value)}
              placeholder="Anything else you'd like to share?"
              rows={3}
            />
            <p className="text-right text-xs text-gray-500">
              {note.length}/{NOTE_MAX_LENGTH}
            </p>
          </div>

          {errors.length > 0 && (
            <Alert variant="destructive">
              <AlertDescription>
                {errors.map((message) => (
                  <p key={message}>{message}</p>
                ))}
              </AlertDescription>
            </Alert>
          )}

          <Button type="submit" disabled={!complete} className="w-full">
            Submit feedback
          </Button>
        </form>
      </CardStatus>
    </DashboardCard>
  );
}
