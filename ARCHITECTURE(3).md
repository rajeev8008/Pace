# Dayflow — Architecture

Dayflow is a personal productivity application that helps a user:

- create and manage tasks
- schedule task reminders
- receive daily productivity digests
- receive weekly productivity summaries

The main engineering feature of Dayflow is its background job system:

```text
Scheduler -> Kafka -> Workers
```

The system should remain simple and local-first while the project is being learned and built.

---

# 1. High-Level Architecture

```text
                         User
                          |
                          | HTTP
                          v
                     +----------+
                     | FastAPI  |
                     +----+-----+
                          |
                          v
                     +----------+
                     |  PostgreSQL  |
                     +----+-----+
                          ^
                          |
                    reads schedules
                          |
                     +----+-----+
                     | Scheduler|
                     +----+-----+
                          |
                          | publish job
                          v
                  +------------------+
                  |      Kafka       |
                  | productivity-jobs|
                  +--------+---------+
                           |
                           | consume
                           v
                  +------------------+
                  |      Worker      |
                  +--------+---------+
                           |
                 +---------+----------+
                 |         |          |
                 v         v          v
            Reminder    Daily       Weekly
             Handler    Digest      Summary
                 \         |          /
                  \        |         /
                   +-------+--------+
                           |
                           v
                    +-------------+
                    |Email Service|
                    +-------------+
```

---

# 2. Why This Architecture Exists

Dayflow has two different kinds of work.

## User-facing work

Examples:

```text
Create a task
Mark a task complete
Change a due date
Update digest preferences
```

These operations should happen immediately through FastAPI.

## Background work

Examples:

```text
Send reminder at 5:00 PM
Generate daily digest at 8:00 PM
Generate weekly summary on Sunday
```

These operations happen later and should not block API requests.

Therefore Dayflow separates:

```text
API request handling
```

from:

```text
scheduled background execution
```

---

# 3. Component Responsibilities

## 3.1 FastAPI

FastAPI is the user-facing backend.

Responsibilities:

- create tasks
- list tasks
- update tasks
- delete tasks
- mark tasks complete
- save reminder times
- save daily digest preferences
- save weekly summary preferences
- expose job status later

FastAPI should not:

- continuously check the clock
- generate scheduled digests
- consume Kafka messages
- perform long-running background jobs

Example:

```text
POST /tasks

        |
        v

FastAPI validates request

        |
        v

PostgreSQL stores task

        |
        v

HTTP response
```

---

# 3.2 PostgreSQL

PostgreSQL is the source of application state for Dayflow.

All timestamps are stored as timezone-aware UTC values (`TIMESTAMPTZ`). Incoming timestamps must include an offset and are converted to UTC before persistence.

Use:

```text
SQLAlchemy 2.x
Alembic
psycopg
```

It stores:

```text
Tasks
Preferences
Scheduled timestamps
Job records later
```

Initial logical tables:

```text
tasks
preferences
```

Later:

```text
jobs
```

Suggested `tasks` fields:

```text
id
title
description
status
priority
due_at
reminder_at
reminder_processed_at (added in Phase 3)
created_at
completed_at
```

Suggested `preferences` fields:

```text
id
email
timezone (defaults to Asia/Kolkata)
daily_digest_enabled
daily_digest_time
next_daily_digest_at
weekly_summary_enabled
weekly_summary_day
weekly_summary_time
next_weekly_summary_at
```

PostgreSQL gives Dayflow a strong relational backend while keeping the project focused on application architecture, scheduling, Kafka, and workers.

---

# 3.3 Scheduler

The scheduler is a separate Python process.

Its responsibility is:

> Determine what work is due now.

Conceptually:

```text
while running:

    check task reminders

    check daily digest schedule

    check weekly summary schedule

    if something is due:
        create a job
        publish it
```

The scheduler does not perform the work itself.

Bad design:

```text
Scheduler
   |
   v
Generate digest
   |
   v
Send email
```

Better design:

```text
Scheduler
   |
   v
Create job
   |
   v
Kafka
```

This keeps scheduling and execution separate.

---

# 4. Kafka

Kafka sits between the scheduler and workers.

Topic:

```text
productivity-jobs
```

Kafka's responsibility is:

> Hold and distribute background jobs until workers process them.

Example message:

```json
{
  "job_id": "550e8400-e29b-41d4-a716-446655440000",
  "type": "TASK_REMINDER",
  "task_id": 12,
  "created_at": "2026-08-23T11:30:00Z"
}
```

