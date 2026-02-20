"""
GitHub sync service for DevTrack.
Handles syncing repository and commit data from GitHub to PostgreSQL.
"""

from sqlalchemy.orm import Session
from src.models import User, Repository, Commit
from src.github_client import GitHubClient
from datetime import datetime, timezone
import os
import requests


class GitHubSyncService:
    """
    Service for syncing GitHub data to local database.
    
    Implements incremental sync to minimize API calls:
    - Only fetches new repositories
    - Only fetches commits created after last sync
    - Only fetches commits authored by the tracked user
    """
    
    def __init__(self, db: Session):
        """
        Initialize sync service.
        
        Args:
            db: SQLAlchemy database session
        """
        self.db = db
        self.github_client = GitHubClient()
    
    def sync_user_data(self) -> dict:
        """
        Sync all GitHub data for the authenticated user.
        
        Process:
        1. Get or create user record
        2. Sync all repositories (add new ones, update metadata)
        3. Sync commits incrementally (only new commits, only user's commits)
        4. Update last_synced_at timestamp
        
        Returns:
            Dictionary with sync results:
                - username: GitHub username
                - repositories_synced: Number of new repos added
                - commits_synced: Number of new commits added
                - last_synced: ISO 8601 timestamp
                
        Raises:
            ValueError: If required environment variables not set
            RuntimeError: If GitHub API requests fail
        """
        username = os.getenv("GITHUB_USERNAME")
        token = os.getenv("GITHUB_TOKEN")
        
        if not username:
            raise ValueError("GITHUB_USERNAME environment variable is required.")
        if not token:
            raise ValueError("GITHUB_TOKEN environment variable is required.")
        
        # Get or create user
        user = self.db.query(User).filter(User.github_username == username).first()
        if not user:
            user = User(
                github_username=username,
                github_token=self._mask_token(token)
            )
            self.db.add(user)
            self.db.commit()
            self.db.refresh(user)
        else:
            # Update masked token (in case it changed)
            user.github_token = self._mask_token(token)
            self.db.commit()
        
        # Sync repositories and commits
        try:
            repos_synced = self._sync_repositories(user)
            commits_synced = self._sync_commits(user)
        except requests.RequestException as exc:
            self.db.rollback()
            raise RuntimeError(f"GitHub API request failed: {exc}") from exc
        
        # Update last sync timestamp
        user.last_synced_at = datetime.now(timezone.utc)
        self.db.commit()
        
        return {
            "username": username,
            "repositories_synced": repos_synced,
            "commits_synced": commits_synced,
            "last_synced": user.last_synced_at.isoformat()
        }

    @staticmethod
    def _mask_token(token: str) -> str:
        """
        Mask GitHub token for secure storage.
        
        Stores only last 4 characters, e.g., "ghp_abc...xyz" → "********xyz"
        
        Args:
            token: GitHub personal access token
            
        Returns:
            Masked token string
        """
        if len(token) <= 4:
            return "*" * len(token)
        return f"{'*' * (len(token) - 4)}{token[-4:]}"
    
    def _sync_repositories(self, user: User) -> int:
        """
        Sync all repositories for the user.
        
        - Adds new repositories
        - Updates metadata (name, url, language) for existing repos
        
        Args:
            user: User database object
            
        Returns:
            Number of new repositories added
        """
        github_repos = self.github_client.get_repositories()
        repos_added = 0
        
        for repo_data in github_repos:
            # Check if repo already exists
            existing_repo = self.db.query(Repository).filter(
                Repository.user_id == user.id,
                Repository.repo_name == repo_data["name"]
            ).first()
            
            if existing_repo:
                # Update metadata in case it changed
                existing_repo.repo_url = repo_data["url"]
                existing_repo.language = repo_data["language"]
            else:
                # Add new repository
                new_repo = Repository(
                    user_id=user.id,
                    repo_name=repo_data["name"],
                    repo_url=repo_data["url"],
                    language=repo_data["language"]
                )
                self.db.add(new_repo)
                repos_added += 1
        
        self.db.commit()
        return repos_added
    
    def _sync_commits(self, user: User) -> int:
        """
        Sync commits for all repositories using incremental strategy.
        
        Incremental sync:
        - Only fetches commits created after last_synced_at
        - Only fetches commits authored by the tracked user
        - Skips commits that already exist in database
        
        Args:
            user: User database object
            
        Returns:
            Number of new commits added
        """
        repos = self.db.query(Repository).filter(Repository.user_id == user.id).all()
        commits_added = 0
        
        # Determine sync cutoff (incremental sync)
        since = None
        if user.last_synced_at:
            # Convert to GitHub ISO format (UTC, ends with Z)
            since = user.last_synced_at.strftime("%Y-%m-%dT%H:%M:%SZ")
        
        for repo in repos:
            repo_full_name = f"{user.github_username}/{repo.repo_name}"
            
            # Fetch commits with filters (incremental + author)
            github_commits = self.github_client.get_commits(
                repo_full_name,
                since=since,
                author=user.github_username  # Only user's commits
            )
            
            for commit_data in github_commits:
                # Check if commit already exists (safety check)
                existing_commit = self.db.query(Commit).filter(
                    Commit.commit_sha == commit_data["sha"]
                ).first()
                
                if not existing_commit:
                    # Get detailed stats for this commit
                    details = self.github_client.get_commit_details(
                        repo_full_name,
                        commit_data["sha"]
                    )
                    
                    new_commit = Commit(
                        repository_id=repo.id,
                        commit_sha=commit_data["sha"],
                        message=commit_data["message"],
                        author_date=datetime.fromisoformat(
                            commit_data["author_date"].replace("Z", "+00:00")
                        ),
                        files_changed=details["files_changed"],
                        additions=details["additions"],
                        deletions=details["deletions"]
                    )
                    self.db.add(new_commit)
                    commits_added += 1
        
        self.db.commit()
        return commits_added