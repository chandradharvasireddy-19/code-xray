import os
import pytest
from pathlib import Path
from app.ingestion.local_repo import LocalRepoLoader
from app.ingestion.private_repo import PrivateRepoLoader
from app.ingestion.public_repo import PublicRepoLoader
from app.ingestion import RepositoryWorkspace, RepositorySourceType


def test_local_repo_loader_success(tmp_path):
    # Create test directory
    sub = tmp_path / "my_project"
    sub.mkdir()
    (sub / "main.py").write_text("print('hello')", encoding="utf-8")

    loader = LocalRepoLoader(str(sub))
    workspace = loader.load()

    assert isinstance(workspace, RepositoryWorkspace)
    assert workspace.source == RepositorySourceType.LOCAL.value
    assert workspace.name == "my_project"
    assert workspace.status == "ready"
    assert workspace.metadata["file_count_estimate"] == 1


def test_local_repo_loader_nonexistent():
    loader = LocalRepoLoader("C:/nonexistent_path_xyz_123")
    with pytest.raises(FileNotFoundError):
        loader.load()


def test_private_repo_loader_missing_token():
    loader = PrivateRepoLoader(
        repo_url="https://github.com/org/private-repo",
        token="",
    )
    with pytest.raises(ValueError, match="Authentication token is required"):
        loader.load()
