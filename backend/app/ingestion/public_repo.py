import os
import shutil
import subprocess
import uuid
from pathlib import Path
from typing import Optional, Dict, Any
from app.config import REPOS_DIR
from app.ingestion import BaseRepoLoader, RepositoryWorkspace, RepositorySourceType


class PublicRepoLoader(BaseRepoLoader):
    """
    Clones a public Git repository into a managed local workspace directory.
    Uses shallow clone (--depth 1) for speed and resource efficiency.
    """

    def __init__(
        self,
        repo_url: str,
        branch: Optional[str] = None,
        repository_id: Optional[str] = None,
        name: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ):
        self.repo_url = repo_url.strip()
        self.branch = branch.strip() if branch else None
        self.repository_id = repository_id or f"repo-{uuid.uuid4().hex[:8]}"
        
        # Derive name from URL if not specified
        if name:
            self.name = name
        else:
            clean_url = self.repo_url.rstrip("/")
            if clean_url.endswith(".git"):
                clean_url = clean_url[:-4]
            self.name = clean_url.split("/")[-1] or "public-repo"

        self.metadata = metadata or {}
        self.target_dir = REPOS_DIR / self.repository_id

    def load(self) -> RepositoryWorkspace:
        if self.target_dir.exists():
            shutil.rmtree(self.target_dir, ignore_errors=True)
        self.target_dir.mkdir(parents=True, exist_ok=True)

        cmd = ["git", "clone", "--depth", "1"]
        if self.branch:
            cmd.extend(["--branch", self.branch])
        cmd.extend([self.repo_url, str(self.target_dir)])

        try:
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                encoding="utf-8",
                errors="replace",
                timeout=120,
            )
        except subprocess.TimeoutExpired as e:
            shutil.rmtree(self.target_dir, ignore_errors=True)
            raise TimeoutError(f"Git clone timed out after 120 seconds: {self.repo_url}") from e
        except FileNotFoundError as e:
            raise RuntimeError("Git executable not found in system PATH.") from e

        if result.returncode != 0:
            shutil.rmtree(self.target_dir, ignore_errors=True)
            raise RuntimeError(f"Git clone failed (exit {result.returncode}): {result.stderr.strip()}")

        meta = dict(self.metadata)
        meta["repo_url"] = self.repo_url
        meta["branch"] = self.branch or "default"
        meta["is_git_repo"] = (self.target_dir / ".git").exists()

        return RepositoryWorkspace(
            repository_id=self.repository_id,
            name=self.name,
            source=RepositorySourceType.GITHUB_PUBLIC.value,
            path=str(self.target_dir.resolve()),
            status="ready",
            metadata=meta,
        )
