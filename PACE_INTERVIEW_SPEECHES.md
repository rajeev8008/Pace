# Pace Interview Speeches

## 2-minute version

Pace is a multi-user productivity platform I built with FastAPI and PostgreSQL. It brings scheduled tasks, daily routines, focus sessions, GitHub activity, and LeetCode progress into one dashboard. Each user gets a private workspace.

Users can sign in with a password, GitHub, or Google. After authentication, Pace creates an HttpOnly JWT session, and every database query is scoped by the user ID.

The main backend challenge was scheduled email. A Python scheduler finds due reminders and daily or weekly summaries. It creates a unique job in PostgreSQL, then a small runner sends the email and records success or failure. Failed jobs are tried up to three times. I used PostgreSQL as the job queue because Pace has a small workload and does not need Kafka or another message broker.

I also handled timezones by storing timestamps in UTC while calculating schedules using each user's local timezone. GitHub Actions tests the application against PostgreSQL and checks migrations, authentication, scheduling, integrations, and email generation.

## 5-minute version

Pace solves a simple problem: planning work and reviewing completed work usually happen in different places. It combines tasks, recurring routines, focus sessions, GitHub work, and LeetCode submissions in one personal timeline and consistency view.

The frontend is plain HTML, CSS, and JavaScript served by FastAPI. The API is split into routes for authentication, tasks, routines, focus, activity, profiles, preferences, and jobs. PostgreSQL is the source of truth, and Alembic manages schema changes.

The system supports separate accounts. Users can register normally or use GitHub and Google OAuth. Pace then issues its own signed JWT in an HttpOnly cookie. The JWT subject is the database user ID, and routes use that ID in their queries so one user cannot read another user's data.

For developer activity, a user links a public GitHub or LeetCode profile. Pace imports recent events and accepted submissions and stores stable external IDs to avoid duplicate rows.

Reminders and summaries run outside normal page requests. The scheduler checks tasks and user preferences, locks due rows, and creates one PostgreSQL job per occurrence. A job runner locks each queued job, builds the email, sends it through SMTP, and records the result. Failures return to the queue until three attempts have been made. The job history keeps timestamps and the final error.

I considered Kafka, but it would add a broker, topics, and consumer management for very little traffic. A durable PostgreSQL queue gives Pace the persistence, retries, inspection, and duplicate prevention it actually needs. If usage grew enough to require many workers or independent consumers, I could move job transport to a dedicated message queue.

Time handling was another important part. Pace stores timestamps in UTC but evaluates reminders and digest boundaries in each user's IANA timezone. This keeps daily and weekly reports correct even when the server runs elsewhere.

CI starts PostgreSQL, runs every migration, checks for schema drift, compiles the project, and executes focused checks for the main flows.

## 20-minute version

Use the five-minute version as the opening, then expand these areas:

1. Draw Browser → FastAPI → PostgreSQL, with GitHub and LeetCode beside FastAPI.
2. Explain the tables and why every private table or query is connected to `user_id`.
3. Walk through password login, OAuth callback, JWT creation, and cookie verification.
4. Show how completing tasks, routines, and focus sessions creates activity records.
5. Trace profile URLs through synchronization, stable external IDs, and deduplication.
6. Draw Scheduler → PostgreSQL jobs → Job runner → SMTP.
7. Explain `QUEUED`, `RUNNING`, `SUCCESS`, and `FAILED`, including the three-attempt limit.
8. Explain duplicate prevention through occurrence keys, reminder markers, next-run timestamps, and row locks.
9. Show how local day/week boundaries are converted to UTC.
10. Close with CI, current limitations, and when a separate message queue would become justified.

Keep the discussion concrete: open the corresponding model, route, scheduler function, and test when the interviewer asks for detail.

## 30-minute version

Use the 20-minute outline, then add deeper discussion:

- Compare task state with activity history: tasks describe current work; activities describe what happened.
- Explain why OAuth provider tokens are not persisted and why Pace issues its own session.
- Discuss database constraints as a second safety layer after API validation.
- Explain what happens if the scheduler runs twice or the process stops after a job is saved.
- Walk through what appears in daily and weekly email bodies.
- Discuss external API failures, GitHub rate limits, and LeetCode availability.
- Explain the choice to avoid Kafka: the database queue is easier to operate and fits the expected workload.
- Describe the upgrade point: introduce a dedicated queue when polling, lock contention, throughput, or multiple independent consumers become real problems.
- Finish with honest limitations: no delayed retry backoff, no session revocation list, and reliance on external providers for sync and SMTP delivery.

## One-line closing

Pace shows that I can turn a user-facing workflow into a secure multi-user application with reliable scheduling, clear data ownership, external integrations, and practical engineering tradeoffs.
