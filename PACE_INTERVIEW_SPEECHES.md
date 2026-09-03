# Pace — Interview Speeches

These versions describe the current multi-user architecture and portfolio-scale deployment. Speak naturally; do not memorize every sentence.

## 2-minute version

Pace is a personal productivity platform I built to combine planning and completed-work signals in one place. It supports scheduled tasks, recurring daily routines, focus sessions, GitHub activity, LeetCode progress, an activity timeline, and daily or weekly email summaries.

The interactive application is a modular FastAPI backend with a plain HTML, CSS, and JavaScript frontend. FastAPI validates requests with Pydantic, SQLAlchemy manages persistence, PostgreSQL is the source of truth, and Alembic handles schema changes.

Authentication supports local accounts or optional GitHub and Google OAuth. Passwords use salted scrypt hashes. After login, Pace creates its own seven-day HS256 JWT in an HttpOnly cookie. OAuth proves identity, but Pace still controls its own session.

The most important backend design is the reminder pipeline. A Python scheduler finds due reminders and summaries, locks the relevant PostgreSQL rows, and creates durable jobs with unique occurrence keys. It publishes only the job ID to Kafka. A consumer-group worker locks that job, builds the email, sends it through SMTP, and records success or failure. Failures have two bounded retries, followed by a failed state and dead-letter topic.

I store timestamps in UTC but interpret schedules and daily boundaries using each user's IANA timezone. Database locks, constraints, occurrence keys, and explicit Kafka delivery confirmation reduce duplicate work.

GitHub Actions CI starts PostgreSQL 17, applies and checks migrations, compiles the project, and runs focused subsystem checks. The main limitations are that Kafka must be running, SMTP is required for real mail, retry messages have no delayed backoff, and email delivery is at-least-once rather than exactly-once.

## 5-minute version

Pace started from a simple problem: tasks, habits, focus time, GitHub work, and LeetCode practice were all recorded separately. I wanted one personal system that showed both what I planned and what I actually completed.

The product has five main areas. Scheduled tasks store priority, due time, and reminder time. Daily routines remain defined across days and use separate completion records. Focus sessions store server start and end times, so refreshing the browser does not lose a timer. GitHub and LeetCode integrations import public coding activity. A unified Activity table powers the daily feed and 84-day consistency tracker.

At a high level, the browser sends JSON requests to FastAPI. Pydantic validates input, SQLAlchemy executes queries, and PostgreSQL stores durable state. I used a modular monolith because the interactive features are cohesive and do not need separate network services. The frontend is dependency-free HTML, CSS, and JavaScript because the state and number of screens are small.

Pace supports multiple private accounts. Local signup stores a salted scrypt password hash, while GitHub and Google OAuth are optional. OAuth callbacks validate a random state cookie, match provider identity or verified email, and create an account when needed. Pace then issues its own signed JWT in an HttpOnly, SameSite Strict cookie. Every protected operation receives the user ID from the verified token rather than trusting browser input.

The key architecture is scheduler to Kafka to worker. The scheduler is a continuously running Python process. It checks task reminders and digest preferences, converts local schedules to UTC, and uses row locks with skip-locked behavior while claiming due work. Each occurrence becomes a PostgreSQL Job with a stable unique key. PostgreSQL is important because Kafka is a transport, not the business source of truth.

After committing the job, the scheduler publishes its ID to the Kafka main topic and records `published_at` only after delivery confirmation. Workers use the `pace-workers` consumer group. A worker locks the database job, moves it from queued to running, selects the appropriate reminder or summary handler, and sends through SMTP. It then marks success and commits the Kafka offset.

If a handler fails, Pace records the error and increments the attempt. Attempts one and two return to queued and publish to the retry topic. Attempt three becomes failed and publishes to the dead-letter topic. Already successful or terminally failed jobs are ignored if redelivered.

Duplicate prevention exists at several layers: task reminders have a processed marker, preferences store their next occurrence, jobs have unique occurrence keys, schedulers lock rows, Kafka delivery is confirmed before publication state is saved, and workers lock and inspect job state.

Timezones are also a real design concern. Instants are stored in UTC, while “today” and “8 PM” are interpreted in an IANA timezone such as Asia/Kolkata. Daily queries use local midnight to the next local midnight, converted to a half-open UTC range.

