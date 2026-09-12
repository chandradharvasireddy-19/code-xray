import os
import sys
import shutil
import subprocess
import uuid
import re
from pathlib import Path
from typing import Optional, Dict, Any
from app.config import REPOS_DIR
from app.ingestion import BaseRepoLoader, RepositoryWorkspace, RepositorySourceType


class PrivateRepoLoader(BaseRepoLoader):
    """
    Clones a private Git repository using authenticated token credentials.
    Ensures credentials are redacted from stored metadata and error logs.
    """

    def __init__(
        self,
        repo_url: str,
        token: str,
        branch: Optional[str] = None,
        repository_id: Optional[str] = None,
        name: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ):
        self.raw_repo_url = repo_url.strip()
        self.token = token.strip()
        self.branch = branch.strip() if branch else None
        self.repository_id = repository_id or f"repo-{uuid.uuid4().hex[:8]}"

        if name:
            self.name = name
        else:
            clean_url = self.raw_repo_url.rstrip("/")
            if clean_url.endswith(".git"):
                clean_url = clean_url[:-4]
            self.name = clean_url.split("/")[-1] or "private-repo"

        self.metadata = metadata or {}
        self.target_dir = REPOS_DIR / self.repository_id

    # ------------------------------------------------------------------
    # Kept for backward-compatibility and existing unit tests.
    # NOT used by load() — see _build_clone_url() + _build_auth_env().
    # ------------------------------------------------------------------
    def _build_authenticated_url(self) -> str:
        """Return a URL with the PAT embedded in the userinfo component.

        Preserved for unit-test compatibility. load() no longer uses this
        because GitHub rejects PATs supplied as the URL *username* with
        HTTP 403; the token must be delivered in the HTTP Basic-auth
        password field, which _build_auth_env() achieves via an injected
        Authorization header.
        """
        url = self.raw_repo_url.rstrip("/")
        if not url.endswith(".git"):
            url = f"{url}.git"
        if url.startswith("https://"):
            stripped = url[len("https://"):]
            return f"https://{self.token}@{stripped}"
        elif url.startswith("http://"):
            stripped = url[len("http://"):]
            return f"http://{self.token}@{stripped}"
        return url

    def _build_clone_url(self) -> str:
        """Return a normalized, credential-free clone URL.

        Credentials are supplied via _build_auth_env() so the token is
        delivered in the HTTP Basic-auth *password* field through an
        Authorization header, not as the URL username.
        """
        url = self.raw_repo_url.rstrip("/")
        if not url.endswith(".git"):
            url = f"{url}.git"
        return url

    def _build_auth_config(self) -> tuple[list[str], dict[str, str]]:
        """
        Build Git credential arguments and environment for authenticated cloning.

        Mechanism:
        - Uses standard Git credential helper mechanism compatible with Git Credential Manager (GCM).
        - When a PAT is supplied, injects a non-interactive credential helper that supplies
          username='oauth2' and password=PAT over Git HTTPS Basic auth.
        - Does NOT clear credential.helper, allowing Git to chain with system/global
          Git Credential Manager (manager).
        - Sets GIT_TERMINAL_PROMPT=0 to prevent any interactive hanging prompts.
        - Does NOT place credentials in the repository URL or use non-standard HTTP headers.
        """
        env = os.environ.copy()
        env["GIT_TERMINAL_PROMPT"] = "0"

        extra_git_args: list[str] = []
        if self.token:
            env["_CODE_XRAY_PAT"] = self.token
            py_exe = sys.executable.replace("\\", "/")
            inline_script = (
                "import os, sys; "
                "pat = os.environ.get('_CODE_XRAY_PAT'); "
                "print('username=oauth2\\npassword=' + pat) if len(sys.argv) > 1 and sys.argv[1] == 'get' and pat else None"
            )
            helper_cmd = f'!\"{py_exe}\" -c \"{inline_script}\"'
            extra_git_args = ["-c", f"credential.helper={helper_cmd}"]

        return extra_git_args, env

    def _redact_token(self, text: str) -> str:
        if self.token:
            return text.replace(self.token, "[REDACTED_TOKEN]")
        return text

    def load(self) -> RepositoryWorkspace:
        if not self.token:
            raise ValueError(
                "Authentication token is required for private repository ingestion."
            )

        if self.target_dir.exists():
            shutil.rmtree(self.target_dir, ignore_errors=True)
        self.target_dir.mkdir(parents=True, exist_ok=True)

        clone_url = self._build_clone_url()
        extra_git_args, env = self._build_auth_config()

        cmd = ["git"] + extra_git_args + ["clone", "--depth", "1"]
        if self.branch:
            cmd.extend(["--branch", self.branch])
        cmd.extend([clone_url, str(self.target_dir)])

        try:
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                encoding="utf-8",
                errors="replace",
                timeout=120,
                stdin=subprocess.DEVNULL,
                env=env,
            )
        except subprocess.TimeoutExpired as e:
            shutil.rmtree(self.target_dir, ignore_errors=True)
            raise TimeoutError("Git clone timed out after 120 seconds.") from e
        except FileNotFoundError as e:
            raise RuntimeError("Git executable not found in system PATH.") from e

        if result.returncode != 0:
            shutil.rmtree(self.target_dir, ignore_errors=True)
            err_clean = self._redact_token(result.stderr.strip())
            raise RuntimeError(f"Private git clone failed: {err_clean}")

        meta = dict(self.metadata)
        meta["repo_url"] = self._redact_token(self.raw_repo_url)
        meta["branch"] = self.branch or "default"
        meta["is_private"] = True
        meta["is_git_repo"] = (self.target_dir / ".git").exists()

        return RepositoryWorkspace(
            repository_id=self.repository_id,
            name=self.name,
            source=RepositorySourceType.GITHUB_PRIVATE.value,
            path=str(self.target_dir.resolve()),
            status="ready",
            metadata=meta,
        )
