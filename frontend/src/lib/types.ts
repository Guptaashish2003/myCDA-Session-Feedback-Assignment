/**
 * File: frontend/src/lib/types.ts
 * Purpose: TypeScript types mirroring the API.
 * Contents:
 *   - User, Session, ClassItem, PaginatedResponse: starter types.
 *   - FeedbackEntry, EligibleSession, FeedbackPayload, InstructorSummary, SessionCompletedEvent,
 *     RatingKey: types added for the feedback feature.
 */
export type UserRole = "admin" | "instructor" | "parent" | "student";

export interface User {
  id: number;
  email: string;
  first_name: string;
  last_name: string;
  preferred_name: string;
  role: UserRole;
  display_name: string;
  created_at: string;
  updated_at: string;
  family_links?: FamilyLink[];
}

export interface FamilyLink {
  id: number;
  student: number;
  student_display: UserMinimal;
  relationship: string;
  created_at: string;
}

export interface UserMinimal {
  id: number;
  display_name: string;
  role: UserRole;
}

export interface ClassItem {
  id: number;
  name: string;
  description: string;
  instructor: number;
  instructor_display: UserMinimal;
  is_active: boolean;
  student_count: number;
  created_at: string;
  updated_at: string;
}

export interface Session {
  id: number;
  class_obj: number;
  class_name: string;
  instructor_display: UserMinimal;
  scheduled_date: string;
  status: "scheduled" | "completed" | "cancelled";
  duration_minutes: number;
  topic: string;
  created_at: string;
  updated_at: string;
}

export interface PaginatedResponse<T> {
  count: number;
  page: number;
  page_size: number;
  results: T[];
}

/* ---------- Session feedback ---------- */

export type RatingKey = "clarity" | "engagement" | "pace";

/** Ratings keyed the way the API sends/receives them (`rating_clarity`, ...). */
export type RatingFields = { [K in RatingKey as `rating_${K}`]: number };

export interface FeedbackEntry extends RatingFields {
  id: number;
  session: number;
  class_name: string;
  session_date: string;
  topic: string;
  student: number;
  student_display: UserMinimal;
  note: string;
  created_by_display: string | null;
  created_at: string;
  /** Client-only: true while an optimistic submission is still in flight. */
  pending?: boolean;
}

export interface EligibleSession {
  session: number;
  class_name: string;
  scheduled_date: string;
  topic: string;
  duration_minutes: number;
  student: number;
  student_display: UserMinimal;
}

export interface FeedbackPayload extends RatingFields {
  session: number;
  student?: number;
  note?: string;
}

export interface InstructorSummary {
  window_size: number;
  sessions_in_window: number;
  sessions_with_feedback: number;
  total_feedback_count: number;
  minimum_responses: number;
  meets_anonymity_threshold: boolean;
  averages: Record<RatingKey | "overall", number | null>;
}

export interface SessionCompletedEvent {
  type: "session_completed";
  session_id: number;
  class_name: string;
  student_ids: number[];
  message: string;
}
