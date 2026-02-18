"""
SQLAlchemy database models for DevTrack.
Defines the schema for users, repositories, commits, and AI-generated summaries.
"""

from sqlalchemy import Column, Integer, String, Text, DateTime, Date, ForeignKey, CheckConstraint, Index
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from src.database import Base


class User(Base):
    """
    Represents a GitHub user whose activity is being tracked.
    
    Attributes:
        id: Primary key
        github_username: GitHub username (unique)
        github_token: GitHub API token (stored for authentication)
        created_at: When this user was added to DevTrack
        last_synced_at: Last time GitHub data was synced
    """
    __tablename__ = "users"
    
    id = Column(Integer, primary_key=True, index=True)
    github_username = Column(String, unique=True, nullable=False, index=True)
    github_token = Column(String, nullable=False)  # TODO: Encrypt at rest
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    last_synced_at = Column(DateTime(timezone=True), nullable=True)
    
    # Relationships
    repositories = relationship("Repository", back_populates="user", cascade="all, delete-orphan")
    summaries = relationship("Summary", back_populates="user", cascade="all, delete-orphan")
    
    def __repr__(self):
        return f"<User(username='{self.github_username}', last_synced={self.last_synced_at})>"


class Repository(Base):
    """
    Represents a GitHub repository owned by a tracked user.
    
    Attributes:
        id: Primary key
        user_id: Foreign key to users table
        repo_name: Repository name (e.g., 'devtrack')
        repo_url: Full GitHub URL
        language: Primary programming language
        created_at: When this repo was added to DevTrack
    """
    __tablename__ = "repositories"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey('users.id', ondelete='CASCADE'), nullable=False, index=True)
    repo_name = Column(String, nullable=False)
    repo_url = Column(String, nullable=False)
    language = Column(String, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    # Relationships
    user = relationship("User", back_populates="repositories")
    commits = relationship("Commit", back_populates="repository", cascade="all, delete-orphan")
    
    def __repr__(self):
        return f"<Repository(name='{self.repo_name}', language='{self.language}')>"


class Commit(Base):
    """
    Represents a single Git commit in a repository.
    
    Attributes:
        id: Primary key
        repository_id: Foreign key to repositories table
        commit_sha: Git commit SHA (unique identifier)
        message: Commit message
        author_date: When the commit was authored
        files_changed: Number of files modified
        additions: Lines of code added
        deletions: Lines of code deleted
        created_at: When this commit was added to DevTrack
    """
    __tablename__ = "commits"
    
    id = Column(Integer, primary_key=True, index=True)
    repository_id = Column(Integer, ForeignKey('repositories.id', ondelete='CASCADE'), nullable=False, index=True)
    commit_sha = Column(String, unique=True, nullable=False, index=True)
    message = Column(Text, nullable=False)
    author_date = Column(DateTime(timezone=True), nullable=False, index=True)  # Indexed for date range queries
    files_changed = Column(Integer, default=0)
    additions = Column(Integer, default=0)
    deletions = Column(Integer, default=0)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    # Relationships
    repository = relationship("Repository", back_populates="commits")
    
    def __repr__(self):
        return f"<Commit(sha='{self.commit_sha[:7]}', repo='{self.repository.repo_name if self.repository else 'N/A'}')>"


class Summary(Base):
    """
    Represents an AI-generated summary of commit activity.
    
    Attributes:
        id: Primary key
        user_id: Foreign key to users table
        timeframe: 'week' or 'month'
        start_date: Start of the summary period
        end_date: End of the summary period
        summary_text: AI-generated summary content
        generated_at: When the summary was created
    """
    __tablename__ = "summaries"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey('users.id', ondelete='CASCADE'), nullable=False, index=True)
    timeframe = Column(String, nullable=False, index=True)  # Indexed for cache lookups
    start_date = Column(Date, nullable=False)
    end_date = Column(Date, nullable=False)
    summary_text = Column(Text, nullable=False)
    generated_at = Column(DateTime(timezone=True), server_default=func.now())
    
    # Relationships
    user = relationship("User", back_populates="summaries")
    
    # Constraints
    __table_args__ = (
        CheckConstraint("timeframe IN ('week', 'month')", name='check_timeframe'),
        Index('idx_summary_lookup', 'user_id', 'timeframe', 'start_date', 'end_date'),  # Composite index for cache queries
    )
    
    def __repr__(self):
        return f"<Summary(timeframe='{self.timeframe}', period={self.start_date} to {self.end_date})>"