Daily digest:

```json
{
  "job_id": "1c03b0c9-c234-43e5-b244-9709d95d1503",
  "type": "DAILY_DIGEST",
  "created_at": "2026-08-23T14:30:00Z"
}
```

Weekly summary:

```json
{
  "job_id": "4f8b185b-0dc8-49d8-9c21-b52f150ab8d7",
  "type": "WEEKLY_SUMMARY",
  "created_at": "2026-08-23T14:30:00Z"
}
```

The scheduler acts as:

```text
Kafka Producer
```

The worker acts as:

```text
Kafka Consumer
```

---

# 5. Worker

A worker is a separate Python process that consumes Kafka jobs.

Basic flow:

```text
Kafka message
     |
     v
Read job type
     |
     v
Select handler
     |
     v
Execute handler
```

Example dispatch:

```text
TASK_REMINDER
      |
      v
handle_task_reminder()


DAILY_DIGEST
      |
      v
handle_daily_digest()


WEEKLY_SUMMARY
      |
      v
handle_weekly_summary()
```

The worker should keep consuming jobs after one job finishes.

One failed job should not permanently stop the worker.

---

# 6. Handler Layer

Handlers contain the actual background-job behavior.

Suggested handlers:

```text
handle_task_reminder
handle_daily_digest
handle_weekly_summary
```

## Task Reminder Handler

Input:

```text
task_id
```

Flow:

```text
Load task
   |
   v
Format reminder
   |
   v
Send email
```

Example:

```text
Reminder: Study Kafka

Due: Today at 9:00 PM
Priority: HIGH
```

---

# 7. Daily Digest Handler

The daily digest worker queries the database for relevant tasks.

Its query interval is the user's local calendar day: `[00:00 today, 00:00 next day)`. The boundaries are calculated in the configured application timezone and converted to UTC before querying PostgreSQL.

It should find:

```text
completed today
pending today
overdue
due tomorrow
```

Flow:

```text
DAILY_DIGEST job
       |
       v
Query PostgreSQL
       |
       v
Calculate summary
       |
       v
Format email
       |
       v
Send email
```

Example:

```text
Your Dayflow Daily Digest

Completed today: 3
Pending: 2
Overdue: 1

Completed
- Finish API
- Revise OS
- Submit assignment

Pending
- Study Kafka
- Update resume

Due Tomorrow
- Finish DBMS project
```

No LLM is required.

---

# 8. Weekly Summary Handler

The weekly summary queries tasks from the previous week.

Its query interval is `[Monday 00:00, following Monday 00:00)` in the user's local timezone. Both boundaries are converted to UTC before querying PostgreSQL.

Calculate:

```text
tasks created
tasks completed
completion rate
overdue tasks
high-priority tasks completed
most productive day
```

Example:

```text
Your Dayflow Weekly Summary

Tasks created: 32
Tasks completed: 26
Completion rate: 81%

Most productive day:
Wednesday

Overdue:
3
```

---

# 9. Email Service

Email delivery should be behind a small service abstraction.

Example interface:

```python
send_email(
    to,
    subject,
    body
)
```

Handlers should not need to know whether email is sent using:

```text
SMTP
Resend
SendGrid
```

Initial development may simply print email contents to the terminal.

Later:

```text
Worker
   |
   v
Email Service
   |
   v
Real Inbox
```

---

# 10. Complete Task Reminder Flow

Suppose the user creates:

```text
Task:
Study Kafka

Due:
9:00 PM

Reminder:
8:00 PM
```

Flow:

```text
1. User

      |
      | POST /tasks
      v

2. FastAPI

      |
      v

3. PostgreSQL

Task stored with:
reminder_at = 20:00

      |
      v

4. Scheduler

At 20:00:
find reminder_at <= now

      |
      v

5. Kafka Producer

Publish:

{
  type: TASK_REMINDER,
  task_id: 12
}

      |
      v

6. Kafka

productivity-jobs

      |
      v

7. Worker

consume message

      |
      v

8. Reminder Handler

load Task 12

      |
      v

9. Email Service

send reminder
```

---

# 11. Complete Daily Digest Flow

Suppose the user configures:

```text
Daily digest:
8:00 PM
```

At 8 PM:

```text
Scheduler
   |
   | digest is due
   v
Kafka
   |
   | DAILY_DIGEST
   v
Worker
   |
   v
Query today's tasks
   |
   v
Generate digest
   |
   v
Email Service
```

