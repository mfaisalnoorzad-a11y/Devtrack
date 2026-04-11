from datetime import datetime, timezone

from src import models


def test_health_endpoint_is_public(client):
    test_client, _ = client

    response = test_client.get("/health")

    assert response.status_code == 200
    assert response.json() == {"status": "healthy"}


def test_sync_requires_api_key(client):
    test_client, _ = client

    response = test_client.post("/sync")

    assert response.status_code == 401
    assert response.json()["detail"] == "Invalid or missing API key."


def test_stats_returns_404_when_user_has_not_been_synced(client):
    test_client, _ = client

    response = test_client.get("/stats", headers={"X-API-Key": "test-api-key"})

    assert response.status_code == 404
    assert response.json()["detail"] == "User not synced yet. Call POST /sync first to initialize."


def test_stats_returns_aggregated_metrics(client):
    test_client, session_factory = client
    db = session_factory()

    user = models.User(
        github_username="test-user",
        github_token="****oken",
        last_synced_at=datetime(2026, 4, 11, tzinfo=timezone.utc),
    )
    db.add(user)
    db.commit()
    db.refresh(user)

    repo = models.Repository(
        user_id=user.id,
        repo_name="devtrack",
        repo_url="https://github.com/test-user/devtrack",
        language="Python",
    )
    db.add(repo)
    db.commit()
    db.refresh(repo)

    db.add_all(
        [
            models.Commit(
                repository_id=repo.id,
                commit_sha="abc123456789",
                message="Add auth support",
                author_date=datetime(2026, 4, 10, tzinfo=timezone.utc),
                files_changed=3,
                additions=42,
                deletions=5,
            ),
            models.Commit(
                repository_id=repo.id,
                commit_sha="def123456789",
                message="Improve tests",
                author_date=datetime(2026, 4, 11, tzinfo=timezone.utc),
                files_changed=2,
                additions=18,
                deletions=4,
            ),
        ]
    )
    db.commit()
    db.close()

    response = test_client.get("/stats", headers={"X-API-Key": "test-api-key"})

    payload = response.json()
    assert response.status_code == 200
    assert payload["username"] == "test-user"
    assert payload["repositories"] == 1
    assert payload["total_commits"] == 2
    assert payload["languages"] == {"Python": 1}
    assert payload["total_lines_added"] == 60
    assert payload["total_lines_deleted"] == 9
    assert payload["total_files_changed"] == 5
    assert payload["net_lines"] == 51
