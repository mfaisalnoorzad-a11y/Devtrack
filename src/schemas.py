"""
Pydantic response models for DevTrack API.
Defines the structure and validation for all API responses.
"""

from pydantic import BaseModel, Field, field_validator
from typing import Optional, List, Dict
from datetime import datetime


class SyncResponse(BaseModel):
    """Response from POST /sync endpoint after syncing GitHub data."""
    
    username: str = Field(..., description="GitHub username that was synced")
    repositories_synced: int = Field(..., ge=0, description="Number of new repositories added")
    commits_synced: int = Field(..., ge=0, description="Number of new commits added")
    last_synced: str = Field(..., description="ISO 8601 timestamp of last sync")
    
    class Config:
        json_schema_extra = {
            "example": {
                "username": "mfaisalnoorzad-a11y",
                "repositories_synced": 2,
                "commits_synced": 15,
                "last_synced": "2026-02-18T12:21:07.843605-05:00"
            }
        }


class StatsResponse(BaseModel):
    """Response from GET /stats endpoint showing user statistics."""
    
    username: str = Field(..., description="GitHub username")
    repositories: int = Field(..., ge=0, description="Total number of repositories")
    total_commits: int = Field(..., ge=0, description="Total number of commits")
    languages: Dict[str, int] = Field(..., description="Programming languages and their repository count")
    total_lines_added: int = Field(..., ge=0, description="Total lines of code added")
    total_lines_deleted: int = Field(..., ge=0, description="Total lines of code deleted")
    total_files_changed: int = Field(..., ge=0, description="Total files modified")
    net_lines: int = Field(..., description="Net lines added (additions - deletions)")
    last_synced: Optional[str] = Field(None, description="ISO 8601 timestamp of last sync")
    
    class Config:
        json_schema_extra = {
            "example": {
                "username": "mfaisalnoorzad-a11y",
                "repositories": 4,
                "total_commits": 27,
                "languages": {"Python": 3, "JavaScript": 1},
                "total_lines_added": 2593,
                "total_lines_deleted": 91,
                "total_files_changed": 85,
                "net_lines": 2502,
                "last_synced": "2026-02-18T12:21:07.843605-05:00"
            }
        }


class CommitItem(BaseModel):
    """Individual commit information."""
    
    sha: str = Field(..., min_length=7, max_length=7, description="Short commit SHA (7 characters)")
    repository: str = Field(..., description="Repository name")
    message: str = Field(..., description="Commit message (first line)")
    date: str = Field(..., description="ISO 8601 commit timestamp")
    files_changed: int = Field(..., ge=0, description="Number of files modified")
    additions: int = Field(..., ge=0, description="Lines added")
    deletions: int = Field(..., ge=0, description="Lines deleted")
    
    class Config:
        json_schema_extra = {
            "example": {
                "sha": "f113db2",
                "repository": "devtrack",
                "message": "Add AI summarization feature",
                "date": "2026-02-18T15:20:21-05:00",
                "files_changed": 3,
                "additions": 127,
                "deletions": 5
            }
        }


class CommitsResponse(BaseModel):
    """Response from GET /commits endpoint."""
    
    commits: List[CommitItem] = Field(..., description="List of recent commits")
    count: int = Field(..., ge=0, description="Number of commits returned")
    
    class Config:
        json_schema_extra = {
            "example": {
                "commits": [
                    {
                        "sha": "f113db2",
                        "repository": "devtrack",
                        "message": "Add AI summarization feature",
                        "date": "2026-02-18T15:20:21-05:00",
                        "files_changed": 3,
                        "additions": 127,
                        "deletions": 5
                    }
                ],
                "count": 1
            }
        }


class SummaryResponse(BaseModel):
    """Response from GET /summary endpoint with AI-generated summary."""
    
    timeframe: str = Field(..., pattern="^(week|month)$", description="Time period: 'week' or 'month'")
    commit_count: int = Field(..., ge=0, description="Number of commits in this timeframe")
    summary: str = Field(..., description="AI-generated summary of activity")
    generated_at: str = Field(..., description="ISO 8601 timestamp when summary was created")
    cached: bool = Field(..., description="Whether this summary was retrieved from cache")
    
    @field_validator('timeframe')
    @classmethod
    def validate_timeframe(cls, v: str) -> str:
        if v not in ['week', 'month']:
            raise ValueError("timeframe must be 'week' or 'month'")
        return v
    
    class Config:
        json_schema_extra = {
            "example": {
                "timeframe": "week",
                "commit_count": 15,
                "summary": "This week you focused on building the DevTrack backend...",
                "generated_at": "2026-02-18T16:00:00-05:00",
                "cached": False
            }
        }


class HealthResponse(BaseModel):
    """Response from GET /health endpoint."""
    
    status: str = Field(..., description="Service health status")
    
    class Config:
        json_schema_extra = {
            "example": {
                "status": "healthy"
            }
        }