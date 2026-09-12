from typing import Any, Dict, List, Optional
from app.models.repository import RepositoryModel
from app.storage.memory_store import db
from app.ingestion.local_repo import LocalRepoLoader
from app.ingestion import RepositoryWorkspace
from app.analyzer.repository import RepositoryLoader


class RepositoryService:
    """
    Manages registered repositories, workspaces, and cached metadata.
    """

    @staticmethod
    def register_local_repository(
        path: str,
        name: Optional[str] = None,
        repository_id: Optional[str] = None,
    ) -> RepositoryWorkspace:
        loader = LocalRepoLoader(
            local_path=path,
            name=name,
            repository_id=repository_id,
        )
        workspace = loader.load()

        repo_loader = RepositoryLoader(
            repo_id=workspace.repository_id,
            repo_path=workspace.path,
            repo_name=workspace.name,
        )
        repo = repo_loader.load()
        db.save_repository(repo)

        return workspace

    @staticmethod
    def get_repository(repository_id: str) -> Optional[RepositoryModel]:
        return db.get_repository(repository_id)

    @staticmethod
    def list_repositories() -> List[Dict[str, Any]]:
        repos = db.list_repositories()
        return [
            {
                "repository_id": r.repository_id,
                "name": r.name,
                "path": r.path,
                "file_count": len(r.files),
                "source_files": len(r.source_files),
                "test_files": len(r.test_files),
                "languages": r.languages,
                "created_at": r.created_at,
            }
            for r in repos
        ]
