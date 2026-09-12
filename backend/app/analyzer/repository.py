from __future__ import annotations

import os
from pathlib import Path


class RepositoryAnalyzer:
    """Discovers and filters files within a local repository for forensic analysis."""

    IGNORED_DIRECTORIES: set[str] = {
        ".git",
        ".venv",
        "venv",
        "__pycache__",
        "node_modules",
        ".pytest_cache",
    }
    IGNORED_DIRS = IGNORED_DIRECTORIES

    def __init__(
        self,
        repo_path: str | Path,
        ignored_directories: set[str] | None = None,
    ) -> None:
        """Initialize the repository analyzer.

        Args:
            repo_path: Path to the local repository.
            ignored_directories: Optional set of directory names to ignore during discovery.

        Raises:
            ValueError: If repo_path is empty.
            FileNotFoundError: If repo_path does not exist.
            NotADirectoryError: If repo_path is not a directory.
        """
        if isinstance(repo_path, str) and not repo_path.strip():
            raise ValueError("Repository path cannot be empty.")

        self.repo_path: Path = Path(repo_path).resolve()
        self.repository_path: Path = self.repo_path

        if not self.repo_path.exists():
            raise FileNotFoundError(f"Repository path does not exist: {self.repo_path}")
        if not self.repo_path.is_dir():
            raise NotADirectoryError(f"Repository path is not a directory: {self.repo_path}")

        self.ignored_directories: set[str] = (
            set(ignored_directories) if ignored_directories is not None else set(self.IGNORED_DIRECTORIES)
        )

    def discover_files(self) -> list[Path]:
        """Recursively discover files in the repository, ignoring specified directories.

        Returns:
            A sorted list of file paths relative to the repository root.
        """
        discovered: list[Path] = []

        if hasattr(self.repo_path, "walk"):
            for root, dirs, files in self.repo_path.walk():
                dirs[:] = [d for d in dirs if d not in self.ignored_directories]
                for file_name in files:
                    rel_path = (root / file_name).relative_to(self.repo_path)
                    if not any(part in self.ignored_directories for part in rel_path.parts[:-1]):
                        discovered.append(rel_path)
        else:
            for root_str, dirs, files in os.walk(self.repo_path):
                dirs[:] = [d for d in dirs if d not in self.ignored_directories]
                root = Path(root_str)
                for file_name in files:
                    rel_path = (root / file_name).relative_to(self.repo_path)
                    if not any(part in self.ignored_directories for part in rel_path.parts[:-1]):
                        discovered.append(rel_path)

        return sorted(discovered)

    get_files = discover_files
    list_files = discover_files

    def is_python_file(self, file_path: str | Path) -> bool:
        """Determine whether a given file path is a Python file (.py).

        Args:
            file_path: Path to the file.

        Returns:
            True if the file has a .py extension, False otherwise.
        """
        return Path(file_path).suffix == ".py"

    def get_python_files(self) -> list[Path]:
        """Return all Python files in the repository relative to root.

        Returns:
            A sorted list of relative paths for Python files.
        """
        return [f for f in self.discover_files() if self.is_python_file(f)]

    discover_python_files = get_python_files

    def is_test_file(self, file_path: str | Path) -> bool:
        """Determine whether a given file path is a test file.

        Test files include:
        - files beginning with test_
        - files ending with _test.py
        - Python files inside a tests directory

        Args:
            file_path: Path to check (relative or absolute).

        Returns:
            True if the file is a test file, False otherwise.
        """
        path = Path(file_path)
        if path.is_absolute():
            try:
                path = path.relative_to(self.repo_path)
            except ValueError:
                pass

        name = path.name

        # 1. files beginning with test_
        if name.startswith("test_"):
            return True

        # 2. files ending with _test.py
        if name.endswith("_test.py"):
            return True

        # 3. Python files inside a tests directory
        if path.suffix == ".py" and any(part.lower() == "tests" for part in path.parts[:-1]):
            return True

        return False

    def get_test_files(self) -> list[Path]:
        """Return all test files in the repository relative to root.

        Returns:
            A sorted list of relative paths for test files.
        """
        return [f for f in self.discover_files() if self.is_test_file(f)]

    discover_test_files = get_test_files
