import subprocess
import pytest
from fastapi.testclient import TestClient
from app.main import app
from app.services.github_service import GitHubService
from app.ingestion.private_repo import PrivateRepoLoader
from app.config import REPOS_DIR

client = TestClient(app)


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


# ---------------------------------------------------------------------------
# Helper: create a minimal local git repository that scan_service can use
# as a stand-in for a real GitHub-cloned workspace.
# ---------------------------------------------------------------------------
def _make_local_git_repo(base_tmp: "Path") -> "Path":
    """Create a bare-minimum git repo under base_tmp and return its path."""
    repo = base_tmp / "fake_cloned_repo"
    repo.mkdir()
    (repo / "app.py").write_text(
        "import os\n\ndef process():\n    pass\n", encoding="utf-8"
    )
    subprocess.run(["git", "init"], cwd=str(repo), capture_output=True, check=True)
    subprocess.run(
        ["git", "config", "user.email", "test@test.com"],
        cwd=str(repo), capture_output=True, check=True,
    )
    subprocess.run(
        ["git", "config", "user.name", "Tester"],
        cwd=str(repo), capture_output=True, check=True,
    )
    subprocess.run(["git", "add", "."], cwd=str(repo), capture_output=True, check=True)
    subprocess.run(
        ["git", "commit", "-m", "initial commit"],
        cwd=str(repo), capture_output=True, check=True,
    )
    return repo


def test_github_ingest_then_scan_reuses_existing_workspace(tmp_path):
    """
    Regression: POST /github/public creates workspace, then POST /repository/scan
    with the same repository_id must NOT reclone (previously caused HTTP 500
    'directory already exists').  Instead it must scan the existing workspace.
    """
    local_src = _make_local_git_repo(tmp_path)
    repo_id = "repo-reuse-test-001"

    # Place the "already-cloned" workspace where REPOS_DIR/repo_id would be.
    import shutil
    workspace_dir = REPOS_DIR / repo_id
    if workspace_dir.exists():
        shutil.rmtree(workspace_dir)
    shutil.copytree(str(local_src), str(workspace_dir))

    try:
        # Now scan with that repository_id + a repo_url. The scan service
        # must detect the existing workspace and skip cloning.
        scan_resp = client.post(
            "/repository/scan",
            json={
                "repo_url": "https://github.com/example/example.git",  # would fail if actually cloned
                "repository_id": repo_id,
                "name": "ReusedWorkspaceRepo",
            },
        )
        assert scan_resp.status_code == 201, (
            f"Expected 201, got {scan_resp.status_code}: {scan_resp.text}"
        )
        data = scan_resp.json()
        assert data["status"] == "completed", f"Scan did not complete: {data}"
        assert data["repository_id"] == repo_id
        # Git history should be found (we committed one commit above)
        assert data.get("git_commits_analyzed", 0) >= 1, "Expected at least 1 git commit"
    finally:
        # Cleanup workspace
        shutil.rmtree(workspace_dir, ignore_errors=True)


def test_scan_existing_local_repository(tmp_path):
    """
    Existing local repository scan must still work without any prior
    /github/public ingestion, using only 'path'.
    """
    local_src = _make_local_git_repo(tmp_path)

    scan_resp = client.post(
        "/repository/scan",
        json={"path": str(local_src), "name": "LocalDirectScan"},
    )
    assert scan_resp.status_code == 201, (
        f"Expected 201, got {scan_resp.status_code}: {scan_resp.text}"
    )
    data = scan_resp.json()
    assert data["status"] == "completed"
    assert data["file_count"] >= 1
    # Git history present
    assert data.get("git_commits_analyzed", 0) >= 1


def test_direct_remote_scan_without_prior_registration(tmp_path):
    """
    POST /repository/scan with a local file-URL (simulates remote URL scanning
    without any prior /github/public call) must clone-and-scan successfully.
    No repository_id is supplied up-front, so a fresh one is generated.
    """
    local_src = _make_local_git_repo(tmp_path)
    # Use a file:// URI so git treats it like a remote clone without network.
    file_uri = local_src.as_uri()

    scan_resp = client.post(
        "/repository/scan",
        json={"repo_url": file_uri, "name": "DirectRemoteScan"},
    )
    assert scan_resp.status_code == 201, (
        f"Expected 201, got {scan_resp.status_code}: {scan_resp.text}"
    )
    data = scan_resp.json()
    assert data["status"] == "completed"
    assert data["file_count"] >= 1
    assert data.get("git_commits_analyzed", 0) >= 1

    # Cleanup cloned workspace
    import shutil
    repo_id = data["repository_id"]
    shutil.rmtree(REPOS_DIR / repo_id, ignore_errors=True)

