# Dayflow — Implementation Phases

Dayflow is a personal productivity application with:

- task management
- reminders
- daily email digests
- weekly productivity summaries
- a scheduler
- Kafka-based background job processing
- worker consumers

The project should be built incrementally.

Do not implement future phases early.

Each phase should be understandable and working before moving to the next one.

---

# Phase 1 — Basic Task Management

## Goal

Build the core productivity app before introducing scheduling or Kafka.

The user should be able to create, view, update, complete, and delete tasks.

## Tech

- Python
- FastAPI
- PostgreSQL
- SQLAlchemy 2.x
- Alembic
- psycopg
- Pydantic

All timestamps are stored in PostgreSQL as timezone-aware UTC values (`TIMESTAMPTZ`). API timestamps must include a timezone offset and are converted to UTC before persistence.

## Task Model

Create a `tasks` table with fields such as:

```text
id
title
description
status
priority
due_at
reminder_at
created_at
completed_at
```

Suggested statuses:

```text
PENDING
COMPLETED
```

Suggested priorities:

```text
LOW
MEDIUM
HIGH
```

## Endpoints

Implement:

```http
POST   /tasks
GET    /tasks
GET    /tasks/{id}
PATCH  /tasks/{id}
DELETE /tasks/{id}
```

The API should support:

- creating tasks
- listing tasks
- marking a task complete
- changing priority
- changing due date
- assigning a reminder time

## Example

```json
{
  "title": "Study Kafka",
  "description": "Learn partitions and consumer groups",
  "priority": "HIGH",
  "due_at": "2026-08-23T21:00:00+05:30",
  "reminder_at": "2026-08-23T20:00:00+05:30"
}
```

## Learn

- FastAPI routing
- request/response models
- CRUD
- Pydantic validation
- PostgreSQL
- basic SQL/database modeling
- timestamps
- separating API logic from database logic

## Done When

- tasks can be created
- tasks can be listed
- individual tasks can be retrieved
- tasks can be updated
- tasks can be marked complete
- tasks can be deleted

---

# Phase 2 — Productivity Preferences

## Goal

Allow the user to configure when periodic summaries should be generated.

For the first version, the application may remain single-user.

Do not add authentication yet.

## Preferences

Store:

```text
email
timezone
daily_digest_enabled
daily_digest_time
weekly_summary_enabled
weekly_summary_day
weekly_summary_time
```

Example:

```json
{
  "email": "user@example.com",
  "timezone": "Asia/Kolkata",
  "daily_digest_enabled": true,
  "daily_digest_time": "20:00",
  "weekly_summary_enabled": true,
  "weekly_summary_day": "SUNDAY",
  "weekly_summary_time": "20:00"
}
```

## Endpoints

Implement:

```http
GET   /preferences
PATCH /preferences
```

## Learn

- configuration stored in a database
- time-based preferences
- partial updates
- modeling user settings

## Done When

- email preference can be stored
- daily digest can be enabled/disabled
- digest time can be changed
- weekly summary settings can be changed

---

# Phase 3 — Basic Scheduler

## Goal

Build the scheduling logic before Kafka is introduced.

Create a separate scheduler process.

Suggested location:

```text
scheduler/
└── scheduler.py
```

The scheduler periodically checks the database for things that are due.

## Scheduler Responsibilities

Detect:

```text
TASK_REMINDER
DAILY_DIGEST
WEEKLY_SUMMARY
```

Initially, do not execute jobs.

Simply print them.

Example:

```text
[Scheduler]

TASK_REMINDER due
Task: Study Kafka
Task ID: 12
```

or:

```text
[Scheduler]

DAILY_DIGEST due
Time: 20:00
```

## Task Reminder Logic

Phase 3 may add one minimal scheduling-state field:

```text
reminder_processed_at TIMESTAMPTZ NULL
```

`NULL` means the reminder has not been processed. A UTC timestamp records when the Phase 3 scheduler processed it. Set it when the scheduler prints the due reminder so the next polling loop does not detect it again.

Do not introduce the broader Phase 12 duplicate-prevention or idempotency mechanisms yet.

