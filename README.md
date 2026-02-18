# DevTrack - Developer Activity Analytics

AI-powered GitHub activity tracker that analyzes your commits and generates intelligent weekly summaries using Claude API.

## Features

- 🔄 **GitHub Integration** - Automatically syncs repositories and commits
- 🤖 **AI Summaries** - Claude-powered analysis of your development patterns
- 📊 **Analytics** - Detailed statistics on languages, commits, and productivity
- 💾 **PostgreSQL Storage** - Efficient data persistence with caching
- 🚀 **REST API** - Clean FastAPI endpoints for all operations

## Tech Stack

- **Backend:** FastAPI, Python 3.10+
- **Database:** PostgreSQL
- **AI:** Anthropic Claude API
- **APIs:** GitHub REST API

## Setup

### Prerequisites
- Python 3.10+
- PostgreSQL
- GitHub Personal Access Token
- Anthropic API Key

### Installation

1. Clone the repository:
```bash
git clone https://github.com/mfaisalnoorzad-a11y/devtrack.git
cd devtrack
```

2. Create virtual environment:
```bash
python3 -m venv venv
source venv/bin/activate
```

3. Install dependencies:
```bash
pip install -r requirements.txt
```

4. Set up environment variables (create `.env`):
```env
GITHUB_TOKEN=your_github_token
GITHUB_USERNAME=your_username
ANTHROPIC_API_KEY=your_anthropic_key
DATABASE_URL=postgresql://user:pass@localhost:5432/devtrack_db
```

5. Set up PostgreSQL database:
```bash
psql -U postgres
CREATE DATABASE devtrack_db;
CREATE USER devtrack_user WITH PASSWORD 'your_password';
GRANT ALL PRIVILEGES ON DATABASE devtrack_db TO devtrack_user;
\q
```

6. Run migrations:
```bash
psql -U devtrack_user -d devtrack_db -h localhost -f migrations/001_initial_schema.sql
```

7. Run the application:
```bash
uvicorn src.main:app --reload
```

## API Endpoints

### `POST /sync`
Sync GitHub repositories and commits to database.

**Response:**
```json
{
  "username": "mfaisalnoorzad-a11y",
  "repositories_synced": 2,
  "commits_synced": 10,
  "last_synced": "2026-02-18T..."
}
```

### `GET /summary?timeframe=week|month`
Generate AI-powered summary of commits.

**Response:**
```json
{
  "timeframe": "week",
  "commit_count": 10,
  "summary": "You worked on two projects...",
  "generated_at": "2026-02-18T...",
  "cached": false
}
```

### `GET /stats`
Get detailed development statistics.

**Response:**
```json
{
  "username": "mfaisalnoorzad-a11y",
  "repositories": 2,
  "total_commits": 10,
  "languages": {"Python": 2},
  "total_lines_added": 1633,
  "total_lines_deleted": 56,
  "net_lines": 1577
}
```

### `GET /commits?limit=10&repo=RepoName`
Get recent commits with optional filtering.

## Usage Example
```bash
# Sync your GitHub data
curl -X POST http://localhost:8000/sync

# Get weekly summary
curl "http://localhost:8000/summary?timeframe=week"

# View statistics
curl http://localhost:8000/stats

# Get recent commits
curl http://localhost:8000/commits?limit=5
```

## Project Structure
```
devtrack/
├── src/
│   ├── main.py           # FastAPI application and routes
│   ├── models.py         # SQLAlchemy database models
│   ├── database.py       # Database connection setup
│   ├── github_client.py  # GitHub API integration
│   ├── services.py       # Business logic (sync service)
│   └── ai_service.py     # Anthropic AI integration
├── migrations/
│   └── 001_initial_schema.sql
├── requirements.txt
└── README.md
```

## Future Enhancements

- [ ] Docker containerization
- [ ] CI/CD pipeline with GitHub Actions
- [ ] Frontend dashboard with React
- [ ] AWS deployment (EC2 + RDS)
- [ ] Webhook support for real-time syncing

## License

MIT

## Author

Mohammad Faisal Noorzad - [GitHub](https://github.com/mfaisalnoorzad-a11y)