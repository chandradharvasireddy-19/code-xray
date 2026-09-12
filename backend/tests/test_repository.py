import pytest
from app.models.repository import RepositoryModel, FileMeta, Relationship
from app.services.repository_service import RepositoryService
from app.storage.memory_store import db


def test_repository_model_serialization():
    repo = RepositoryModel(
        repository_id="repo-test-123",
        name="test-service",
        path="/tmp/test",
        files=["main.py", "service.py"],
        declared_dependencies={"fastapi": "0.110.0"},
    )
    data = repo.to_dict()
    assert data["repository_id"] == "repo-test-123"
    assert data["name"] == "test-service"
    assert "main.py" in data["files"]
    assert data["declared_dependencies"]["fastapi"] == "0.110.0"


def test_repository_service_save_and_retrieve():
    repo = RepositoryModel(
        repository_id="repo-service-test",
        name="service-test",
        path="/test/path",
        files=["app.py"],
    )
    db.save_repository(repo)

    retrieved = RepositoryService.get_repository("repo-service-test")
    assert retrieved is not None
    assert retrieved.name == "service-test"

    summary_list = RepositoryService.list_repositories()
    assert any(r["repository_id"] == "repo-service-test" for r in summary_list)


def test_register_local_repository_persists_to_db(tmp_path):
    (tmp_path / "hello.py").write_text("print(1)", encoding="utf-8")
    workspace = RepositoryService.register_local_repository(
        path=str(tmp_path),
        name="direct-test",
    )
    assert workspace.repository_id is not None
    repo = RepositoryService.get_repository(workspace.repository_id)
    assert repo is not None
    assert repo.name == "direct-test"
    assert "hello.py" in repo.files

