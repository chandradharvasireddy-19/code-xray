from typing import Any, Dict, Optional
from app.ingestion.public_repo import PublicRepoLoader
from app.ingestion.private_repo import PrivateRepoLoader
from app.ingestion import RepositoryWorkspace
from app.analyzer.repository import RepositoryLoader
from app.storage.memory_store import db


class GitHubService:
    """
    Handles GitHub repository ingestion (public and private via tokens).
    """

    @staticmethod
    def ingest_public_repository(
        repo_url: str,
        branch: Optional[str] = None,
        name: Optional[str] = None,
        repository_id: Optional[str] = None,
    ) -> RepositoryWorkspace:
        loader = PublicRepoLoader(
            repo_url=repo_url,
            branch=branch,
            name=name,
            repository_id=repository_id,
        )
        workspace = loader.load()
        try:
            repo_loader = RepositoryLoader(
                repo_id=workspace.repository_id,
                repo_path=workspace.path,
                repo_name=workspace.name,
            )
            repo = repo_loader.load()
            db.save_repository(repo)
        except Exception:
            pass
        return workspace

    @staticmethod
    def ingest_private_repository(
        repo_url: str,
        token: str,
        branch: Optional[str] = None,
        name: Optional[str] = None,
        repository_id: Optional[str] = None,
    ) -> RepositoryWorkspace:
        loader = PrivateRepoLoader(
            repo_url=repo_url,
            token=token,
            branch=branch,
            name=name,
            repository_id=repository_id,
        )
        workspace = loader.load()
        try:
            repo_loader = RepositoryLoader(
                repo_id=workspace.repository_id,
                repo_path=workspace.path,
                repo_name=workspace.name,
            )
            repo = repo_loader.load()
            db.save_repository(repo)
        except Exception:
            pass
        return workspace