Find tasks where:

```text
reminder_at <= current time
status = PENDING
reminder_processed_at IS NULL
```

## Daily Digest Logic

If:

```text
daily_digest_enabled = true
```

and the digest is due, produce:

```text
DAILY_DIGEST due
```

## Weekly Summary Logic

If the configured:

```text
day + time
```

matches the current schedule, produce:

```text
WEEKLY_SUMMARY due
```

## Learn

- scheduler loops
- time comparisons
- scheduled work
- separation between API and background process

## Done When

A task can be created with a reminder time and the scheduler correctly detects it when the time becomes due.

---

# Phase 4 — Introduce Kafka

## Goal

Replace scheduler print statements with Kafka job publishing.

Architecture becomes:

```text
FastAPI
   |
   v
PostgreSQL

Scheduler
   |
   v
Kafka Producer
   |
   v
productivity-jobs
```

## Kafka Topic

Create:

```text
productivity-jobs
```

## Job Message

Use a consistent structure.

Example task reminder:

```json
{
  "job_id": "uuid",
  "type": "TASK_REMINDER",
  "task_id": 12,
  "created_at": "2026-08-23T14:30:00Z"
}
```

Example daily digest:

```json
{
  "job_id": "uuid",
  "type": "DAILY_DIGEST",
  "created_at": "2026-08-23T14:30:00Z"
}
```

Example weekly summary:

```json
{
  "job_id": "uuid",
  "type": "WEEKLY_SUMMARY",
  "created_at": "2026-08-23T14:30:00Z"
}
```

## Scheduler Responsibility

The scheduler should now:

```text
detect due work
      ↓
create job message
      ↓
publish to Kafka
```

The scheduler should not execute reminders or generate summaries.

## Learn

- Kafka producer
- brokers
- topics
- message serialization
- asynchronous messaging
- producer-consumer architecture

## Done When

A scheduled reminder results in a message appearing in the `productivity-jobs` Kafka topic.

---

# Phase 5 — Build the Worker

## Goal

Create a Kafka consumer that receives and processes jobs.

Suggested structure:

```text
worker/
├── worker.py
└── handlers.py
```

## Worker Flow

```text
Kafka
  |
  v
Worker
  |
  v
Read message
  |
  v
Inspect job type
  |
  v
Call correct handler
```

## Handlers

Implement:

```text
handle_task_reminder()
handle_daily_digest()
handle_weekly_summary()
```

Initially, handlers should print output instead of sending real emails.

Example:

```text
[Worker]

TASK REMINDER

Study Kafka
Due: 9:00 PM
Priority: HIGH
```

## Learn

- Kafka consumers
- consumer loop
- message deserialization
- handler dispatch
- background workers

## Done When

This complete flow works:

```text
Task becomes due
      ↓
Scheduler
      ↓
Kafka
      ↓
Worker
      ↓
Console output
```

---

# Phase 6 — Daily Digest Generation

## Goal

Make `DAILY_DIGEST` generate useful productivity information.

The worker should query today's task data.

"Today" is the user's local calendar day: `[00:00 today, 00:00 next day)`. Use the configured application timezone, defaulting to `Asia/Kolkata` for the current single-user version, and convert both boundaries to UTC before querying PostgreSQL.

## Calculate

```text
tasks completed today
tasks still pending
tasks overdue
tasks due tomorrow
```

## Example Output

```text
Your Daily Digest

Completed today: 3
Pending: 2
Overdue: 1

Completed:
- Finish API
- Revise OS
- Submit assignment

Pending:
- Study Kafka
- Update resume

Due Tomorrow:
- Complete DBMS project
```

Do not use an LLM.

Generate the digest using normal Python logic.

## Learn

- database queries
- date filtering
- aggregation
- formatting data
- worker-to-database interaction

## Done When

A `DAILY_DIGEST` Kafka job produces a meaningful digest based on actual task records.

---

# Phase 7 — Weekly Productivity Summary

## Goal

Generate a useful summary of the user's previous week.

