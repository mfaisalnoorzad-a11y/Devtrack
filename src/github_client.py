"""
GitHub API client for DevTrack.
Handles authentication, pagination, and data fetching from GitHub's REST API.
"""

import requests
from typing import List, Dict, Optional
import os
from dotenv import load_dotenv
import time

load_dotenv()


class GitHubClient:
    """
    Client for interacting with GitHub's REST API.
    
    Handles:
    - Authentication with personal access token
    - Automatic pagination for list endpoints
    - Rate limit awareness
    - Error handling and retries
    """
    
    def __init__(self):
        """
        Initialize GitHub client with credentials from environment.
        
        Raises:
            ValueError: If GITHUB_TOKEN or GITHUB_USERNAME not set
        """
        self.token = os.getenv("GITHUB_TOKEN")
        self.username = os.getenv("GITHUB_USERNAME")
        
        if not self.token:
            raise ValueError(
                "GITHUB_TOKEN environment variable is required. "
                "Create a personal access token at https://github.com/settings/tokens"
            )
        if not self.username:
            raise ValueError("GITHUB_USERNAME environment variable is required.")
        
        self.base_url = "https://api.github.com"
        self.headers = {
            "Authorization": f"token {self.token}",
            "Accept": "application/vnd.github.v3+json"
        }
        self.timeout = 30  # seconds

    def _make_request(self, url: str, params: Optional[Dict] = None, max_retries: int = 3) -> requests.Response:
        """
        Make HTTP request with retry logic.
        
        Args:
            url: API endpoint URL
            params: Query parameters
            max_retries: Number of retry attempts on failure
            
        Returns:
            Response object
            
        Raises:
            RuntimeError: If all retries fail
        """
        for attempt in range(max_retries):
            try:
                response = requests.get(
                    url,
                    headers=self.headers,
                    params=params,
                    timeout=self.timeout
                )
                response.raise_for_status()
                return response
            except requests.exceptions.RequestException as e:
                if attempt == max_retries - 1:
                    raise RuntimeError(f"GitHub API request failed after {max_retries} attempts: {e}") from e
                time.sleep(2 ** attempt)  # Exponential backoff: 1s, 2s, 4s
        
        # This line should never be reached, but satisfies type checker
        raise RuntimeError("Unexpected error in _make_request")

    def _get_paginated(self, url: str, params: Optional[Dict] = None) -> List[Dict]:
        """
        Fetch all pages from a GitHub list endpoint.
        
        GitHub API returns max 100 items per page. This method automatically
        fetches all pages until no more results.
        
        Args:
            url: API endpoint URL
            params: Query parameters
            
        Returns:
            List of all items across all pages
        """
        items: List[Dict] = []
        page = 1
        
        while True:
            page_params = dict(params or {})
            page_params["per_page"] = 100
            page_params["page"] = page

            response = self._make_request(url, page_params)
            chunk = response.json()
            
            if not chunk:
                break

            items.extend(chunk)
            
            # If we got fewer than 100 items, we've reached the last page
            if len(chunk) < 100:
                break
                
            page += 1

        return items

    def get_repositories(self) -> List[Dict]:
        """
        Fetch all repositories for the authenticated user.
        
        Uses /user/repos endpoint which includes private repos.
        
        Returns:
            List of repository dictionaries with keys:
                - name: Repository name
                - url: GitHub URL
                - language: Primary language (or None)
                - full_name: owner/repo format
        """
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
    
    def get_commits(
        self,
        repo_full_name: str,
        since: Optional[str] = None,
        author: Optional[str] = None
    ) -> List[Dict]:
        """
        Fetch commits for a repository with pagination.
        
        Args:
            repo_full_name: Full repository name (e.g., 'owner/repo')
            since: ISO 8601 timestamp to fetch commits after (e.g., '2026-01-01T00:00:00Z')
            author: GitHub username to filter commits by author
            
        Returns:
            List of commit dictionaries with keys:
                - sha: Commit SHA
                - message: Commit message
                - author_date: ISO 8601 commit timestamp
                - url: GitHub commit URL
        """
        url = f"{self.base_url}/repos/{repo_full_name}/commits"
        params = {}
        
        if since:
            params["since"] = since
        if author:
            params["author"] = author
        
        # Use pagination for repos with many commits
        commits = self._get_paginated(url, params)
        
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
        Get detailed statistics for a specific commit.
        
        Args:
            repo_full_name: Full repository name (e.g., 'owner/repo')
            commit_sha: Git commit SHA
            
        Returns:
            Dictionary with keys:
                - sha: Commit SHA
                - files_changed: Number of files modified
                - additions: Lines added
                - deletions: Lines deleted
        """
        url = f"{self.base_url}/repos/{repo_full_name}/commits/{commit_sha}"
        response = self._make_request(url)
        commit = response.json()
        stats = commit.get("stats", {})

        return {
            "sha": commit_sha,
            "files_changed": len(commit.get("files", [])),
            "additions": stats.get("additions", 0),
            "deletions": stats.get("deletions", 0)
        }