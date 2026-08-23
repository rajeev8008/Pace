# Dailyflow

Dailyflow is a local-first productivity application that combines a responsive task dashboard with a durable background-job pipeline. Users manage tasks and schedules through a FastAPI-served web interface, while PostgreSQL, a standalone scheduler, Apache Kafka, and horizontally scalable workers coordinate reminders and productivity summaries.

The project demonstrates end-to-end software engineering across API design, relational data modeling, timezone-safe scheduling, asynchronous messaging, concurrency control, retry handling, observability, testing, and frontend integration.

## Demo

<!-- Upload your demo video to GitHub, then replace the placeholder below with the generated video URL. -->

> Dailyflow interface walkthrough video will be added here.

## Features

- Create, retrieve, update, complete, filter, and delete tasks
- Track recurring daily routines that reset each local calendar day while preserving completion history
- Set priorities, due dates, and reminder timestamps
- Configure email, timezone, daily digest, and weekly summary preferences
- Schedule work using the user's local timezone while storing PostgreSQL timestamps in UTC
- Deliver task reminders, daily digests, and weekly summaries through SMTP
- Distribute background jobs across Kafka consumers in the `dayflow-workers` group
- Persist `QUEUED`, `RUNNING`, `SUCCESS`, and `FAILED` job states
- Retry failed jobs up to three times before publishing them to a dead-letter topic
- Prevent repeated reminders and duplicate periodic jobs with persisted scheduling state
- Visualize twelve weeks of completed work in a GitHub-style activity tracker
- Switch between responsive light and dark themes

## Architecture

```text
Browser
   |
   | HTTP/JSON
   v
FastAPI --------------------------> PostgreSQL
   |                                 | Tasks
   | serves UI                       | Preferences
   v                                 | Jobs
HTML / CSS / JavaScript              |
                                     v
                                 Scheduler
                                     |
                                     | publish
                                     v
                              Apache Kafka
                         productivity-jobs
                         productivity-jobs-retry
                         productivity-jobs-dead
                                     |
                           consumer group: dayflow-workers
                              +------+------+ 
                              |             |
                           Worker 1      Worker N
                              |
                              v
                    Reminder / Daily / Weekly
                              |
                              v
                         SMTP service
```

The API handles immediate user requests. The scheduler answers what work is due, Kafka distributes that work, workers execute it, and PostgreSQL remains the source of truth for both application and job state.

See the detailed [architecture document](ARCHITECTURE%283%29.md) and [implementation phases](PHASES%284%29.md).

## Engineering Highlights

| Area | Implementation |
|---|---|
| API design | FastAPI routers with Pydantic request validation and explicit response models |
| Persistence | SQLAlchemy 2.x models, PostgreSQL constraints, and versioned Alembic migrations |
| Time correctness | Offset-required API timestamps, UTC `TIMESTAMPTZ` storage, IANA timezone preferences |
| Calendar boundaries | Local daily and Monday-to-Monday weekly ranges converted to UTC before querying |
| Scheduling | Separate polling process with row locking and persisted next-run state |
| Messaging | Three-partition Kafka topics and JSON job envelopes keyed by job ID |
| Parallelism | Multiple consumers share the `dayflow-workers` group without fan-out duplication |
| Reliability | Job lifecycle persistence, manual offset commits, bounded retries, and dead-letter routing |
| Idempotency | Reminder processing timestamps, periodic occurrence keys, unique constraints, and terminal-state guards |
| Delivery | Provider-independent email service backed by authenticated SMTP and STARTTLS |
| Frontend | Dependency-free responsive UI with daily routines, scheduled work, preferences, dark mode, and activity tracking |
| Testing | Isolated SQLite checks for CRUD, validation, schedules, summaries, lifecycle transitions, retries, and deduplication |

## Technology Stack

- Python 3.11+
- FastAPI and Uvicorn
- PostgreSQL and psycopg
- SQLAlchemy 2.x and Alembic
- Apache Kafka and confluent-kafka
- Pydantic
- HTML, CSS, and JavaScript
- Python standard-library SMTP client

## Project Structure

```text
app/
  api/                 Daily-task, scheduled-task, preference, and job endpoints
  services/            Email delivery
  static/              Connected web interface
  database.py          Engine and session management
  models.py            Relational models and constraints
  schemas.py           API validation and serialization
alembic/               Database migrations
messaging/             Kafka publisher and topic setup
scheduler/             Due-work detection and publishing
worker/                Consumer loop and job handlers
tests/                 Runnable isolated checks
```

## Local Setup

### 1. Create the virtual environment

