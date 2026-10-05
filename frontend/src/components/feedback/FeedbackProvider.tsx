"use client";

import { createContext, useCallback, useContext, useMemo, ReactNode } from "react";
import { toast } from "sonner";
import { api } from "@/lib/api";
import { useAuth } from "@/contexts/AuthContext";
import { useApiResource } from "@/hooks/useApiResource";
import { useServerEvents } from "@/hooks/useServerEvents";
import type {
  EligibleSession,
  FeedbackEntry,
  FeedbackPayload,
  PaginatedResponse,
  SessionCompletedEvent,
  User,
  UserMinimal,
} from "@/lib/types";

interface FeedbackState {
  /** Students the current user can submit for (themselves, or a parent's children). */
  students: UserMinimal[];
  eligible: EligibleSession[];
  history: FeedbackEntry[];
  loading: boolean;
  error: string;
  /**
   * Optimistic submit: the entry shows up in `history` (and leaves `eligible`)
   * immediately, and is rolled back if the server rejects it. Rejects with the
   * original error so the form can show server validation messages.
   */
  submit: (payload: FeedbackPayload, target: EligibleSession) => Promise<void>;
}

const FeedbackContext = createContext<FeedbackState | undefined>(undefined);

const byDateDesc = (a: EligibleSession, b: EligibleSession) =>
  b.scheduled_date.localeCompare(a.scheduled_date);

/**
 * Owns the student/parent feedback data (eligible sessions + history) so the
 * submission form and the history card stay in sync without prop drilling.
 */
export function FeedbackProvider({ children }: { children: ReactNode }) {
  const { user } = useAuth();
  const isParent = user?.role === "parent";

  const eligibleRes = useApiResource<PaginatedResponse<EligibleSession>>(
    "/feedback/eligible-sessions/?page_size=100",
    "Could not load sessions awaiting feedback."
  );
  const historyRes = useApiResource<PaginatedResponse<FeedbackEntry>>(
    "/feedback/my/?page_size=100",
    "Could not load your feedback history."
  );
  // Parents' links are only on the profile endpoint, not on the login response.
  const profileRes = useApiResource<User>(isParent ? "/accounts/profile/" : null);

  const students = useMemo<UserMinimal[]>(() => {
    if (!user) return [];
    if (!isParent) return [{ id: user.id, display_name: user.display_name, role: user.role }];
    return (profileRes.data?.family_links ?? []).map((link) => link.student_display);
  }, [user, isParent, profileRes.data]);

  const { setData: setEligible, reload: reloadEligible } = eligibleRes;
  const { setData: setHistory } = historyRes;

  useServerEvents<SessionCompletedEvent>("/feedback/events/", (event) => {
    toast.info(event.message);
    reloadEligible(true);
  });

  const submit = useCallback(
    async (payload: FeedbackPayload, target: EligibleSession) => {
      const tempId = -Date.now();
      const optimistic: FeedbackEntry = {
        id: tempId,
        session: target.session,
        class_name: target.class_name,
        session_date: target.scheduled_date,
        topic: target.topic,
        student: target.student,
        student_display: target.student_display,
        rating_clarity: payload.rating_clarity,
        rating_engagement: payload.rating_engagement,
        rating_pace: payload.rating_pace,
        note: payload.note ?? "",
        created_by_display: user?.display_name ?? null,
        created_at: new Date().toISOString(),
        pending: true,
      };

      const isTarget = (item: EligibleSession) =>
        item.session === target.session && item.student === target.student;

      setEligible((prev) =>
        prev ? { ...prev, results: prev.results.filter((item) => !isTarget(item)) } : prev
      );
      setHistory((prev) =>
        prev ? { ...prev, results: [optimistic, ...prev.results] } : prev
      );

      try {
        const saved = await api.post<FeedbackEntry>("/feedback/", payload);
        setHistory((prev) =>
          prev
            ? { ...prev, results: prev.results.map((e) => (e.id === tempId ? saved : e)) }
            : prev
        );
      } catch (error) {
        setHistory((prev) =>
          prev ? { ...prev, results: prev.results.filter((e) => e.id !== tempId) } : prev
        );
        setEligible((prev) =>
          prev
            ? { ...prev, results: [...prev.results, target].sort(byDateDesc) }
            : prev
        );
        throw error;
      }
    },
    [user, setEligible, setHistory]
  );

  const value: FeedbackState = {
    students,
    eligible: eligibleRes.data?.results ?? [],
    history: historyRes.data?.results ?? [],
    loading: eligibleRes.loading || historyRes.loading || (isParent && profileRes.loading),
    error: eligibleRes.error || historyRes.error,
    submit,
  };

  return <FeedbackContext.Provider value={value}>{children}</FeedbackContext.Provider>;
}

export function useFeedback() {
  const ctx = useContext(FeedbackContext);
  if (!ctx) throw new Error("useFeedback must be used within FeedbackProvider");
  return ctx;
}