---

# 12. Multiple Workers

Initially use one worker.

Later run multiple workers in the same Kafka consumer group:

```text
                     Kafka
              productivity-jobs
                     |
          +----------+----------+
          |          |          |
          v          v          v
       Worker 1   Worker 2   Worker 3
```

Kafka partitions allow different workers to process jobs in parallel.

Example:

```text
Partition 0 -> Worker 1
Partition 1 -> Worker 2
Partition 2 -> Worker 3
```

All workers belong to:

```text
consumer group:
dayflow-workers
```

This means a job is assigned to one consumer in the group rather than every worker receiving the same job.

---

# 13. Job Types

Keep the job system small.

Initial supported job types:

```text
TASK_REMINDER
DAILY_DIGEST
WEEKLY_SUMMARY
```

Do not build a generic job scheduler framework.

Dayflow's scheduler exists specifically to support Dayflow features.

---

# 14. Job Lifecycle

Once job tracking is implemented:

```text
             QUEUED
                |
                v
             RUNNING
                |
        +-------+-------+
        |               |
        v               v
     SUCCESS          FAILED
```

The scheduler creates the job.

The worker executes it.

PostgreSQL stores its state.

---

# 15. Failure and Retry Architecture

Later phases can introduce:

```text
productivity-jobs
       |
       v
     Worker
       |
      fail
       |
       v
productivity-jobs-retry
       |
      fail repeatedly
       |
       v
productivity-jobs-dead
```

Keep retries simple:

```text
maximum attempts = 3
```

Do not build complicated retry infrastructure initially.

---

# 16. Duplicate Scheduling Problem

The scheduler may run every few seconds.

Without protection:

```text
20:00:00 -> digest due -> publish
20:00:05 -> digest still due -> publish
20:00:10 -> digest still due -> publish
```

This would generate duplicate emails.

Dayflow should track scheduling state such as:

```text
next_daily_digest_at
next_weekly_summary_at
reminder_processed_at
```

Phase 3 uses only `reminder_processed_at` to stop a reminder being detected repeatedly. Phase 12 adds the broader claim/idempotency behavior and periodic `next_*` state needed for Kafka publishing and consumption.

---

# 17. Suggested Project Structure

```text
dayflow/
|
├── app/
│   ├── main.py
│   ├── database.py
│   ├── models.py
│   ├── schemas.py
│   |
│   ├── api/
│   │   ├── tasks.py
│   │   └── preferences.py
│   |
│   └── services/
│       ├── task_service.py
│       └── email_service.py
|
├── scheduler/
│   └── scheduler.py
|
├── messaging/
│   └── kafka_producer.py
|
├── worker/
│   ├── worker.py
│   └── handlers.py
|
├── tests/
|
├── requirements.txt
├── README.md
├── PHASES.md
└── ARCHITECTURE.md
```

Do not create layers that are not needed yet.

---

# 18. Processes Running Locally

Eventually the developer runs three main processes:

## Terminal 1

```text
FastAPI
```

Example:

```bash
uvicorn app.main:app --reload
```

## Terminal 2

```text
Scheduler
```

Example:

```bash
python -m scheduler.scheduler
```

## Terminal 3

```text
Worker
```

Example:

```bash
python -m worker.worker
```

Kafka runs separately.

Later, multiple workers can be started from additional terminals.

---

# 19. What Dayflow Is Teaching

The important software-engineering concepts are:

```text
REST APIs
database design
background processes
scheduling
producer-consumer architecture
Kafka producers
Kafka consumers
topics
partitions
consumer groups
offsets
workers
asynchronous processing
failure handling
retries
dead-letter queues
idempotency
race conditions
separation of concerns
```

---

# 20. Non-Goals

For the initial learning version, do not introduce:

```text
Docker
Kubernetes
Prometheus
Grafana
Redis
microservices
cloud infrastructure
authentication
LLMs
complex event-driven architecture
generic workflow engines
```

These can be considered later only if Dayflow develops a real requirement for them.

---

# 21. Architectural Principle

Every component must answer a concrete question.

```text
FastAPI
"What does the user want?"

PostgreSQL
"What tasks and settings exist?"

Scheduler
"What needs to happen now?"

Kafka
"What background work needs to be distributed?"

Worker
"Who will execute this work?"

Handler
"What does this job actually do?"

Email Service
"How does the result reach the user?"
```

If a new technology cannot answer a real problem in Dayflow, do not add it.
