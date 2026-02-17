from sqlalchemy.orm import Session
from src.models import User, Repository, Commit
from src.github_client import GitHubClient
from datetime import datetime, timezone
import os
import requests


class GitHubSyncService:
    def __init__(self, db: Session):
        self.db = db
        self.github_client = GitHubClient()
    
    def sync_user_data(self) -> dict:
        """
        Main function to sync all GitHub data for the user
        Returns summary of what was synced
        """
        username = os.getenv("GITHUB_USERNAME")
        token = os.getenv("GITHUB_TOKEN")
        if not username:
            raise ValueError("GITHUB_USERNAME is not set. Add it to your .env file.")
        if not token:
            raise ValueError("GITHUB_TOKEN is not set. Add it to your .env file.")
        
        # Get or create user
        user = self.db.query(User).filter(User.github_username == username).first()
        if not user:
            user = User(github_username=username, github_token=self._mask_token(token))
            self.db.add(user)
            self.db.commit()
            self.db.refresh(user)
        else:
            # Keep a non-sensitive marker instead of the raw token.
            user.github_token = self._mask_token(token)
            self.db.commit()
        
        # Sync repositories
        try:
            repos_synced = self._sync_repositories(user)
        
            # Sync commits for each repo
            commits_synced = self._sync_commits(user)
        except requests.RequestException as exc:
            self.db.rollback()
            raise RuntimeError(f"GitHub API request failed: {exc}") from exc
        
        # Update last sync time
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
        if len(token) <= 4:
            return "*" * len(token)
        return f"{'*' * (len(token) - 4)}{token[-4:]}"
    
    def _sync_repositories(self, user: User) -> int:
        """Sync all repositories for the user"""
        github_repos = self.github_client.get_repositories()
        repos_added = 0
        
        for repo_data in github_repos:
            # Check if repo already exists
            existing_repo = self.db.query(Repository).filter(
                Repository.user_id == user.id,
                Repository.repo_name == repo_data["name"]
            ).first()
            
            if not existing_repo:
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
        """Sync commits for all repositories"""
        repos = self.db.query(Repository).filter(Repository.user_id == user.id).all()
        commits_added = 0
        
        for repo in repos:
            # Get commits from GitHub
            repo_full_name = f"{user.github_username}/{repo.repo_name}"
            github_commits = self.github_client.get_commits(repo_full_name)
            
            for commit_data in github_commits:
                # Check if commit already exists
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