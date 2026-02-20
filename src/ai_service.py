"""
AI service for DevTrack using Anthropic's Claude API.
Generates intelligent summaries of commit activity.
"""

from anthropic import Anthropic, APIError, RateLimitError, AuthenticationError
import os
from typing import List, Dict, Optional


class AIService:
    """
    Service for generating AI-powered commit summaries using Claude.
    
    Uses Claude Sonnet 4 to analyze commit patterns and generate
    human-readable summaries of development activity.
    """
    
    def __init__(self):
        """
        Initialize AI service with Anthropic API credentials.
        
        Raises:
            ValueError: If ANTHROPIC_API_KEY not set in environment
        """
        api_key = os.getenv("ANTHROPIC_API_KEY")
        if not api_key:
            raise ValueError(
                "ANTHROPIC_API_KEY environment variable is required. "
                "Get your API key at https://console.anthropic.com"
            )
        self.client = Anthropic(api_key=api_key)
        self.model = "claude-sonnet-4-20250514"  # Best balance of speed/quality/cost

    def generate_summary(self, commits: List[Dict], timeframe: str) -> str:
        """
        Generate AI summary from commit data.
        
        Analyzes commit patterns, groups by repository, and generates
        a natural language summary of development activity.
        
        Args:
            commits: List of commit dictionaries with keys:
                - message: Commit message
                - repo_name: Repository name
                - author_date: Commit timestamp
                - files_changed: Number of files modified
                - additions: Lines added
                - deletions: Lines deleted
            timeframe: Either 'week' or 'month'
            
        Returns:
            AI-generated summary text (2-4 sentences)
            
        Raises:
            RuntimeError: If Anthropic API call fails
        """
        if not commits:
            return f"No commits found in the last {timeframe}."
        
        # Format commits into structured text for Claude
        commits_text = self._format_commits_for_ai(commits, timeframe)
        
        # Craft prompt for Claude
        prompt = f"""Analyze these Git commits from the last {timeframe} and provide a concise summary.

{commits_text}

Provide a summary that:
1. Groups work by repository/project
2. Highlights main focus areas and accomplishments
3. Notes any patterns (refactoring, bug fixes, new features)
4. Mentions productivity metrics (commit count, lines changed)

Keep it concise (3-4 sentences max). Write in second person ("you worked on...").
Do NOT use markdown formatting in the output - just plain text paragraphs."""
        
        try:
            # Call Claude API
            message = self.client.messages.create(
                model=self.model,
                max_tokens=1000,
                messages=[
                    {"role": "user", "content": prompt}
                ]
            )
            
            # Track token usage for cost monitoring
            usage = message.usage
            tokens_used = usage.input_tokens + usage.output_tokens
            
            # Log usage for debugging (optional: send to monitoring service)
            print(f"[AI Service] Tokens used: {tokens_used} (in: {usage.input_tokens}, out: {usage.output_tokens})")
            
            return message.content[0].text
            
        except AuthenticationError as exc:
            raise RuntimeError(
                "Anthropic API authentication failed. Check your ANTHROPIC_API_KEY."
            ) from exc
        except RateLimitError as exc:
            raise RuntimeError(
                "Anthropic API rate limit exceeded. Please try again in a few moments."
            ) from exc
        except APIError as exc:
            raise RuntimeError(f"Anthropic API call failed: {exc}") from exc

    def _format_commits_for_ai(self, commits: List[Dict], timeframe: str) -> str:
        """
        Format commit data into structured text for Claude.
        
        Groups commits by repository and calculates aggregate statistics
        to provide Claude with organized context.
        
        Args:
            commits: List of commit dictionaries
            timeframe: 'week' or 'month'
            
        Returns:
            Formatted text with repository grouping and statistics
        """
        lines = [f"=== Commits from the last {timeframe} ===\n"]
        
        # Group commits by repository
        repos: Dict[str, List[Dict]] = {}
        for commit in commits:
            repo = commit["repo_name"]
            if repo not in repos:
                repos[repo] = []
            repos[repo].append(commit)
        
        # Format each repository's commits
        for repo_name, repo_commits in repos.items():
            lines.append(f"\n**{repo_name}** ({len(repo_commits)} commits):")
            
            # Calculate aggregate statistics
            total_additions = sum(c["additions"] for c in repo_commits)
            total_deletions = sum(c["deletions"] for c in repo_commits)
            total_files = sum(c["files_changed"] for c in repo_commits)
            
            lines.append(f"  Total changes: +{total_additions}/-{total_deletions} lines, {total_files} files")
            lines.append("  Commits:")
            
            # Show up to 10 most recent commits per repo
            for commit in repo_commits[:10]:
                date = commit["author_date"].strftime("%b %d")
                msg = commit["message"].split('\n')[0][:80]  # First line only, max 80 chars
                lines.append(f"    - [{date}] {msg} (+{commit['additions']}/-{commit['deletions']})")
            
            # Note if more commits exist
            if len(repo_commits) > 10:
                lines.append(f"    ... and {len(repo_commits) - 10} more commits")
        
        return "\n".join(lines)