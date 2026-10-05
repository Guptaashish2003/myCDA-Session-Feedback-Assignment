# Design Decisions -- Session Feedback

## Data model

`feedback.SessionFeedback` has FKs to `Session` and to two users, three separate rating columns, an optional note (max 500) and timestamps.

- **`student` vs `created_by` (the submitter).** They are different people when a parent submits, so they are separate FKs. `created_by` is the submitter; `submitter` is a read-only property alias. I used the name `created_by` because that is the project's audit-field convention that `BaseModelSerializer` is built around.
- **Uniqueness is `(session, student)`, not `(session, submitter)`.** The review belongs to the *student's* experience of the session. If uniqueness were on the submitter, Emma and her parent could each submit for the same session and the instructor would count Emma twice. A sibling is a different student, so James can still review the same session for Liam.
- **Three rating columns, not one score.** The instructor summary averages each dimension independently, so they must be queryable independently.
- **Ratings are validated twice:** model validators (`1..5`, used by DRF) and DB `CheckConstraint`s (so nothing bypasses them via the ORM or admin).
- The feedback app only references `Session`; `classes` knows nothing about feedback (see "Events").

## Backend structure (SOLID)

| File | Single responsibility |
|---|---|
| `policies.py` | The submission rules. Each rule is a tiny class with `check(ctx)`; `FeedbackSubmissionPolicy` runs a list of them. Adding a rule = adding a class (open/closed); the serializer depends on the policy abstraction, and tests can inject their own rules. |
| `selectors.py` | Read-side queries: "which students does this user represent", "what can they see", "which sessions are eligible", "who should be notified". |
| `summary.py` | Instructor aggregation. The maths (`weighted_average`, `compute_summary`) is pure -- no ORM -- and `InstructorSummaryService` only feeds it. |
| `notifications.py` / `receivers.py` | SSE broker and the signal handler that publishes to it. |
| `serializers.py` | Validation + representation only. Views stay thin. |

Conventions kept: serializers extend `BaseModelSerializer` / `ReadOnlyBaseSerializer`; permissions use the `core.permissions` classes (`IsStudentOrParent`, `IsInstructorOrAdmin`); lists use the project `StandardPagination` response shape; routes live under `/api/v1/feedback/`.

**Finding in `core`:** `BaseModelSerializer.create()` fills `created_by` from `core.middleware.get_current_user()`, but with token auth that returns `AnonymousUser` -- the middleware captures Django's session-based `request.user` *before* DRF's `TokenAuthentication` runs (I verified this against a running server). Relying on it would silently store `created_by=NULL`. So the view passes `serializer.save(created_by=request.user)`; the base class respects an explicitly provided `created_by`. `created_by` is not a writable serializer field, so a body value is ignored. I left `core` untouched, but the middleware should be fixed (e.g. store the request and read `request.user` lazily).

## Server-side validation

All in `policies.py`, run from `FeedbackCreateSerializer.validate()`:

1. actor is the student themselves, or a parent linked by `FamilyLink` -> otherwise **403**
2. student is actively enrolled in the session's class
3. session `status == completed`
4. completed within 30 days (`FEEDBACK_WINDOW_DAYS`)
5. no existing feedback for `(session, student)` -> friendly "already submitted" message; the DB unique constraint is a backstop and `IntegrityError` (a race) is mapped to the same message.

A parent must send `student`; a student may omit it (defaults to self). Ratings and note length use standard field validation. The DRF auto `UniqueTogetherValidator` is disabled because it would make `student` required.

**"Completed N days ago".** `Session` has no completion timestamp. `complete_session()` records `completed_at` in `session_metadata` (the documented place for variable session data, so no change to `classes`' schema); sessions without it (seed data) fall back to `scheduled_date`.

## Anonymization

Enforced at the API layer, not the UI:

- `GET /instructor-summary/` uses `InstructorSummarySerializer`, a plain `Serializer` with **no model behind it** and an explicit whitelist of aggregate numbers. There is no student, submitter or note field that could leak, now or if the model grows. It is a separate endpoint and serializer from the student-facing list.
- `InstructorSummaryService` only runs `values("session_id").annotate(Avg, Count)` -- it never selects identifying columns.
- **No per-session breakdown** is returned (it would identify the student in a one-student session/class).
- **Minimum-response threshold** (`FEEDBACK_SUMMARY_MIN_RESPONSES`, default 3): below it, the averages are `null` and only the count is returned, because an "average" of one review *is* that student's review. This is a deliberate choice that makes small demos look empty until 3 reviews exist.
- A test asserts the exact response key set and that no name, email, `student`, `note` or note text appears in the raw response.

## Weighted rolling average

1. Take the instructor's **last 10 completed sessions** (`ORDER BY scheduled_date DESC LIMIT 10`).
2. One aggregate query gives, per session, the review count and the average of each dimension.
3. Weight each session's average by `session_metadata["duration_minutes"]`: `sum(duration_i * avg_i) / sum(duration_i)`, per dimension. Overall is the same formula over each session's mean of the three dimensions.
4. Total feedback count = reviews in those sessions.

Example: 90 min @ 4.0 and 60 min @ 3.0 -> `(360 + 180) / 150 = 3.6` (not 3.5). Covered by a unit test.

Decisions: the window is the last 10 *completed* sessions, so sessions with no reviews take a slot but add no weight. Duration is read directly from the metadata -- a session without a valid duration is excluded rather than assigned a made-up default (`Session.duration_minutes` silently returns 60, which I deliberately avoid here). An admin without `?instructor_id` gets all instructors combined; an instructor asking for someone else gets 403.

## Events (server-sent events)

When an instructor marks a session completed (`POST /classes/sessions/<id>/complete/`), `classes.services.complete_session` sends a `session_completed` Django signal. The feedback app listens and publishes to an in-process broker; `GET /feedback/events/` streams the events to each logged-in user. Recipients are the class's enrolled students and their linked parents (a parent's event lists only their own children). `classes` never imports `feedback` (dependency inversion), so the feedback data and logic stay independent of the classes app.

## Frontend (DRY)

- `DimensionRatings` + `StarRating` render every rating in the app (form, history, summary). Stars preview on hover and fill on click; read-only mode supports partial stars for averages.
- `lib/feedback.ts` is the single source for the three dimensions, field mapping, formatting, grouping and API-error flattening.
- `useApiResource` (fetch + loading/error) and `CardStatus` (skeleton / error / empty) are shared by all cards; `useServerEvents` handles the SSE stream.
- `FeedbackProvider` owns the student/parent data so the form and history stay in sync, and implements the **optimistic submit** (entry appears and the session leaves the eligible list at once; both are rolled back and the server's validation messages shown if the request fails).
- UI primitives are shadcn/ui; every card is wrapped in the existing `DashboardCard`, rendered by role.

## Trade-offs given the time

- **SSE broker is in-process memory:** fine for the dev server / one worker; multiple workers need Redis (the `publish` interface is the seam). Events are not persisted: a user offline at completion still sees the session on next load because eligibility is recomputed from the database.
- Streaming uses `fetch` rather than `EventSource` (which cannot send the `Authorization` header).
- Eligible sessions are filtered in Python (the completion time may live in JSON metadata), which is fine at this scale.
- Lists request `page_size=100` and do not paginate in the UI.
- No instructor picker for admins in the UI (the API supports `?instructor_id=`).
- The summary window is by `scheduled_date`, not `completed_at`.
- `seed_feedback` is an optional demo command; `seed_data` is unchanged (it creates no feedback).