```powershell
python -m venv .venv
& ".\.venv\Scripts\python.exe" -m pip install -r requirements.txt
```

Using the virtual environment's Python directly avoids PowerShell activation-policy and path-escaping issues.

### 2. Configure PostgreSQL

Create a PostgreSQL database and application user, then copy the environment template:

```powershell
Copy-Item .env.example .env
```

Set `DATABASE_URL` in `.env`. For a PostgreSQL server on port `5433`:

```env
DATABASE_URL=postgresql+psycopg://dayflow_app:your_password@localhost:5433/dayflow
```

Apply all migrations:

```powershell
& ".\.venv\Scripts\alembic.exe" upgrade head
& ".\.venv\Scripts\alembic.exe" current
```

### 3. Configure email delivery

For Gmail, use a Google App Password rather than the account password:

```env
SMTP_HOST=smtp.gmail.com
SMTP_PORT=587
SMTP_USERNAME=your_address@gmail.com
SMTP_PASSWORD=your_app_password
SMTP_FROM=your_address@gmail.com
SMTP_STARTTLS=true
```

Set the recipient through the web preferences panel. Without `SMTP_HOST`, emails print to the worker terminal instead of leaving the machine.

### 4. Start Kafka

Start a local Kafka broker at the address configured by `KAFKA_BOOTSTRAP_SERVERS`, then create the required topics:

```powershell
& ".\.venv\Scripts\python.exe" -m messaging.setup_kafka
```

The setup command creates `productivity-jobs`, `productivity-jobs-retry`, and `productivity-jobs-dead` with three partitions each.

## Run Dailyflow

Use separate PowerShell terminals.

### API and frontend

```powershell
& ".\.venv\Scripts\python.exe" -m uvicorn app.main:app --reload
```

Open `http://127.0.0.1:8000` for Dailyflow or `http://127.0.0.1:8000/docs` for the interactive API documentation.

### Scheduler

```powershell
& ".\.venv\Scripts\python.exe" -m scheduler.scheduler
```

To inspect due work without Kafka:

```powershell
& ".\.venv\Scripts\python.exe" -m scheduler.scheduler --print-only --once
```

### Worker

```powershell
& ".\.venv\Scripts\python.exe" -m worker.worker
```

Start the same command in additional terminals to observe Kafka partition assignment across multiple workers.

## API Surface

| Method | Endpoint | Purpose |
|---|---|---|
| `POST` | `/tasks` | Create a task |
| `GET` | `/tasks` | List tasks |
| `GET` | `/tasks/{id}` | Retrieve one task |
| `PATCH` | `/tasks/{id}` | Update or complete a task |
| `DELETE` | `/tasks/{id}` | Delete a task |
| `GET` | `/preferences` | Read application preferences |
| `PATCH` | `/preferences` | Update email, timezone, or schedules |
| `GET` | `/jobs` | Inspect background jobs |
| `GET` | `/jobs/{job_id}` | Inspect one job and its failure details |
| `GET` | `/daily-tasks` | List recurring daily routines and completion history |
| `POST` | `/daily-tasks` | Create a recurring daily routine |
| `PUT` | `/daily-tasks/{id}/today` | Set today's completion state |
| `DELETE` | `/daily-tasks/{id}` | Delete a daily routine |

Example task request:

```json
{
  "title": "Study Kafka consumer groups",
  "description": "Review partitions, offsets, and rebalancing",
  "priority": "HIGH",
  "due_at": "2026-08-23T21:00:00+05:30",
  "reminder_at": "2026-08-23T20:00:00+05:30"
}
```

API timestamps must include an offset. Daily summaries use the user's local calendar day, and weekly summaries use the previous Monday-to-Monday interval. Both ranges are converted to UTC before PostgreSQL queries.

## Verification

Run the isolated checks:

```powershell
& ".\.venv\Scripts\python.exe" -m tests.test_phase1
& ".\.venv\Scripts\python.exe" -m tests.test_preferences
& ".\.venv\Scripts\python.exe" -m tests.test_background
& ".\.venv\Scripts\alembic.exe" check
```

The background check disables SMTP and uses an in-memory database, so test addresses cannot generate real outbound email.

## Scope and Tradeoffs

Dailyflow is intentionally single-user and local-first. It does not include authentication, Docker, Kubernetes, Redis, cloud infrastructure, observability platforms, microservices, or LLM-generated summaries. Those technologies would add operational cost without solving a current requirement.

The current retry path is immediate rather than delayed, SMTP is synchronous inside each worker process, and the activity tracker derives its view from the task list. These are deliberate choices for a focused learning system and clear upgrade points if workload or product requirements grow.