The weekly interval is `[Monday 00:00, following Monday 00:00)` in the user's local timezone. Convert both boundaries to UTC before querying PostgreSQL.

## Calculate

At minimum:

```text
tasks created
tasks completed
completion percentage
overdue tasks
high-priority tasks completed
most productive day
```

Example:

```text
Weekly Productivity Summary

Tasks Created: 32
Tasks Completed: 26
Completion Rate: 81%

High Priority Completed:
9 / 10

Most Productive Day:
Wednesday

Overdue:
3
```

## Learn

- aggregation queries
- grouping data
- date ranges
- productivity metrics
- basic analytics

## Done When

A weekly summary can be generated entirely from stored task data.

---

# Phase 8 — Real Email Sending

## Goal

Replace console output with actual email delivery.

Create:

```text
app/services/email_service.py
```

Expose a simple function:

```python
send_email(
    to,
    subject,
    body
)
```

Possible implementation options:

- SMTP
- Resend
- SendGrid
- another simple transactional email provider

The worker should not contain provider-specific email code directly.

## Flow

```text
Kafka
  ↓
Worker
  ↓
Generate content
  ↓
Email service
  ↓
Inbox
```

## Email Types

Support:

```text
Task Reminder
Daily Digest
Weekly Summary
```

## Learn

- external API/service integration
- SMTP or transactional email APIs
- service abstraction
- handling external failures

## Done When

A real scheduled reminder or digest arrives in the configured email inbox.

---

# Phase 9 — Multiple Kafka Workers

## Goal

Understand Kafka consumer groups and parallel processing.

Run multiple worker processes.

Example:

```text
                productivity-jobs
                       |
            +----------+----------+
            |          |          |
            v          v          v
         Worker 1   Worker 2   Worker 3
```

All workers should use the same:

```text
consumer_group = dayflow-workers
```

Configure the Kafka topic with multiple partitions.

Example:

```text
Partition 0 -> Worker 1
Partition 1 -> Worker 2
Partition 2 -> Worker 3
```

Run the workers manually in separate terminals.

## Experiment

Publish many jobs.

For example:

```text
20 reminder jobs
10 digest jobs
```

Observe which workers process them.

## Learn

- partitions
- consumer groups
- partition assignment
- parallel consumers
- horizontal worker scaling
- offsets

## Done When

Multiple workers process jobs from the same topic without all workers independently processing every message.

---

# Phase 10 — Job Tracking

## Goal

Track the lifecycle of each background job.

Create a `jobs` table.

Suggested fields:

```text
id
type
status
task_id
created_at
started_at
completed_at
error
```

Statuses:

```text
QUEUED
RUNNING
SUCCESS
FAILED
```

## Lifecycle

Scheduler:

```text
create job
   ↓
QUEUED
```

Worker receives:

```text
QUEUED
   ↓
RUNNING
```

Worker succeeds:

```text
RUNNING
   ↓
SUCCESS
```

Worker fails:

```text
RUNNING
   ↓
FAILED
```

## Endpoint

Optionally add:

```http
GET /jobs
GET /jobs/{job_id}
```

## Learn

- job state machines
- background job observability
- persistence
- lifecycle tracking

## Done When

Every scheduled background operation can be inspected after execution.

---

# Phase 11 — Failure Handling and Retries

## Goal

Handle temporary job failures.

Start by creating a fake job handler that intentionally fails sometimes.

Example:

```text
send email
   ↓
temporary failure
```

Implement a simple retry mechanism.

Maximum:

```text
3 attempts
```

Possible Kafka topics:

```text
productivity-jobs
productivity-jobs-retry
productivity-jobs-dead
```

Do not overcomplicate retry timing initially.

## Example Flow

```text
Job
 |
 v
Worker
 |
 fail
 |
 v
attempt < 3?
 |
 +---- yes ---> retry
 |
 +---- no ----> dead topic
```

## Learn

- transient failures
- retry policies
- Kafka offset behavior
- dead-letter queues
- failure isolation

## Done When

A failed job retries a limited number of times and eventually either succeeds or moves to the dead-letter topic.

---

