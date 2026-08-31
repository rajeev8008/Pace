# Pace Architecture

Pace is an intentionally single-user productivity system. It combines planning, recurring routines, focused work, completed-work history, GitHub activity, LeetCode submissions, and scheduled email without introducing a separate frontend framework or a generic workflow engine.

## System context

```mermaid
flowchart TB
    User([Owner]) --> UI[HTML, CSS, JavaScript]
    UI --> API[FastAPI REST API]
    API --> DB[(PostgreSQL)]
    API --> OAuth[GitHub and Google OAuth]
    API --> External[External APIs: GitHub REST / LeetCode GraphQL]

    Scheduler --> DB
    Scheduler --> MainTopic[productivity-jobs]
    MainTopic --> Worker[Kafka worker]
    RetryTopic[productivity-jobs-retry] --> Worker
    Worker --> DB
    Worker --> RetryTopic
    Worker --> DeadTopic[productivity-jobs-dead]
    Worker --> Email[SMTP]
    Email --> User
```

The request path and background path are deliberately separate:

- FastAPI handles interactive operations and profile synchronization.
- The scheduler detects due reminder and digest work.
- Kafka transports persisted job identifiers.
- Workers execute email jobs outside HTTP requests.

## Runtime components

### Frontend

FastAPI serves a dependency-free single-page interface from `app/static`. It provides:

- dashboard and dedicated focus views
- fast task and daily-routine entry
- task editing, completion, filtering, and deletion
- preference, profile-connection, and account controls
- three daily activity feeds for Pace, GitHub, and LeetCode activity
- an 84-day consistency tracker
- responsive light and dark themes

The browser calls authenticated JSON endpoints. It never accesses PostgreSQL directly.

### FastAPI application

Routers are divided by capability:

| Module | Responsibility |
|---|---|
| `auth.py` | Owner login, logout, session verification, GitHub OAuth, and Google OAuth |
| `tasks.py` | Scheduled-task CRUD and completion activities |
| `daily_tasks.py` | Recurring routines and local-day completion records |
| `focus_sessions.py` | Start, stop, list, and read the single active focus timer |
| `activities.py` | Local-day and recent activity queries plus edit/delete operations |
| `profiles.py` | GitHub and LeetCode connection and synchronization |
| `preferences.py` | Email, timezone, and digest schedule settings |
| `jobs.py` | Background-job inspection |

All application routers except authentication require a valid HS256 JWT from the HttpOnly session cookie.

### PostgreSQL

SQLAlchemy 2.x models define the source of truth and Alembic versions `0001` through `0012` evolve the schema. The latest schema retains ownership columns for compatibility with databases created during the former multi-user version, but the application now accepts only owner `id = 1`.

| Table | Stored state and key guarantees |
|---|---|
| `users` | The application authenticates only owner `id = 1`; unique username, email, GitHub ID, and Google ID |
| `tasks` | Status, priority, due/reminder timestamps, completion state, and reminder processing time |
| `preferences` | One settings row, IANA timezone, email, digest schedules, and next occurrences |
| `daily_tasks` | Definitions of recurring daily routines |
| `daily_task_completions` | One completion per routine and local calendar date |
| `focus_sessions` | UTC start/end, duration, category, notes, linked routine, and one nullable active slot |
| `activities` | Editable task/routine/focus events and deduplicated external activity |
| `external_profiles` | At most one GitHub and one LeetCode profile plus last-sync state |
| `jobs` | Type, lifecycle, occurrence key, attempts, timestamps, and terminal error |

Database constraints enforce enum-like values, one active focus session, unique external activity IDs, unique source activities, unique scheduling occurrences, and the single-owner model.

### Scheduler

`scheduler.scheduler` is a continuously running process. Every configured interval it:

1. locks and claims pending task reminders whose `reminder_at` is due;
2. advances enabled daily and weekly schedule state;
3. creates durable `QUEUED` job rows with unique occurrence keys;
4. publishes unpublished job identifiers to Kafka;
5. records `published_at` only after producer delivery succeeds.

`SELECT ... FOR UPDATE SKIP LOCKED`, `reminder_processed_at`, periodic `next_*` timestamps, and unique occurrence keys prevent repeated scheduling.

### Kafka

Pace creates three three-partition topics:

| Topic | Purpose |
|---|---|
| `productivity-jobs` | Newly scheduled work |
| `productivity-jobs-retry` | Jobs awaiting another attempt |
| `productivity-jobs-dead` | Jobs that exhausted three attempts |

Messages contain the durable job ID, job type, creation timestamp, attempt count, and task ID when applicable. Workers use the `pace-workers` consumer group and commit Kafka offsets only after the database-backed processing attempt completes.

### Worker and handlers

`worker.worker` consumes the main and retry topics, locks the corresponding database job, and dispatches one of three handlers:

- `TASK_REMINDER`
- `DAILY_DIGEST`
- `WEEKLY_SUMMARY`

