from src.github_client import GitHubClient

client = GitHubClient()

# Test 1: Get repositories
print("=== REPOSITORIES ===")
repos = client.get_repositories()
for repo in repos:
    print(f"  {repo['name']} ({repo['language']})")

# Test 2: Get commits from first repo
if repos:
    first_repo = repos[0]["full_name"]
    print(f"\n=== COMMITS FROM {first_repo} ===")
    commits = client.get_commits(first_repo)
    print(f"Total commits: {len(commits)}")
    
    # Test 3: Get details of first commit
    if commits:
        first_commit_sha = commits[0]["sha"]
        print(f"\n=== COMMIT DETAILS: {first_commit_sha[:7]} ===")
        details = client.get_commit_details(first_repo, first_commit_sha)
        print(f"  Files changed: {details['files_changed']}")
        print(f"  Additions: {details['additions']}")
        print(f"  Deletions: {details['deletions']}")