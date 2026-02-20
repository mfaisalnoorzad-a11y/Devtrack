"""
DevTrack API - Main FastAPI application.
Provides endpoints for syncing GitHub data and generating AI-powered analytics.
"""

from fastapi import FastAPI, Depends, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session
from dotenv import load_dotenv
from typing import Optional
import os

from src.database import get_db
from src import models, schemas
from src.services import GitHubSyncService
from datetime import datetime, timedelta, timezone
from src.ai_service import AIService

load_dotenv()

# Initialize FastAPI app
app = FastAPI(
    title="DevTrack API",
    description="AI-powered GitHub activity analytics and insights",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc"
)

# CORS middleware (if you add a frontend later)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure appropriately for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Dependency: Get current user
def get_current_user(db: Session = Depends(get_db)) -> models.User:
    """
    Dependency to get the current authenticated user.
    
    Returns:
        User model instance
        
    Raises:
        HTTPException: If user not found (needs to sync first)
    """
    username = os.getenv("GITHUB_USERNAME")
    if not username:
        raise HTTPException(
            status_code=500,
            detail="GITHUB_USERNAME not configured. Check server environment."
        )
    
    user = db.query(models.User).filter(
        models.User.github_username == username
    ).first()
    
    if not user:
        raise HTTPException(
            status_code=404,
            detail="User not synced yet. Call POST /sync first to initialize."
        )
    
    return user


@app.get("/", tags=["General"])
def root():
    """
    API root endpoint with service information.
    
    Returns basic information about the API and available endpoints.
    """
    return {
        "service": "DevTrack API",
        "version": "1.0.0",
        "status": "operational",
        "documentation": "/docs",
        "endpoints": {
            "sync": "POST /sync - Sync GitHub data",
            "stats": "GET /stats - Get user statistics",
            "summary": "GET /summary?timeframe=week - Get AI summary",
            "commits": "GET /commits?limit=10 - Get recent commits",
            "health": "GET /health - Health check"
        }
    }


@app.post("/sync", response_model=schemas.SyncResponse, tags=["GitHub Sync"])
def sync_github_data(db: Session = Depends(get_db)):
    """
    Sync GitHub repositories and commits to database.
    
    Performs incremental sync:
    - Fetches new repositories
    - Fetches commits created since last sync
    - Only includes commits authored by the tracked user
    
    Returns:
        SyncResponse with counts of synced items
    """
    try:
        service = GitHubSyncService(db)
        result = service.sync_user_data()
        return result
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except RuntimeError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(
            status_code=500,
            detail=f"Unexpected sync error: {exc}"
        ) from exc


@app.get("/stats", response_model=schemas.StatsResponse, tags=["Analytics"])
def get_stats(
    user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Get comprehensive user statistics.
    
    Includes:
    - Repository and commit counts
    - Programming language breakdown
    - Total lines added/deleted
    - Net contribution
    
    Returns:
        StatsResponse with all statistics
    """
    # Basic counts
    repo_count = db.query(models.Repository).filter(
        models.Repository.user_id == user.id
    ).count()
    
    commit_count = db.query(models.Commit).join(models.Repository).filter(
        models.Repository.user_id == user.id
    ).count()
    
    # Language breakdown
    repos = db.query(models.Repository).filter(
        models.Repository.user_id == user.id
    ).all()
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
        "username": user.github_username,
        "repositories": repo_count,
        "total_commits": commit_count,
        "languages": languages,
        "total_lines_added": total_additions,
        "total_lines_deleted": total_deletions,
        "total_files_changed": total_files,
        "net_lines": total_additions - total_deletions,
        "last_synced": user.last_synced_at.isoformat() if user.last_synced_at else None
    }


@app.get("/summary", response_model=schemas.SummaryResponse, tags=["AI Analytics"])
def get_summary(
    timeframe: str = "week",
    user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Get AI-generated summary of commit activity.
    
    Uses Claude to analyze commit patterns and generate natural language
    summaries of development work.
    
    Args:
        timeframe: Either 'week' (last 7 days) or 'month' (last 30 days)
    
    Returns:
        SummaryResponse with AI-generated insights
    """
    if timeframe not in ["week", "month"]:
        raise HTTPException(
            status_code=400,
            detail="timeframe must be 'week' or 'month'"
        )

    # Calculate date range
    now = datetime.now(timezone.utc)
    days = 7 if timeframe == "week" else 30
    start_date = now - timedelta(days=days)
    start_day = start_date.date()
    end_day = now.date()

    # Check for cached summary
    existing_summary = db.query(models.Summary).filter(
        models.Summary.user_id == user.id,
        models.Summary.timeframe == timeframe,
        models.Summary.start_date == start_day,
        models.Summary.end_date == end_day
    ).order_by(models.Summary.generated_at.desc()).first()
    
    if existing_summary:
        # Return cached summary with recalculated commit count
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

    # Generate AI summary
    try:
        ai_service = AIService()
        summary_text = ai_service.generate_summary(commit_data, timeframe)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except RuntimeError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(
            status_code=500,
            detail=f"Unexpected summary error: {exc}"
        ) from exc

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


@app.get("/commits", response_model=schemas.CommitsResponse, tags=["Analytics"])
def get_commits(
    limit: int = 10,
    repo: Optional[str] = None,
    user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Get recent commits with optional filtering.
    
    Args:
        limit: Number of commits to return (max 50)
        repo: Filter by repository name (optional)
    
    Returns:
        CommitsResponse with list of commits
    """
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


@app.get("/health", response_model=schemas.HealthResponse, tags=["General"])
def health():
    """
    Health check endpoint.
    
    Returns service health status for monitoring/load balancers.
    """
    return {"status": "healthy"}