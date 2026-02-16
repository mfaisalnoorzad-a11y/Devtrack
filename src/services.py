from sqlalchemy.orm import Session
from src.models import User, Repository, Commit
from src.github_client import GitHubClient
from datetime import datetime
import os


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
        
        # Get or create user
        user = self.db.query(User).filter(User.github_username == username).first()
        if not user:
            user = User(github_username=username, github_token=token)
            self.db.add(user)
            self.db.commit()
            self.db.refresh(user)
        
        # Sync repositories
        repos_synced = self._sync_repositories(user)
        
        # Sync commits for each repo
        commits_synced = self._sync_commits(user)
        
        # Update last sync time
        user.last_synced_at = datetime.now()
        self.db.commit()
        
        return {
            "username": username,
            "repositories_synced": repos_synced,
            "commits_synced": commits_synced,
            "last_synced": user.last_synced_at.isoformat()
        }
    
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