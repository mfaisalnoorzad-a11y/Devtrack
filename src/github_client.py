import requests
from typing import List, Dict, Optional
import os
from dotenv import load_dotenv

load_dotenv()


class GitHubClient:
    def __init__(self):
        self.token = os.getenv("GITHUB_TOKEN")
        self.username = os.getenv("GITHUB_USERNAME")
        if not self.token:
            raise ValueError("GITHUB_TOKEN is not set. Add it to your .env file.")
        if not self.username:
            raise ValueError("GITHUB_USERNAME is not set. Add it to your .env file.")
        self.base_url = "https://api.github.com"
        self.headers = {
            "Authorization": f"token {self.token}",
            "Accept": "application/vnd.github.v3+json"
        }

    def _get_paginated(self, url: str, params: Optional[Dict] = None) -> List[Dict]:
        """Fetch all pages for GitHub list endpoints."""
        items: List[Dict] = []
        page = 1
        while True:
            page_params = dict(params or {})
            page_params["per_page"] = 100
            page_params["page"] = page

            response = requests.get(url, headers=self.headers, params=page_params, timeout=30)
            response.raise_for_status()
            chunk = response.json()
            if not chunk:
                break

            items.extend(chunk)
            if len(chunk) < 100:
                break
            page += 1

        return items

    def get_repositories(self) -> List[Dict]:
        """Fetch all repositories for the user"""
        # /user/repos includes private repos when authenticated.
        url = f"{self.base_url}/user/repos"
        repos = self._get_paginated(url)
        return [
            {
                "name": repo["name"],
                "url": repo["html_url"],
                "language": repo.get("language"),
                "full_name": repo["full_name"]
            }
            for repo in repos
        ]
    
    def get_commits(self, repo_full_name: str, since: Optional[str] = None, author: Optional[str] = None) -> List[Dict]:
        """
        Fetch commits for a repository
        repo_full_name: e.g., 'mfaisalnoorzad-a11y/Asteroids'
        since: ISO 8601 date string (e.g., '2026-01-01T00:00:00Z')
        author: GitHub username to filter commits by author
        """
        url = f"{self.base_url}/repos/{repo_full_name}/commits"
        params = {}
        if since:
            params["since"] = since
        if author:
            params["author"] = author
    
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
        response = requests.get(url, headers=self.headers, timeout=30)
        response.raise_for_status()

        commit = response.json()
        stats = commit.get("stats", {})

        return {
            "sha": commit_sha,
            "files_changed": len(commit.get("files", [])),
            "additions": stats.get("additions", 0),
            "deletions": stats.get("deletions", 0)
        }