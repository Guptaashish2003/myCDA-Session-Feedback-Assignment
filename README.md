# myCDA -- Session Feedback

myCDA is a debate-academy dashboard (Django 5.1 + Django REST Framework backend, Next.js 14 + Tailwind + shadcn/ui frontend).
This repo contains the **Session Feedback** feature:

- After an instructor marks a session **completed**, the enrolled students and their linked parents get a real-time notification (Server-Sent Events) and can leave a 3-star-rating review (clarity, engagement, pace) plus an optional note.
- Students review for themselves; parents review on behalf of a linked child.
- Instructors see only an **anonymized, duration-weighted rolling average** of their last 10 completed sessions -- never a student, submitter or note.

Related documents: [ASSIGNMENT_SPEC.md](ASSIGNMENT_SPEC.md) (requirements), [TEST_ACCOUNTS.md](TEST_ACCOUNTS.md) (logins),
[DESIGN_DECISIONS.md](DESIGN_DECISIONS.md) (why it is built this way), [docs/](docs/) (in-depth LaTeX developer + user-testing documentation).

---

## 1. Run with Docker (easiest)

Requires Docker with Compose v2.24 or newer.

```bash
docker compose up --build
```

| Service  | URL                              | What happens on start                                                    |
|----------|----------------------------------|--------------------------------------------------------------------------|
| backend  | http://localhost:8000/api/v1/    | installs packages (image build), `migrate`, **seeds test data**, runs the server |
| frontend | http://localhost:3000            | installs packages, builds Next.js, serves it                             |

Open http://localhost:3000 and sign in with any account from [TEST_ACCOUNTS.md](TEST_ACCOUNTS.md) (password `testpass123`).

Useful commands:

```bash
docker compose up --build -d          # run in the background
docker compose logs -f backend        # follow backend logs
docker compose down                   # stop and remove the containers (data is re-seeded next time)
docker compose build --no-cache       # rebuild after changing frontend/.env
```

How the backend container starts ([backend/Dockerfile](backend/Dockerfile) + [backend/docker_start.py](backend/docker_start.py)):

1. `pip install -r requirements.txt` (cached image layer)
2. `python manage.py migrate`
3. seed according to `SEED_ON_START` -- `if-empty` (default: only when there are no users), `always` (wipe and re-seed), `never`
4. optional demo reviews when `SEED_FEEDBACK=true`
5. `python manage.py runserver 0.0.0.0:8000`

The SQLite database lives inside the container, so recreating the container gives you fresh seed data.

## 2. Run without Docker

Prerequisites: Python 3.11+, Node.js 18+ and npm.

### 2.1 Backend

```bash
cd backend

# create and activate a virtual environment
python -m venv venv
venv\Scripts\activate            # Windows (cmd / PowerShell)
# source venv/bin/activate       # macOS / Linux

pip install -r requirements.txt
python manage.py migrate
python manage.py seed_data       # users, classes, sessions (no feedback)
python manage.py runserver       # http://localhost:8000
```

Optional demo reviews (so the instructor summary has data): `python manage.py seed_feedback`.
Do **not** run it before the manual role tests in `docs/` -- those expect no existing reviews.

Backend configuration is read from environment variables (all optional, see [backend/.env.example](backend/.env.example)).
For a local run, export them in your shell, for example `set DJANGO_DEBUG=false` (cmd) or `export DJANGO_DEBUG=false` (bash).

Generate a secret key:

```bash
python -c "import secrets; print(secrets.token_urlsafe(50))"
```

### 2.2 Frontend

```bash
cd frontend
npm install
npm run dev                      # http://localhost:3000
```

The frontend calls the backend at `NEXT_PUBLIC_API_URL`. Copy [frontend/.env.example](frontend/.env.example) to
`frontend/.env.local` for `npm run dev` (or `frontend/.env` for builds). Default: `http://localhost:8000/api/v1`.
Production build: `npm run build && npm start`.

## 3. Verify it works

```bash
# log in
curl -X POST http://localhost:8000/api/v1/accounts/login/ \
  -H "Content-Type: application/json" \
  -d '{"username": "student.emma", "password": "testpass123"}'

# use the token
curl http://localhost:8000/api/v1/feedback/eligible-sessions/ -H "Authorization: Token <your-token>"
```

Run the automated tests (47: 13 original + 34 feedback):

```bash
cd backend
python manage.py test
```

Quick manual flow:

