# Pace

Pace is a full-stack productivity application for daily routines, scheduled tasks, reminders, and email summaries. It pairs a fast, responsive interface with a PostgreSQL-backed FastAPI API and a durable Kafka job pipeline.

https://github.com/user-attachments/assets/83eb173d-d2cc-4f56-9246-86f045d22fb6

## Features

- Create, retrieve, edit, complete, filter, and delete scheduled tasks
- Track recurring daily routines that reset each local calendar day
- Run one active focus timer on a dedicated, simplified Focus page and link it to a task
- Edit or delete timeline entries for completed tasks, routines, and focus sessions
- Visualize 12 weeks of completed work in a GitHub-style activity tracker
- Configure timezone-aware reminders, daily digests, and weekly summaries
- Sign in with a password, GitHub, or Google while retaining signed, HttpOnly application sessions
- Switch between responsive light and dark themes
- Distribute background jobs through Kafka with retries and dead-letter handling

## Architecture

```mermaid
flowchart TB
    User([User]) --> Web[Web interface]
    Web --> API[FastAPI]
    OAuth[GitHub / Google] --> API
    API --> DB[(PostgreSQL)]
    DB --> Scheduler[Scheduler]
    Scheduler --> Kafka[Kafka]
    Kafka --> Worker[Workers]
    Worker --> Email[Email delivery]
    Email --> User
```

FastAPI handles synchronous user requests, PostgreSQL is the source of truth, the scheduler detects due work, Kafka distributes it, and workers execute reminders and summaries independently of the request path. See [ARCHITECTURE.md](ARCHITECTURE.md) for the detailed design.

## Software Engineering Skills Demonstrated

| Skill | How Pace demonstrates it |
|---|---|
| Backend engineering | Modular FastAPI routers, Pydantic validation, explicit response models, and RESTful CRUD semantics |
| Database engineering | SQLAlchemy 2.x models, PostgreSQL constraints, UTC `TIMESTAMPTZ` data, and versioned Alembic migrations |
| Security engineering | Salted `scrypt` password hashing, verified-email OAuth linking, CSRF state validation, signed expiring sessions, HttpOnly and SameSite cookies, and environment-managed secrets |
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
  api/                 Task, routine, focus, preference, and job endpoints
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

Set PostgreSQL and session values in `.env`:

```env
DATABASE_URL=postgresql+psycopg://dayflow_app:your_password@localhost:5433/dayflow
SESSION_SECRET=generate_a_long_random_value
COOKIE_SECURE=false
OAUTH_BASE_URL=http://127.0.0.1:8000
GITHUB_CLIENT_ID=
GITHUB_CLIENT_SECRET=
GOOGLE_CLIENT_ID=
GOOGLE_CLIENT_SECRET=
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
| `POST` | `/auth/signup` | Create the single owner account on first use |
| `POST` | `/auth/login` | Start an authenticated session |
| `POST` | `/auth/logout` | End the current session |
| `GET` | `/auth/me` | Read the authenticated identity |
| `GET` | `/auth/oauth/{provider}` | Start GitHub or Google OAuth |
| `GET` | `/auth/oauth/{provider}/callback` | Verify OAuth identity and start a signed session |
| `POST`, `GET` | `/tasks` | Create and list scheduled tasks |
| `GET`, `PATCH`, `DELETE` | `/tasks/{id}` | Retrieve, update, complete, or delete a task |
| `GET`, `PATCH` | `/preferences` | Read or update application preferences |
| `GET` | `/jobs`, `/jobs/{job_id}` | Inspect background-job state |
| `GET`, `POST` | `/daily-tasks` | List or create recurring routines |
| `PUT` | `/daily-tasks/{id}/today` | Set today's routine completion |
| `DELETE` | `/daily-tasks/{id}` | Delete a recurring routine |
| `POST` | `/focus-sessions/start` | Start the focus timer |
| `POST` | `/focus-sessions/{id}/stop` | Stop and persist elapsed time |
| `GET` | `/focus-sessions` | List focus-session history |
| `GET` | `/focus-sessions/active` | Read the active focus session |
| `GET` | `/activities/today` | List today's editable accomplishments |
| `PATCH`, `DELETE` | `/activities/{id}` | Edit or remove a timeline entry |

All application endpoints except sign-up and login are protected by the session cookie. API timestamps must include an offset; PostgreSQL stores them as timezone-aware UTC values.

## Deploy to Render

[![Deploy to Render](https://render.com/images/deploy-to-render-button.svg)](https://render.com/deploy?repo=https://github.com/rajeev8008/Dayflow)

The Blueprint provisions the FastAPI web service and PostgreSQL database, runs migrations at startup, and generates `SESSION_SECRET`. Create the private owner account from the sign-up option on first use. After creation, Render provides the public `onrender.com` URL.

The web application, authentication, tasks, routines, preferences, and tracker run in this deployment. Scheduled email delivery additionally requires a reachable Kafka broker, SMTP secrets, and separate scheduler and worker processes; those are intentionally not provisioned by the free web Blueprint.

## Verification

```powershell
& ".\.venv\Scripts\python.exe" -m compileall -q app messaging scheduler worker tests
& ".\.venv\Scripts\python.exe" -m tests.test_phase1
& ".\.venv\Scripts\python.exe" -m tests.test_preferences
& ".\.venv\Scripts\python.exe" -m tests.test_background
& ".\.venv\Scripts\python.exe" -m tests.test_daily_tasks
& ".\.venv\Scripts\python.exe" -m tests.test_auth
& ".\.venv\Scripts\python.exe" -m tests.test_focus_sessions
& ".\.venv\Scripts\python.exe" -m tests.test_activities
& ".\.venv\Scripts\python.exe" -m tests.test_oauth
& ".\.venv\Scripts\alembic.exe" check
```

## Author

Developed by **K Rajeev**.

## License

Pace is available under the [MIT License](LICENSE).
