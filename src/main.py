from fastapi import FastAPI, Depends, HTTPException
from sqlalchemy.orm import Session
from dotenv import load_dotenv
import os

from src.database import engine, get_db, Base
from src import models
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

@app.post("/sync")
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

@app.get("/stats")
def get_stats(db: Session = Depends(get_db)):
    """Get user statistics"""
    username = os.getenv("GITHUB_USERNAME")
    if not username:
        raise HTTPException(status_code=400, detail="GITHUB_USERNAME is not set.")
    user = db.query(models.User).filter(models.User.github_username == username).first()

    if not user:
        raise HTTPException(status_code=404, detail="User not synced yet. Call /sync first.")

    repo_count = db.query(models.Repository).filter(models.Repository.user_id == user.id).count()
    commit_count = db.query(models.Commit).join(models.Repository).filter(
        models.Repository.user_id == user.id
    ).count()
    
    return {
        "username": username,
        "repositories": repo_count,
        "total_commits": commit_count,
        "last_synced": user.last_synced_at.isoformat() if user.last_synced_at else None
    }

@app.get("/health")
def health():
    return {"status": "healthy"}


@app.get("/summary")
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
        raise HTTPException(status_code=404, detail="User not synced yet. Call /sync first.")

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
        return {
            "timeframe": timeframe,
            "commit_count": None,
            "summary": existing_summary.summary_text,
            "generated_at": existing_summary.generated_at.isoformat() if existing_summary.generated_at else None,
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