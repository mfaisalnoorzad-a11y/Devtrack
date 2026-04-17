# DevTrack

AI-powered GitHub activity analytics backend built with FastAPI, SQLAlchemy, PostgreSQL, and Anthropic.

DevTrack syncs your repositories and commits into PostgreSQL, exposes an API for developer analytics, and generates weekly or monthly summaries of your coding activity. This version is polished as a backend portfolio project and prepared for an initial deployment.

[![Python](https://img.shields.io/badge/Python-3.10+-blue.svg)](https://python.org)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.109-green.svg)](https://fastapi.tiangolo.com)
[![PostgreSQL](https://img.shields.io/badge/PostgreSQL-16-blue.svg)](https://postgresql.org)

## Live Demo

- API Root: https://devtrack-production-99e3.up.railway.app/
- API Docs: https://devtrack-production-99e3.up.railway.app/docs
- Health Check: https://devtrack-production-99e3.up.railway.app/health

## What It Does

- Syncs your GitHub repositories and commits into PostgreSQL
- Filters imported commits to your GitHub username
- Provides API endpoints for sync, stats, summaries, recent commits, and health checks
- Generates cached AI summaries from synced commit history
- Supports optional API-key protection for sensitive routes

## Screenshots

### API Documentation

![DevTrack API Docs](assets/devtrack-api-docs.png)

### AI Summary Response

![DevTrack AI Summary](assets/devtrack-ai-summary.png)

## Architecture

```text
GitHub API
    |
    v
GitHubClient -> GitHubSyncService -> PostgreSQL
                                   |
                                   v
                               FastAPI API
                                   |
                                   v
                               AIService
```

## Tech Stack

- Python 3.10+
- FastAPI
- SQLAlchemy 2.0
- PostgreSQL
- Pydantic
- requests
- Anthropic SDK
- pytest

## Project Structure

```text
devtrack/
|- migrations/
|  |- 001_initial_schema.sql
|- src/
|  |- ai_service.py
|  |- auth.py
|  |- config.py
|  |- database.py
|  |- github_client.py
|  |- main.py
|  |- models.py
|  |- schemas.py
|  |- services.py
|- tests/
|  |- conftest.py
|  |- test_api.py
|- .env.example
|- pytest.ini
|- requirements.txt
|- README.md
```

## Environment Variables

Copy `.env.example` to `.env` and fill in your values.

```env
GITHUB_TOKEN=your_github_pat
GITHUB_USERNAME=your_github_username
ANTHROPIC_API_KEY=your_anthropic_key
DATABASE_URL=postgresql://username:password@localhost:5432/devtrack_db
DEVTRACK_API_KEY=optional_api_key_for_protected_routes
```

### Notes

- `DEVTRACK_API_KEY` is optional. If you set it, protected routes require either `Authorization: Bearer <key>` or `X-API-Key: <key>`.
- Keep `.env` private. Never commit real secrets.

## Local Setup

1. Clone the repository.

```bash
git clone https://github.com/mfaisalnoorzad-a11y/devtrack.git
cd devtrack
```

2. Create and activate a virtual environment.

```bash
python -m venv venv
```

Windows PowerShell:

```powershell
.\venv\Scripts\Activate.ps1
```

macOS / Linux:

```bash
source venv/bin/activate
```

3. Install dependencies.

```bash
pip install -r requirements.txt
```

4. Create `.env` from `.env.example` and fill in real credentials.

5. Create the PostgreSQL database and run the schema migration.

```bash
psql -U postgres
CREATE DATABASE devtrack_db;
\q
psql -U postgres -d devtrack_db -f migrations/001_initial_schema.sql
```

6. Start the development server.

```bash
uvicorn src.main:app --reload
```

7. Open the interactive docs at [http://localhost:8000/docs](http://localhost:8000/docs).

## API Overview

### `GET /health`

Public health check for local verification and deployment platforms.

### `POST /sync`

Protected route that pulls repositories and commits from GitHub and stores them locally.

```bash
curl -X POST http://localhost:8000/sync \
  -H "X-API-Key: your_api_key"
```

### `GET /stats`

Protected route that returns repository counts, commit counts, language breakdown, and aggregate line and file metrics.

### `GET /summary?timeframe=week`

Protected route that returns a cached or freshly generated AI summary for the requested timeframe.

### `GET /commits?limit=10&repo=devtrack`

Protected route that returns recent commits, optionally filtered by repository.

## Testing

Run the test suite with:

```bash
python -m pytest -q
```

The tests use SQLite in memory so they stay fast and do not depend on your PostgreSQL instance.

## Deployment Notes

For Railway, configure these environment variables:

- `DATABASE_URL`
- `GITHUB_TOKEN`
- `GITHUB_USERNAME`
- `ANTHROPIC_API_KEY`
- `DEVTRACK_API_KEY`

Recommended start command:

```bash
gunicorn -k uvicorn.workers.UvicornWorker src.main:app
```

## Portfolio Highlights

This project demonstrates:

- backend API design with FastAPI
- relational schema design with SQLAlchemy and PostgreSQL
- external API integration with pagination and retries
- AI-powered summarization over real developer activity data
- incremental sync logic and cached summaries
- deployment-focused hardening such as config centralization, optional auth, and tests

## Author

Mohammad Faisal Noorzad

- GitHub: [@mfaisalnoorzad-a11y](https://github.com/mfaisalnoorzad-a11y)
- LinkedIn: [Mohammad Faisal Noorzad](https://linkedin.com/in/mohammad-faisal-noorzad-26561831b)
