import pytest
from app.services.github_service import GitHubService
from app.ingestion.private_repo import PrivateRepoLoader


def test_github_service_private_validation():
    with pytest.raises(ValueError, match="Authentication token is required"):
        GitHubService.ingest_private_repository(
            repo_url="https://github.com/test/repo",
            token="",
        )


def test_private_repo_token_redaction():
    loader = PrivateRepoLoader(
        repo_url="https://github.com/my-org/secret-repo",
        token="ghp_mySuperSecretToken1234567890abcdef",
    )
    auth_url = loader._build_authenticated_url()
    assert "ghp_mySuperSecretToken" in auth_url

    redacted = loader._redact_token(f"Error connecting with {loader.token}")
    assert "ghp_mySuperSecretToken" not in redacted
    assert "[REDACTED_TOKEN]" in redacted