1. Log in as `coach.sarah` -> *Close Out Sessions* -> **Mark completed** on a Lincoln-Douglas session.
2. In another browser window logged in as `student.emma` or `parent.james`, a toast appears instantly and the session shows up in *Leave Session Feedback*.
3. Hover the stars, click to fill them, submit. The entry appears in *My Feedback* immediately.
4. Back as `coach.sarah`, *Session Feedback Summary* shows the anonymized weighted average (once at least 3 reviews exist).

## 4. Configuration reference

### Backend ([backend/.env.example](backend/.env.example))

| Variable | Default | Purpose |
|---|---|---|
| `DJANGO_SECRET_KEY` | dev key | Django secret key -- set your own outside development |
| `DJANGO_DEBUG` | `true` | Django debug mode |
| `DJANGO_ALLOWED_HOSTS` | `*` | comma-separated allowed hosts |
| `CORS_ALLOW_ALL_ORIGINS` | `true` | allow any browser origin (dev) |
| `CORS_ALLOWED_ORIGINS` | empty | comma-separated origins when the previous one is `false` |
| `SEED_ON_START` | `if-empty` | Docker only: `if-empty`, `always` or `never` |
| `SEED_FEEDBACK` | `false` | Docker only: also create demo reviews |
| `PORT` | `8000` | Docker only: port inside the container |
| `FEEDBACK_WINDOW_DAYS` | `30` | days after completion that feedback is accepted |
| `FEEDBACK_SUMMARY_WINDOW` | `10` | sessions in the rolling average |
| `FEEDBACK_SUMMARY_MIN_RESPONSES` | `3` | reviews needed before the summary shows averages |

### Frontend ([frontend/.env.example](frontend/.env.example))

| Variable | Default | Purpose |
|---|---|---|
| `NEXT_PUBLIC_API_URL` | `http://localhost:8000/api/v1` | backend base URL **as the browser reaches it**; baked in at build time |

## 5. API summary

| Method | Path | Roles | Purpose |
|---|---|---|---|
| POST | `/api/v1/accounts/login/` | anyone | get a token |
| GET | `/api/v1/accounts/profile/` | authenticated | current user (+ family links for parents) |
| POST | `/api/v1/classes/sessions/<id>/complete/` | instructor (own class), admin | mark completed and notify |
| POST | `/api/v1/feedback/` | student, parent | submit feedback |
| GET | `/api/v1/feedback/my/` | student, parent | history (paginated) |
| GET | `/api/v1/feedback/eligible-sessions/` | student, parent | sessions still reviewable |
| GET | `/api/v1/feedback/instructor-summary/` | instructor, admin (`?instructor_id=X`) | anonymized weighted average |
| GET | `/api/v1/feedback/events/` | authenticated | Server-Sent Events stream |

Full request/response examples are in [docs/](docs/) (section "API Reference").

## 6. Project structure and file guide

**Every `.py`, `.ts` and `.tsx` file starts with a header comment** giving its path, purpose and the functions/classes it contains with how they work. Read the header first when opening a file.

```
backend/
  manage.py, docker_start.py      CLI entry point; container start-up (migrate, seed, serve)
  config/                         settings.py (env-driven), urls.py, wsgi.py
  core/                           shared base classes: BaseModelSerializer, role permissions, StandardPagination, audit middleware
  accounts/                       User + FamilyLink, login/profile endpoints, seed_data command
  classes/                        Class, ClassEnrollment, Session; services.py (complete a session), signals.py (session_completed)
  feedback/
    models.py                     SessionFeedback (unique per session+student, 1-5 check constraints)
    policies.py                   submission rules, one class per rule
    selectors.py                  who may see / review what; notification audience
    summary.py                    weighted rolling average (pure maths + service)
    notifications.py, receivers.py  SSE broker + signal handler
    serializers.py, views.py, urls.py  API layer
    management/commands/seed_feedback.py  optional demo reviews
    tests.py                      34 tests
frontend/src/
  app/                            routes: / (redirect), /login, /dashboard (+ layout)
  components/                     DashboardCard, CardStatus, Sidebar, existing cards
  components/feedback/            FeedbackProvider, SubmitFeedbackCard, FeedbackHistoryCard, InstructorSummaryCard, CompleteSessionsCard, DimensionRatings
  components/ui/                  shadcn primitives + star-rating.tsx (hover + click-to-fill stars)
  contexts/AuthContext.tsx        login state and token storage
  hooks/                          useApiResource (GET + loading/error), useServerEvents (SSE client)
  lib/                            api.ts (fetch client), types.ts, feedback.ts (shared constants/helpers), utils.ts
docs/                             main.tex + sections/ -- developer and user-testing documentation (LaTeX)
docker-compose.yml                runs backend + frontend
```