GitHub Actions runs CI and triggers hosted jobs every ten minutes. CI launches PostgreSQL 17, applies Alembic migrations, checks model-to-schema drift, compiles Python, and runs eleven focused checks. Render hosts the portfolio-scale web service; Gmail SMTP delivers mail. Tradeoffs include free-service cold starts, provider rate limits, no JWT revocation list, and at-least-once email behavior.

## 20-minute version

Use this as a paced explanation while drawing the HLD, data model, and Kafka sequence from the study guide.

### 0:00–2:30 — Problem and result

Start with the fragmented-productivity problem. Explain that a task list records intent, while focus sessions and coding platforms record different forms of completed work. Pace combines both sides in one personal system.

Describe the visible features: one-time tasks, daily routines, focus timer, GitHub and LeetCode connections, activity history, consistency tracking, reminders, and daily or weekly summaries.

State the main engineering result: Pace is one FastAPI application for interactive work plus a separate Kafka background path for scheduled email.

### 2:30–5:00 — High-level architecture

Draw Browser → FastAPI → PostgreSQL. Add GitHub and LeetCode to the right of FastAPI. Below the database draw Scheduler → Kafka → Worker → SMTP, with the worker also reading and updating PostgreSQL.

Explain that FastAPI is a modular monolith. Routes are separated by feature but deploy and run as one program. This avoids microservice overhead while keeping code organized.

Explain the second path: the scheduler and worker have a different lifecycle from an HTTP request. Email should not block a browser request and scheduled work must exist when nobody has the page open.

### 5:00–7:30 — Data modeling

Explain current state versus history. Task answers what is pending now. Activity records that something happened. Completing a task changes Task and creates an Activity in one transaction.

Explain recurring definitions versus occurrences. DailyTask describes “practice DSA,” while DailyTaskCompletion stores one local date. A unique constraint prevents two completions for the same routine and date.

Explain FocusSession start and end timestamps. The server timestamp survives refreshes and supports accurate duration. A unique active slot prevents two timers.

Explain Job as durable background state: type, queued/running/success/failed status, occurrence key, attempts, timestamps, and error.

### 7:30–9:30 — Authentication

Pace supports local signup, with optional environment credentials to bootstrap the first account. Passwords use a random salt and scrypt.

For OAuth, Pace creates a random state value, stores it in a short-lived HttpOnly cookie, and exchanges the returned authorization code on the server. It matches provider identity first, then verified email, or creates a separate account.

After password or OAuth authentication, Pace issues its own JWT with subject, issue time, and expiry. Verification checks the expected HS256 algorithm, signature, expiry, integer subject, and existing user. The cookie is HttpOnly and SameSite Strict.

### 9:30–12:30 — Core application flows

Walk through task completion: validate the request, load the authenticated user's task, detect the state transition, set server UTC completion time, insert the task activity, and commit both writes together.

Walk through a daily routine: calculate today in the configured timezone, insert the dated completion, and create the routine activity. The database unique rule handles competing duplicate requests.

Walk through focus start: check for an active row, insert a server timestamp and active slot, and use a uniqueness rule as the final race-safe guarantee. Focus stop locks the row, records the end, calculates duration, clears the slot, and inserts an activity.

For provider sync, a user pastes a public profile URL. The backend validates the exact host, extracts the username, calls GitHub REST or LeetCode GraphQL, and normalizes provider-specific payloads into Activity. Stable external IDs prevent duplicate imports.

### 12:30–16:30 — Scheduler, Kafka, and worker

Use one concrete example: a task reminder is due at 8 PM. The scheduler converts the local schedule to a UTC instant. When due, it selects the row with `FOR UPDATE SKIP LOCKED`, creates one queued Job with an occurrence key containing the task and reminder timestamp, and records the task's reminder as processed.

The scheduler commits the database state, publishes only the job ID to `productivity-jobs`, waits for Kafka delivery confirmation, and then records `published_at`. Publishing an ID avoids stale or duplicated business data inside messages.

The worker belongs to the `pace-workers` consumer group and subscribes to the main and retry topics. It receives the ID, locks the Job row, ignores already completed terminal work, marks the row running, and dispatches by JobType.

The reminder handler loads the task. Digest handlers calculate local date boundaries, then query tasks and productive Activity rows. The email boundary uses SMTP or console output during development.

On success, the worker records success and synchronously commits the Kafka offset. On failure, it records the exception and increments attempts. The first two failures return to queued and publish to the retry topic. The third becomes failed and publishes to the dead-letter topic.

