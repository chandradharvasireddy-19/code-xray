import os
import uuid
from pathlib import Path
from typing import Optional, Dict, Any
from app.ingestion import BaseRepoLoader, RepositoryWorkspace, RepositorySourceType


class LocalRepoLoader(BaseRepoLoader):
    """
    Ingests a local directory path into a RepositoryWorkspace.
    Ensures path exists, is a directory, and contains readable content.
    """

    def __init__(
        self,
        local_path: str,
        repository_id: Optional[str] = None,
        name: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ):
        self.raw_path = local_path
        self.resolved_path = Path(local_path).resolve()
        self.repository_id = repository_id or f"repo-{uuid.uuid4().hex[:8]}"
        self.name = name or self.resolved_path.name or "local-repo"
        self.metadata = metadata or {}

    def load(self) -> RepositoryWorkspace:
        if not self.resolved_path.exists():
            raise FileNotFoundError(f"Local repository path does not exist: {self.raw_path}")
        if not self.resolved_path.is_dir():
            raise NotADirectoryError(f"Local repository path is not a directory: {self.raw_path}")

        # Check readable
        try:
            items = os.listdir(self.resolved_path)
        except PermissionError as e:
            raise PermissionError(f"Permission denied accessing local repository: {self.raw_path}") from e

        meta = dict(self.metadata)
        meta["file_count_estimate"] = len(items)
        meta["is_git_repo"] = (self.resolved_path / ".git").exists()

        return RepositoryWorkspace(
            repository_id=self.repository_id,
            name=self.name,
            source=RepositorySourceType.LOCAL.value,
            path=str(self.resolved_path),
            status="ready",
            metadata=meta,
        )
