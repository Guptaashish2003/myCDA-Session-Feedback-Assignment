/**
 * File: frontend/src/lib/feedback.ts
 * Purpose: Single source of truth for feedback constants and helpers (DRY).
 * Contents:
 *   - RATING_DIMENSIONS, MAX_RATING, NOTE_MAX_LENGTH: the three dimensions with labels/hints and
 *     the limits.
 *   - toRatingFields / fromRatingFields / emptyRatings: convert between {clarity} and the API's
 *     {rating_clarity}.
 *   - formatDate / groupBy: date formatting and grouping (parent history by student).
 *   - apiErrorMessages(error): flattens a DRF error body into displayable strings.
 */
import { ApiError } from "./api";
import type { RatingFields, RatingKey } from "./types";

/** Single source of truth for the three rating dimensions (form, history, summary). */
export const RATING_DIMENSIONS: { key: RatingKey; label: string; hint: string }[] = [
  { key: "clarity", label: "Clarity", hint: "How clearly concepts were explained" },
  { key: "engagement", label: "Engagement", hint: "How engaging the session was" },
  { key: "pace", label: "Pace", hint: "Whether the pacing felt right" },
];

export const MAX_RATING = 5;
export const NOTE_MAX_LENGTH = 500;

export const ratingField = (key: RatingKey) => `rating_${key}` as const;

export const emptyRatings = (): Record<RatingKey, number> => ({
  clarity: 0,
  engagement: 0,
  pace: 0,
});

/** Convert `{clarity: 4}` into the API's `{rating_clarity: 4}`. */
export function toRatingFields(values: Record<RatingKey, number>): RatingFields {
  return {
    rating_clarity: values.clarity,
    rating_engagement: values.engagement,
    rating_pace: values.pace,
  };
}

export function fromRatingFields(entry: RatingFields): Record<RatingKey, number> {
  return {
    clarity: entry.rating_clarity,
    engagement: entry.rating_engagement,
    pace: entry.rating_pace,
  };
}

export const formatDate = (iso: string) =>
  new Date(iso).toLocaleDateString(undefined, {
    month: "short",
    day: "numeric",
    year: "numeric",
  });

export function groupBy<T, K extends string | number>(items: T[], keyOf: (item: T) => K) {
  const groups = new Map<K, T[]>();
  for (const item of items) {
    const key = keyOf(item);
    groups.set(key, [...(groups.get(key) ?? []), item]);
  }
  return groups;
}

/**
 * Flatten a DRF error body ({field: ["msg"]} or {detail: "msg"}) into
 * displayable messages. Falls back to a generic message for anything else.
 */
export function apiErrorMessages(error: unknown): string[] {
  if (!(error instanceof ApiError)) return ["Something went wrong. Please try again."];
  const messages = Object.values(error.body).flatMap((value) =>
    Array.isArray(value) ? value.map(String) : [String(value)]
  );
  return messages.length > 0 ? messages : [`Request failed (${error.status}).`];
}