Explain why PostgreSQL and Kafka both exist. PostgreSQL is the business truth and supports queries, constraints, locks, and inspection. Kafka moves work and coordinates consumers. Kafka alone would not provide the application-specific job history.

### 16:30–18:00 — Time and reliability

All real instants use UTC. Each user's schedule uses an IANA timezone. Daily summaries calculate local midnight boundaries and convert them to UTC. Half-open ranges avoid double-counting an exact boundary.

Duplicate protection comes from locks, processed markers, stored next occurrences, unique occurrence keys, confirmed publication, row locking in the worker, and terminal-state checks.

Be honest that email is at-least-once. SMTP and PostgreSQL do not share a transaction, so a crash after SMTP accepts a message but before success is committed can produce a duplicate.

### 18:00–20:00 — CI, tradeoffs, and close

GitHub Actions starts PostgreSQL 17, installs dependencies, migrates to head, runs `alembic check`, compiles the code, and runs eleven subsystem checks. SMTP is mocked or disabled so CI cannot send real mail.

Close with the tradeoffs: Kafka is heavier than needed for one person's workload, but it demonstrates a real asynchronous boundary, consumer groups, retries, and dead-letter handling. There is no delayed backoff, no full browser suite, no session revocation list, and no deployment claim.

## 30-minute version

Use the 20-minute version, then add the following deeper sections and allow questions after each diagram.

### Add 3 minutes — Why this system shape

Explain why ordinary CRUD stays inside one FastAPI application. Splitting tasks, focus, and activities into services would introduce network calls and separate deployments without independent scale needs.

Explain why the scheduler and worker are separate processes. They run continuously, have retry behavior, and do not belong inside user-facing request latency. Kafka exists only at that meaningful boundary.

Compare with APScheduler. A scheduling library could wake a function, but Pace still needs next-occurrence state, database locks, unique job keys, attempts, and dead-letter behavior. The custom loop is small and directly expresses those rules.

### Add 2 minutes — Transactions and constraints

Validation checks input shape. Route logic checks meaningful transitions. Database constraints protect truth under concurrency.

Give the focus-start race example: two requests can both see no active session, so the unique active-slot constraint is required even after an application check. An integrity error becomes a friendly conflict response.

Give the task-completion example: state and Activity are committed together so the dashboard cannot show a completed task without its history record.

### Add 2 minutes — Kafka failure cases

If publishing fails, `published_at` stays empty and the scheduler can retry. If a worker dies before committing the Kafka offset, Kafka can redeliver. The worker checks PostgreSQL state to avoid repeating terminal work.

If processing fails normally, the job records its error before a retry message is published. The database therefore remains inspectable even if Kafka is unavailable later.

The retry topic currently has no timed delay. A production improvement would add delayed retry semantics or exponential backoff, but that is intentionally outside this portfolio scope.

### Add 1.5 minutes — Security boundaries

Discuss salted scrypt hashes, OAuth state verification, server-side code exchange, verified email account linking, non-persisted provider tokens, fixed JWT algorithm checks, constant-time signature comparison, HttpOnly cookies, and SameSite Strict.

Mention limits: JWT logout deletes the browser cookie but does not revoke a copied token; rotating the session secret invalidates all tokens.

### Add 1.5 minutes — Final résumé framing

End with:

> Pace demonstrates that I can connect a product requirement to a reliable backend design. I modeled current and historical state separately, protected state transitions with transactions and constraints, implemented multi-user authentication and data isolation with OAuth and JWT, handled local-time schedules correctly, and built a durable PostgreSQL-to-Kafka worker pipeline with bounded retries and dead-letter routing. I also verified schema and behavior against PostgreSQL in CI. I keep the claim honest: it is a portfolio system, not a production-scale deployment.

## Quick speaking checklist

1. Multi-user portfolio platform, not production SaaS.
2. FastAPI modular monolith for interactive work.
3. PostgreSQL is the source of truth.
4. Activity unifies completed work.
5. OAuth proves user identity; Pace JWT stores the session.
6. UTC instants plus IANA local calendar rules.
7. Scheduler decides; Kafka transports; worker executes.
8. PostgreSQL Job stores lifecycle and errors.
9. Main, retry, and dead-letter topics.
10. Locks and occurrence keys prevent duplicate creation.
11. SMTP is optional; console mode keeps tests safe.
12. GitHub Actions runs PostgreSQL-backed CI and the hosted job trigger.
