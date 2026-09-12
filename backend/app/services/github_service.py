from typing import Any, Dict, Optional
from app.ingestion.public_repo import PublicRepoLoader
from app.ingestion.private_repo import PrivateRepoLoader
from app.ingestion import RepositoryWorkspace


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
        return loader.load()

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
        return loader.load()
