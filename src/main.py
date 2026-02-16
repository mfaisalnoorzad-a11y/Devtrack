from fastapi import FastAPI, Depends
from sqlalchemy.orm import Session
from dotenv import load_dotenv
import os

from src.database import engine, get_db, Base
from src import models
from src.services import GitHubSyncService

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
    service = GitHubSyncService(db)
    result = service.sync_user_data()
    return result

@app.get("/stats")
def get_stats(db: Session = Depends(get_db)):
    """Get user statistics"""
    username = os.getenv("GITHUB_USERNAME")
    user = db.query(models.User).filter(models.User.github_username == username).first()
    
    if not user:
        return {"error": "User not synced yet. Call /sync first"}
    
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