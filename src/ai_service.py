from anthropic import Anthropic
import os
from typing import List, Dict
from anthropic import APIError


class AIService:
    def __init__(self):
        api_key = os.getenv("ANTHROPIC_API_KEY")
        if not api_key:
            raise ValueError("ANTHROPIC_API_KEY is not set. Add it to your .env file.")
        self.client = Anthropic(api_key=api_key)

    def generate_summary(self, commits: List[Dict], timeframe: str) -> str:
        """
        Generate AI summary from commit data
        commits: List of commit dictionaries with keys: message, repo_name, author_date, files_changed, additions, deletions
        timeframe: 'week' or 'month'
        """
        if not commits:
            return f"No commits found in the last {timeframe}."
        
        # Format commits into readable text
        commits_text = self._format_commits_for_ai(commits, timeframe)
        
        # Create prompt for Claude
        prompt = f"""Analyze these Git commits from the last {timeframe} and provide a concise summary.

{commits_text}

Provide a summary that:
1. Groups work by repository/project
2. Highlights main focus areas and accomplishments
3. Notes any patterns (refactoring, bug fixes, new features)
4. Mentions productivity metrics (commit count, lines changed)

Keep it concise (3-4 sentences max). Write in second person ("you worked on...").
"""
        
        try:
            # Call Claude API
            message = self.client.messages.create(
                model="claude-sonnet-4-20250514",
                max_tokens=1000,
                messages=[
                    {"role": "user", "content": prompt}
                ]
            )
        except APIError as exc:
            raise RuntimeError(f"Anthropic API call failed: {exc}") from exc

        return message.content[0].text

    def _format_commits_for_ai(self, commits: List[Dict], timeframe: str) -> str:
        """Format commit data into readable text for the AI"""
        lines = [f"=== Commits from the last {timeframe} ===\n"]
        
        # Group by repository
        repos = {}
        for commit in commits:
            repo = commit["repo_name"]
            if repo not in repos:
                repos[repo] = []
            repos[repo].append(commit)
        
        for repo_name, repo_commits in repos.items():
            lines.append(f"\n**{repo_name}** ({len(repo_commits)} commits):")
            
            total_additions = sum(c["additions"] for c in repo_commits)
            total_deletions = sum(c["deletions"] for c in repo_commits)
            total_files = sum(c["files_changed"] for c in repo_commits)
            
            lines.append(f"  Total changes: +{total_additions}/-{total_deletions} lines, {total_files} files")
            lines.append(f"  Commits:")
            
            for commit in repo_commits[:10]:  # Limit to 10 most recent per repo
                date = commit["author_date"].strftime("%b %d")
                msg = commit["message"].split('\n')[0][:80]  # First line, max 80 chars
                lines.append(f"    - [{date}] {msg} (+{commit['additions']}/-{commit['deletions']})")
        
        return "\n".join(lines)