# Dailyflow

Dailyflow is a full-stack productivity application for daily routines, scheduled tasks, reminders, and email summaries. It pairs a fast, responsive interface with a PostgreSQL-backed FastAPI API and a durable Kafka job pipeline.

https://github.com/user-attachments/assets/83eb173d-d2cc-4f56-9246-86f045d22fb6

## Features

- Create, retrieve, edit, complete, filter, and delete scheduled tasks
- Track recurring daily routines that reset each local calendar day
- Visualize 12 weeks of completed work in a GitHub-style activity tracker
- Configure timezone-aware reminders, daily digests, and weekly summaries
- Protect application data with signed, HttpOnly session authentication
- Switch between responsive light and dark themes
- Distribute background jobs through Kafka with retries and dead-letter handling

## Architecture

```mermaid
flowchart LR
    User([User]) --> UI[Responsive Web UI]
    UI -->|HTTPS and signed session cookie| API[FastAPI API]
    API --> DB[(PostgreSQL)]
    Scheduler[Scheduler] -->|Find due work| DB
    Scheduler -->|Publish jobs| Kafka{{Apache Kafka}}
    Kafka -->|dayflow-workers group| Workers[Worker pool]
    Workers -->|Update job state| DB
    Workers -->|Retry failures| Retry[Retry topic]
    Retry --> Workers
    Workers -->|Exhausted jobs| DLQ[Dead-letter topic]
    Workers --> Email[SMTP email service]
    Email --> User
```

FastAPI handles synchronous user requests, PostgreSQL is the source of truth, the scheduler detects due work, Kafka distributes it, and workers execute reminders and summaries independently of the request path. See [ARCHITECTURE.md](ARCHITECTURE.md) for the detailed design.

## Software Engineering Skills Demonstrated

| Skill | How Dailyflow demonstrates it |
|---|---|
| Backend engineering | Modular FastAPI routers, Pydantic validation, explicit response models, and RESTful CRUD semantics |
| Database engineering | SQLAlchemy 2.x models, PostgreSQL constraints, UTC `TIMESTAMPTZ` data, and versioned Alembic migrations |
| Security engineering | Constant-time credential comparison, signed expiring sessions, HttpOnly and SameSite cookies, protected API boundaries, and environment-managed secrets |
| Distributed systems | Kafka producers and consumers, partition-based parallelism, and the shared `dayflow-workers` consumer group |
| Reliability engineering | Persisted job states, manual offset commits, bounded retries, dead-letter routing, row locking, and idempotency controls |
| Time correctness | IANA timezone preferences and local daily and Monday-to-Monday weekly boundaries converted to UTC before queries |
| Frontend engineering | Responsive dependency-free HTML, CSS, and JavaScript with accessible dialogs, fast task entry, and theme persistence |
| Testing and CI | Isolated behavior checks plus GitHub Actions verification against a real PostgreSQL service |
| DevOps | Environment-based configuration, database migrations, health checks, and declarative Render infrastructure |

## Technology Stack

- Python 3.11+, FastAPI, Uvicorn, and Pydantic
- PostgreSQL, SQLAlchemy 2.x, Alembic, and psycopg
- Apache Kafka and confluent-kafka
- HTML, CSS, and JavaScript
- SMTP with STARTTLS
- GitHub Actions and Render Blueprints

## Project Structure

```text
app/
  api/                 Task, routine, preference, and job endpoints
  services/            Email delivery
  static/              Connected web interface
  auth.py              Login and signed-session verification
  database.py          Engine and session management
  models.py            Relational models and constraints
  schemas.py           API validation and serialization
alembic/               Database migrations
messaging/             Kafka publisher and topic setup
scheduler/             Due-work detection and publishing
worker/                Consumer loop and job handlers
tests/                 Runnable isolated checks
render.yaml            Render web service and PostgreSQL Blueprint
```

## Local Setup

### 1. Install

```powershell
python -m venv .venv
& ".\.venv\Scripts\python.exe" -m pip install -r requirements.txt
Copy-Item .env.example .env
```

Using the virtual environment's Python directly avoids PowerShell activation-policy issues.

### 2. Configure

Set PostgreSQL and authentication values in `.env`:

```env
DATABASE_URL=postgresql+psycopg://dayflow_app:your_password@localhost:5433/dayflow
APP_USERNAME=admin
APP_PASSWORD=choose_a_strong_password
SESSION_SECRET=generate_a_long_random_value
COOKIE_SECURE=false
```

Generate a session secret in PowerShell:

```powershell
[Convert]::ToBase64String([Security.Cryptography.RandomNumberGenerator]::GetBytes(32))
```

Apply the schema:

```powershell
& ".\.venv\Scripts\alembic.exe" upgrade head
```

Optional SMTP settings are documented in `.env.example`. For Gmail, use an App Password rather than the account password.

### 3. Run

```powershell
& ".\.venv\Scripts\python.exe" -m uvicorn app.main:app --reload
```

Open `http://127.0.0.1:8000`. For background delivery, start Kafka and run these commands in separate terminals:

```powershell
& ".\.venv\Scripts\python.exe" -m messaging.setup_kafka
& ".\.venv\Scripts\python.exe" -m scheduler.scheduler
& ".\.venv\Scripts\python.exe" -m worker.worker
```

## API Surface

| Method | Endpoint | Purpose |
|---|---|---|
| `POST` | `/auth/login` | Start an authenticated session |
| `POST` | `/auth/logout` | End the current session |
| `GET` | `/auth/me` | Read the authenticated identity |
| `POST`, `GET` | `/tasks` | Create and list scheduled tasks |
| `GET`, `PATCH`, `DELETE` | `/tasks/{id}` | Retrieve, update, complete, or delete a task |
| `GET`, `PATCH` | `/preferences` | Read or update application preferences |
| `GET` | `/jobs`, `/jobs/{job_id}` | Inspect background-job state |
| `GET`, `POST` | `/daily-tasks` | List or create recurring routines |
| `PUT` | `/daily-tasks/{id}/today` | Set today's routine completion |
| `DELETE` | `/daily-tasks/{id}` | Delete a recurring routine |

All application endpoints except login are protected by the session cookie. API timestamps must include an offset; PostgreSQL stores them as timezone-aware UTC values.

## Deploy to Render

[![Deploy to Render](https://render.com/images/deploy-to-render-button.svg)](https://render.com/deploy?repo=https://github.com/rajeev8008/Dayflow)

The Blueprint provisions the FastAPI web service and PostgreSQL database, runs migrations at startup, generates `SESSION_SECRET`, and asks for `APP_USERNAME` and `APP_PASSWORD`. After creation, Render provides the public `onrender.com` URL.

The web application, authentication, tasks, routines, preferences, and tracker run in this deployment. Scheduled email delivery additionally requires a reachable Kafka broker, SMTP secrets, and separate scheduler and worker processes; those are intentionally not provisioned by the free web Blueprint.

## Verification

```powershell
& ".\.venv\Scripts\python.exe" -m compileall -q app messaging scheduler worker tests
& ".\.venv\Scripts\python.exe" -m tests.test_phase1
& ".\.venv\Scripts\python.exe" -m tests.test_preferences
& ".\.venv\Scripts\python.exe" -m tests.test_background
& ".\.venv\Scripts\python.exe" -m tests.test_daily_tasks
& ".\.venv\Scripts\python.exe" -m tests.test_auth
& ".\.venv\Scripts\alembic.exe" check
```

## Author

Developed by **K Rajeev**.

## License

Dailyflow is available under the [MIT License](LICENSE).