The lifecycle is `QUEUED -> RUNNING -> SUCCESS`. A handler failure increments `attempts`, records the error, and republishes to the retry topic while fewer than three attempts have run. The third failure marks the job `FAILED` and publishes it to the dead-letter topic. Already successful and terminally failed jobs are ignored when redelivered.

### Email service

Handlers call one `send_email(to, subject, body)` boundary. It uses authenticated SMTP with optional STARTTLS. Without an SMTP host, it prints the rendered message for local development.

## Core flows

### Authentication

The first matching `APP_USERNAME` / `APP_PASSWORD` login creates owner `id = 1` and stores a random-salt `scrypt` hash. Later login accepts the owner's username or email and issues a seven-day HS256 JWT containing `sub`, `iat`, and `exp` claims. The token is stored in a cookie with `HttpOnly`, `SameSite=Strict`, and environment-controlled `Secure` settings. Public sign-up is not available.

GitHub and Google OAuth use a random state cookie, provider callbacks, and verified email addresses. OAuth identities can create the owner or link to the existing owner only when the verified email matches. Provider access tokens are used during the callback and are not persisted.

### Planning and completion

- A scheduled task stores optional due and reminder timestamps in UTC.
- Completing a task records `completed_at` and creates one task activity.
- Reopening it removes that generated activity.
- A daily routine remains defined across days; its checkbox state comes from a completion row for the configured local date.
- Stopping a focus session calculates duration on the server and creates a focus activity. Focus sessions can repeatedly reference the same daily routine without completing it automatically.

Activity editing changes only the timeline record, not its source task, routine completion, or focus session.

### External activity

The authenticated browser requests profile synchronization on load, every 30 seconds, and when the tab becomes visible.

GitHub synchronization:

- uses authenticated user events when `GITHUB_SYNC_TOKEN` exists and public events otherwise;
- imports pull requests, reviews, issues, comments, repository creation, releases, stars, and other recent events;
- uses GitHub commit search for recent commits authored by the linked username;
- keys commits by SHA and external events by GitHub event ID;
- rebuilds overlapping recent commit rows to avoid duplicate counts.

LeetCode synchronization uses the public GraphQL endpoint to import up to 20 recent accepted submissions and resolve frontend problem numbers. Both providers are upstream dependencies and may return rate-limit or availability errors.

The dashboard groups same-day commits by repository and shows accepted submissions separately. The consistency tracker aggregates tasks, routines, focus sessions, repository commit totals, and LeetCode problems by local date.

### Reminder and digest delivery

```mermaid
sequenceDiagram
    participant S as Scheduler
    participant D as PostgreSQL
    participant K as Kafka
    participant W as Worker
    participant M as SMTP

    S->>D: Claim due occurrence and create job
    S->>K: Publish job ID
    K->>W: Deliver job
    W->>D: Lock job and mark RUNNING
    W->>D: Query task or summary data
    W->>M: Send email
    W->>D: Mark SUCCESS
    W->>K: Commit offset
```

## Time model

- PostgreSQL timestamps are timezone-aware UTC values.
- API task timestamps must contain an offset and are normalized to UTC.
- The default application timezone is `Asia/Kolkata` and can be changed to another valid IANA zone.
- A daily digest queries `[00:00 today, 00:00 next day)` in local time after converting both boundaries to UTC.
- A weekly summary queries the previous `[Monday 00:00, following Monday 00:00)` local interval after UTC conversion.
- Daily-routine state and activity feeds use the user's local calendar date.

## Security and reliability boundaries

- Secrets come from environment variables and are not stored in source control.
- JWT signatures use HS256 and constant-time comparison, and verification rejects unexpected algorithm metadata.
- Password hashes use `scrypt` with a random 16-byte salt.
- OAuth state validation protects callbacks against request forgery.
- Pydantic validates input shape, lengths, timezone names, and timestamp offsets.
- Database constraints backstop application validation and concurrency rules.
- Kafka delivery is confirmed before `published_at` is set.
- Worker offsets use explicit synchronous commits.
- Retry and dead-letter state remains inspectable through PostgreSQL job endpoints.

Pace does not currently encrypt application data at the field level, persist OAuth provider tokens, delay retry-topic consumption with backoff, or support multiple application users.

## Runtime boundary

Pace is intended to run as a personal system. FastAPI, PostgreSQL, Kafka, the scheduler, and the worker run locally or on infrastructure controlled by the owner. GitHub Actions is used only for CI; it does not run application jobs.

## Verification

GitHub Actions runs against PostgreSQL 17 and performs:

1. dependency installation;
2. `alembic upgrade head`;
3. `alembic check`;
4. Python compilation;
5. isolated checks covering CRUD, preferences, scheduling, routines, authentication, focus, activities, OAuth, and external profiles.

The test suite uses SMTP console mode, so CI verifies message generation and job behavior without sending external email.
