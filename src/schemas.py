from pydantic import BaseModel
from typing import Optional, List, Dict
from datetime import datetime


class SyncResponse(BaseModel):
    username: str
    repositories_synced: int
    commits_synced: int
    last_synced: str


class StatsResponse(BaseModel):
    username: str
    repositories: int
    total_commits: int
    languages: Dict[str, int]
    total_lines_added: int
    total_lines_deleted: int
    total_files_changed: int
    net_lines: int
    last_synced: Optional[str]


class CommitItem(BaseModel):
    sha: str
    repository: str
    message: str
    date: str
    files_changed: int
    additions: int
    deletions: int


class CommitsResponse(BaseModel):
    commits: List[CommitItem]
    count: int


class SummaryResponse(BaseModel):
    timeframe: str
    commit_count: Optional[int]
    summary: str
    generated_at: Optional[str]
    cached: bool


class HealthResponse(BaseModel):
    status: str
