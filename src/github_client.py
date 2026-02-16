import requests
from typing import List, Dict, Optional
from datetime import datetime
import os
from dotenv import load_dotenv

load_dotenv()

class GitHubClient:
    def __init__(self):
        self.token = os.getenv("GITHUB_TOKEN")
        self.username = os.getenv("GITHUB_USERNAME")
        self.base_url = "https://api.github.com"
        self.headers = {
            "Authorization": f"token {self.token}",
            "Accept": "application/vnd.github.v3+json"
        }
    
    def get_repositories(self) -> List[Dict]:
        """Fetch all repositories for the user"""
        url = f"{self.base_url}/users/{self.username}/repos"
        response = requests.get(url, headers=self.headers)
        response.raise_for_status()
        
        repos = response.json()
        return [
            {
                "name": repo["name"],
                "url": repo["html_url"],
                "language": repo.get("language"),
                "full_name": repo["full_name"]
            }
            for repo in repos
        ]
    
    def get_commits(self, repo_full_name: str, since: Optional[str] = None) -> List[Dict]:
        """
        Fetch commits for a repository
        repo_full_name: e.g., 'mfaisalnoorzad-a11y/Asteroids'
        since: ISO 8601 date string (e.g., '2026-01-01T00:00:00Z')
        """
        url = f"{self.base_url}/repos/{repo_full_name}/commits"
        params = {}
        if since:
            params["since"] = since
        
        response = requests.get(url, headers=self.headers, params=params)
        response.raise_for_status()
        
        commits = response.json()
        return [
            {
                "sha": commit["sha"],
                "message": commit["commit"]["message"],
                "author_date": commit["commit"]["author"]["date"],
                "url": commit["html_url"]
            }
            for commit in commits
        ]
    
    def get_commit_details(self, repo_full_name: str, commit_sha: str) -> Dict:
        """
        Get detailed stats for a specific commit
        Returns: files_changed, additions, deletions
        """
        url = f"{self.base_url}/repos/{repo_full_name}/commits/{commit_sha}"
        response = requests.get(url, headers=self.headers)
        response.raise_for_status()
        
        commit = response.json()
        stats = commit.get("stats", {})
        
        return {
            "sha": commit_sha,
            "files_changed": len(commit.get("files", [])),
            "additions": stats.get("additions", 0),
            "deletions": stats.get("deletions", 0)
        }