# Phase 12 — Prevent Duplicate Scheduled Jobs

## Goal

Prevent the scheduler from publishing the same reminder or digest multiple times.

## Example Bug

Scheduler checks every 5 seconds:

```text
20:00:00
digest due -> publish

20:00:05
digest still appears due -> publish again

20:00:10
publish again
```

The user receives three emails.

This must be prevented.

## Reminder Strategy

Phase 3 already stores the minimal reminder processing state:

```text
reminder_processed_at TIMESTAMPTZ NULL
```

Phase 12 adds the broader claim/idempotency behavior needed when publishing and consuming jobs. Reuse the timestamp rather than adding a boolean flag.

## Periodic Digest Strategy

Store:

```text
next_daily_digest_at
next_weekly_summary_at
```

When a digest becomes due:

```text
read current next_run
       ↓
claim/create job
       ↓
advance next_run
```

Do this carefully so repeated scheduler loops do not generate duplicates.

## Learn

- race conditions
- idempotency
- scheduler correctness
- state transitions
- duplicate background jobs

## Done When

Running the scheduler frequently does not produce duplicate reminders or duplicate periodic digests.

---

# Phase 13 — Cleanup and Tests

## Goal

Make the local project clean and defensible.

Still do not add unnecessary production infrastructure.

## Add Tests For

```text
task CRUD
task completion
preference updates
scheduler due-time detection
daily digest calculation
weekly summary calculation
job status transitions
handler routing
duplicate-schedule prevention
retry limits
```

## Improve

- README
- local setup instructions
- API examples
- architecture diagram
- error handling
- type hints
- code organization

## Do Not Add Yet

Unless explicitly requested:

```text
Docker
Kubernetes
Prometheus
Grafana
cloud deployment
authentication
microservices
LLMs
Redis
complex monitoring
```

## Done When

The project can be run locally, demonstrated cleanly, and explained end-to-end.

---

# Final Architecture

```text
                         User
                          |
                          v
                       FastAPI
                          |
                          v
                        PostgreSQL
                  +-------+-------+
                  |       |       |
                Tasks  Preferences Jobs
                          |
                          v
                      Scheduler
                          |
                          v
                    Kafka Producer
                          |
                          v
                  productivity-jobs
                          |
                +---------+---------+
                |         |         |
                v         v         v
             Worker 1  Worker 2  Worker 3
                |
                v
             Handlers
          +-----+------+------+
          |            |      |
          v            v      v
      Reminder      Daily   Weekly
                    Digest  Summary
          |            |      |
          +------------+------+
                       |
                       v
                  Email Service
                       |
                       v
                   User Inbox
```

---

# Recommended Development Order

Do not think about all phases at once.

Build in this order:

```text
Phase 1
Task CRUD

   ↓

Phase 2
Preferences

   ↓

Phase 3
Scheduler prints due work

   ↓

Phase 4
Scheduler publishes to Kafka

   ↓

Phase 5
Worker consumes Kafka messages

   ↓

Phase 6
Daily digest

   ↓

Phase 7
Weekly summary

   ↓

Phase 8
Real emails

   ↓

Phase 9
Multiple workers

   ↓

Phase 10
Job tracking

   ↓

Phase 11
Retries / DLQ

   ↓

Phase 12
Duplicate prevention

   ↓

Phase 13
Tests + cleanup
```

---

# First Milestone

Do not start Kafka immediately.

The first milestone is:

```text
1. Create a task
2. Give it a reminder time
3. Store it in PostgreSQL
4. Run the scheduler
5. Scheduler detects that reminder
6. Scheduler prints:

   Reminder Due:
   Study Kafka
```

Once that works, introduce Kafka.

The key learning progression is:

```text
"I need scheduled work"
        ↓
build scheduler
        ↓
"I don't want scheduler executing work"
        ↓
introduce Kafka
        ↓
"I need something to consume the work"
        ↓
build workers
        ↓
"I need multiple jobs processed concurrently"
        ↓
use Kafka partitions + consumer groups
```

Every technology should enter the project because it solves a real problem.
