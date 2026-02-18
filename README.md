# DevTrack 🚀

> AI-powered GitHub activity analytics with intelligent weekly summaries

Track your development activity, analyze commit patterns, and get AI-generated insights about your coding journey using Claude.

[![Python](https://img.shields.io/badge/Python-3.10+-blue.svg)](https://python.org)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.109-green.svg)](https://fastapi.tiangolo.com)
[![PostgreSQL](https://img.shields.io/badge/PostgreSQL-16-blue.svg)](https://postgresql.org)

## ✨ Features

- 🔄 **Automated GitHub Sync** - Incremental syncing with smart pagination
- 🤖 **AI-Powered Summaries** - Claude analyzes your commits and generates insights
- 📊 **Developer Analytics** - Track languages, productivity metrics, and patterns
- ⚡ **Smart Caching** - Reduces API costs by caching generated summaries
- 🎯 **Author Filtering** - Only tracks YOUR commits (perfect for team repos)
- 🔒 **Type-Safe API** - Pydantic models for validated responses

## 🏗️ Architecture
```
┌─────────────┐
│   GitHub    │
│     API     │
└──────┬──────┘
       │
       │ Fetch repos & commits
       ▼
┌─────────────────────────────┐
│      FastAPI Backend        │
│  ┌─────────────────────┐   │
│  │  GitHub Client      │   │
│  │  - Pagination       │   │
│  │  - Auth filtering   │   │
│  └──────────┬──────────┘   │
│             │               │
│  ┌──────────▼──────────┐   │
│  │   Sync Service      │   │
│  │  - Incremental sync │   │
│  │  - Deduplication    │   │
│  └──────────┬──────────┘   │
│             │               │
│  ┌──────────▼──────────┐   │
│  │   PostgreSQL DB     │   │
│  │  - Users            │   │
│  │  - Repositories     │   │
│  │  - Commits          │   │
│  │  - Summaries        │   │
│  └──────────┬──────────┘   │
│             │               │
│  ┌──────────▼──────────┐   │
│  │   AI Service        │───┼──► Anthropic
│  │  - Prompt building  │   │    Claude API
│  │  - Cache check      │   │
│  └─────────────────────┘   │
└─────────────────────────────┘
       │
       │ REST API
       ▼
┌─────────────┐
│   Client    │
└─────────────┘
```

## 🚀 Quick Start

### Prerequisites
- Python 3.10+
- PostgreSQL 16+
- GitHub Personal Access Token ([create one](https://github.com/settings/tokens))
- Anthropic API Key ([get free credits](https://console.anthropic.com))

### Installation

1. **Clone the repository**
```bash
git clone https://github.com/mfaisalnoorzad-a11y/devtrack.git
cd devtrack
```

2. **Set up virtual environment**
```bash
python3 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

3. **Install dependencies**
```bash
pip install -r requirements.txt
```

4. **Configure environment**
```bash
cp .env.example .env
# Edit .env with your actual credentials
```

5. **Set up PostgreSQL**
```bash
# Create database and user
psql -U postgres
CREATE DATABASE devtrack_db;
CREATE USER devtrack_user WITH PASSWORD 'your_password';
GRANT ALL PRIVILEGES ON DATABASE devtrack_db TO devtrack_user;
GRANT ALL ON SCHEMA public TO devtrack_user;
\q

# Run migrations
psql -U devtrack_user -d devtrack_db -h localhost -f migrations/001_initial_schema.sql
```

6. **Start the server**
```bash
uvicorn src.main:app --reload
```

Visit `http://localhost:8000/docs` for interactive API documentation.

## 📡 API Endpoints

### Sync GitHub Data
```bash
curl -X POST http://localhost:8000/sync
```
**Response:**
```json
{
  "username": "mfaisalnoorzad-a11y",
  "repositories_synced": 2,
  "commits_synced": 10,
  "last_synced": "2026-02-18T..."
}
```

### Get AI Summary
```bash
curl "http://localhost:8000/summary?timeframe=week"
```
**Response:**
```json
{
  "timeframe": "week",
  "commit_count": 15,
  "summary": "This week you focused on...",
  "cached": false
}
```

### Get Statistics
```bash
curl http://localhost:8000/stats
```

### Get Recent Commits
```bash
curl "http://localhost:8000/commits?limit=10&repo=YourRepo"
```

## 🎯 Key Features Explained

### Incremental Sync
Only fetches commits created since the last sync, dramatically reducing API calls:
```python
# First sync: fetches all commits
# Subsequent syncs: only new commits since last_synced_at
```

### Author Filtering
Filters commits to only include yours, perfect for collaborative repos:
```python
github_client.get_commits(repo, author=username)
```

### Smart Caching
Summaries are cached by timeframe and date range to minimize AI API costs:
```python
# Same day + timeframe = returns cached summary
# Different day = generates new summary
```

## 📁 Project Structure
```
devtrack/
├── src/
│   ├── main.py           # FastAPI app + route handlers
│   ├── models.py         # SQLAlchemy database models
│   ├── schemas.py        # Pydantic response models
│   ├── database.py       # DB connection & session management
│   ├── github_client.py  # GitHub API wrapper
│   ├── services.py       # Business logic (sync operations)
│   └── ai_service.py     # Anthropic Claude integration
├── migrations/
│   └── 001_initial_schema.sql
├── .env.example          # Environment template
├── requirements.txt      # Python dependencies
└── README.md
```

## 🔧 Tech Stack Details

| Component | Technology | Why |
|-----------|-----------|-----|
| **API Framework** | FastAPI | Fast, automatic OpenAPI docs, type hints |
| **Database** | PostgreSQL | Relational data, ACID compliance, JSON support |
| **ORM** | SQLAlchemy 2.0 | Type-safe queries, relationship management |
| **AI** | Anthropic Claude | Superior summarization, fast, affordable |
| **Validation** | Pydantic | Type-safe request/response models |

## 🎓 What I Learned

- **RESTful API Design:** Built clean endpoints with proper HTTP semantics
- **Database Modeling:** Normalized schema with foreign keys and constraints
- **External API Integration:** Handled pagination, rate limits, authentication
- **Caching Strategies:** Reduced costs by caching expensive AI operations
- **Incremental Sync:** Optimized data fetching for large datasets
- **Type Safety:** Used Pydantic for runtime validation

## 🚧 Future Enhancements

- [ ] Docker containerization
- [ ] CI/CD pipeline with GitHub Actions  
- [ ] AWS deployment (EC2 + RDS)
- [ ] React dashboard frontend
- [ ] GitHub webhooks for real-time sync
- [ ] Multi-user support with authentication
- [ ] Commit streak tracking
- [ ] Language trend analysis over time

## 📝 License

MIT License - see LICENSE file for details

## 👤 Author

**Mohammad Faisal Noorzad**
- GitHub: [@mfaisalnoorzad-a11y](https://github.com/mfaisalnoorzad-a11y)
- LinkedIn: [Mohammad Faisal Noorzad](https://linkedin.com/in/mohammad-faisal-noorzad-26561831b)