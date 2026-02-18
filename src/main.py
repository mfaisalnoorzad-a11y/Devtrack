from fastapi import FastAPI, Depends, HTTPException
from sqlalchemy.orm import Session
from dotenv import load_dotenv
from typing import Optional
import os

from src.database import engine, get_db, Base
from src import models, schemas
from src.services import GitHubSyncService

from datetime import datetime, timedelta, timezone
from src.ai_service import AIService

load_dotenv()

# Create all tables
Base.metadata.create_all(bind=engine)

app = FastAPI(title="DevTrack API")

@app.get("/")
def root():
    return {
        "message": "DevTrack API is running",
        "endpoints": {
            "sync": "/sync",
            "stats": "/stats",
            "health": "/health"
        }
    }

@app.post("/sync", response_model=schemas.SyncResponse)
def sync_github_data(db: Session = Depends(get_db)):
    """Sync GitHub data for the user"""
    try:
        service = GitHubSyncService(db)
        result = service.sync_user_data()
        return result
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except RuntimeError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Unexpected sync error: {exc}") from exc

@app.get("/stats", response_model=schemas.StatsResponse)
def get_stats(db: Session = Depends(get_db)):
    """Get detailed user statistics"""
    username = os.getenv("GITHUB_USERNAME")
    user = db.query(models.User).filter(models.User.github_username == username).first()
    
    if not user:
        raise HTTPException(status_code=404, detail="User not synced yet. Call POST /sync first")
    
    # Basic counts
    repo_count = db.query(models.Repository).filter(models.Repository.user_id == user.id).count()
    commit_count = db.query(models.Commit).join(models.Repository).filter(
        models.Repository.user_id == user.id
    ).count()
    
    # Language breakdown
    repos = db.query(models.Repository).filter(models.Repository.user_id == user.id).all()
    languages = {}
    for repo in repos:
        if repo.language:
            languages[repo.language] = languages.get(repo.language, 0) + 1
    
    # Total lines changed
    commits = db.query(models.Commit).join(models.Repository).filter(
        models.Repository.user_id == user.id
    ).all()
    
    total_additions = sum(c.additions for c in commits)
    total_deletions = sum(c.deletions for c in commits)
    total_files = sum(c.files_changed for c in commits)
    
    return {
        "username": username,
        "repositories": repo_count,
        "total_commits": commit_count,
        "languages": languages,
        "total_lines_added": total_additions,
        "total_lines_deleted": total_deletions,
        "total_files_changed": total_files,
        "net_lines": total_additions - total_deletions,
        "last_synced": user.last_synced_at.isoformat() if user.last_synced_at else None
    }

@app.get("/health", response_model=schemas.HealthResponse)
def health():
    return {"status": "healthy"}


@app.get("/summary", response_model=schemas.SummaryResponse)
def get_summary(timeframe: str = "week", db: Session = Depends(get_db)):
    """
    Get AI-generated summary of commits
    timeframe: 'week' or 'month'
    """
    if timeframe not in ["week", "month"]:
        raise HTTPException(status_code=400, detail="timeframe must be 'week' or 'month'")

    username = os.getenv("GITHUB_USERNAME")
    if not username:
        raise HTTPException(status_code=400, detail="GITHUB_USERNAME is not set.")
    user = db.query(models.User).filter(models.User.github_username == username).first()

    if not user:
        raise HTTPException(status_code=404, detail="User not synced yet. Call POST /sync first")

    # Calculate date range
    now = datetime.now(timezone.utc)
    if timeframe == "week":
        start_date = now - timedelta(days=7)
    else:  # month
        start_date = now - timedelta(days=30)

    start_day = start_date.date()
    end_day = now.date()

    existing_summary = db.query(models.Summary).filter(
        models.Summary.user_id == user.id,
        models.Summary.timeframe == timeframe,
        models.Summary.start_date == start_day,
        models.Summary.end_date == end_day
    ).order_by(models.Summary.generated_at.desc()).first()
    if existing_summary:
        # Recalculate commit count for the same date range
        cached_commit_count = db.query(models.Commit).join(models.Repository).filter(
            models.Repository.user_id == user.id,
            models.Commit.author_date >= start_date
        ).count()
        
        return {
            "timeframe": timeframe,
            "commit_count": cached_commit_count,
            "summary": existing_summary.summary_text,
            "generated_at": existing_summary.generated_at.isoformat(),
            "cached": True
        }

    # Fetch commits from date range
    commits = db.query(models.Commit).join(models.Repository).filter(
        models.Repository.user_id == user.id,
        models.Commit.author_date >= start_date
    ).all()

    # Format commits for AI
    commit_data = [
        {
            "repo_name": commit.repository.repo_name,
            "message": commit.message,
            "author_date": commit.author_date,
            "files_changed": commit.files_changed,
            "additions": commit.additions,
            "deletions": commit.deletions
        }
        for commit in commits
    ]

    try:
        # Generate AI summary
        ai_service = AIService()
        summary_text = ai_service.generate_summary(commit_data, timeframe)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except RuntimeError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Unexpected summary error: {exc}") from exc

    # Store summary in database
    new_summary = models.Summary(
        user_id=user.id,
        timeframe=timeframe,
        start_date=start_day,
        end_date=end_day,
        summary_text=summary_text
    )
    db.add(new_summary)
    db.commit()

    return {
        "timeframe": timeframe,
        "commit_count": len(commit_data),
        "summary": summary_text,
        "generated_at": now.isoformat(),
        "cached": False
    }

@app.get("/commits", response_model=schemas.CommitsResponse)
def get_commits(limit: int = 10, repo: Optional[str] = None, db: Session = Depends(get_db)):
    """
    Get recent commits
    limit: number of commits to return (default 10, max 50)
    repo: filter by repository name (optional)
    """
    username = os.getenv("GITHUB_USERNAME")
    user = db.query(models.User).filter(models.User.github_username == username).first()
    
    if not user:
        raise HTTPException(status_code=404, detail="User not synced yet. Call POST /sync first")
    
    limit = min(limit, 50)  # Cap at 50
    
    query = db.query(models.Commit).join(models.Repository).filter(
        models.Repository.user_id == user.id
    )
    
    if repo:
        query = query.filter(models.Repository.repo_name == repo)
    
    commits = query.order_by(models.Commit.author_date.desc()).limit(limit).all()
    
    return {
        "commits": [
            {
                "sha": c.commit_sha[:7],
                "repository": c.repository.repo_name,
                "message": c.message.split('\n')[0],  # First line only
                "date": c.author_date.isoformat(),
                "files_changed": c.files_changed,
                "additions": c.additions,
                "deletions": c.deletions
            }
            for c in commits
        ],
        "count": len(commits)
    }