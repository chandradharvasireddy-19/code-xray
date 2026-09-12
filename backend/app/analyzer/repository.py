import os
import re
from pathlib import Path
from typing import Dict, List, Optional, Set, Tuple
from app.models.repository import RepositoryModel, FileMeta, CodeEntity, Relationship


class RepositoryLoader:
    """
    Loads and normalizes a repository from a local filesystem path into a RepositoryModel.
    Categorizes files, extracts declared dependencies, and prepares files for AST analysis.
    """

    EXTENSIONS_SOURCE = {".py", ".js", ".ts", ".jsx", ".tsx", ".java", ".go", ".rs", ".rb", ".php", ".c", ".cpp"}
    EXTENSIONS_DOCS = {".md", ".rst", ".txt", ".adoc"}
    EXTENSIONS_CONFIG = {".json", ".yaml", ".yml", ".toml", ".ini", ".cfg", ".xml", ".env"}

    IGNORE_DIRS = {
        ".git", ".svn", ".hg", "__pycache__", ".pytest_cache",
        "node_modules", ".venv", "venv", "env", ".idea", ".vscode",
        "dist", "build", ".egg-info", ".tox", ".mypy_cache"
    }

    def __init__(self, repo_id: str, repo_path: str, repo_name: Optional[str] = None):
        self.repo_id = repo_id
        self.repo_path = Path(repo_path).resolve()
        self.repo_name = repo_name or self.repo_path.name

    def load(self) -> RepositoryModel:
        """
        Scan repository directory tree and construct baseline RepositoryModel.
        """
        if not self.repo_path.exists() or not self.repo_path.is_dir():
            raise FileNotFoundError(f"Repository directory does not exist: {self.repo_path}")

        files_list: List[str] = []
        dirs_list: List[str] = []
        languages: Dict[str, int] = {}
        source_files: List[str] = []
        test_files: List[str] = []
        doc_files: List[str] = []
        config_files: List[str] = []
        file_metadata: Dict[str, FileMeta] = {}

        for root, dirs, files in os.walk(self.repo_path):
            # Prune ignored directories in-place
            dirs[:] = [d for d in dirs if d not in self.IGNORE_DIRS and not d.startswith(".")]

            rel_root = Path(root).relative_to(self.repo_path).as_posix()
            if rel_root != ".":
                dirs_list.append(rel_root)

            for file_name in files:
                full_file_path = Path(root) / file_name
                rel_file_path = full_file_path.relative_to(self.repo_path).as_posix()

                # Ignore lock files or OS files
                if file_name.startswith(".") or file_name.endswith((".pyc", ".pyo")):
                    continue

                files_list.append(rel_file_path)
                ext = full_file_path.suffix.lower()
                size = full_file_path.stat().st_size if full_file_path.exists() else 0

                is_test = self._is_test_file(rel_file_path)
                is_source = ext in self.EXTENSIONS_SOURCE and not is_test
                is_doc = ext in self.EXTENSIONS_DOCS
                is_config = ext in self.EXTENSIONS_CONFIG or file_name in ["Dockerfile", "Makefile", "requirements.txt"]

                if is_test:
                    test_files.append(rel_file_path)
                elif is_source:
                    source_files.append(rel_file_path)

                if is_doc:
                    doc_files.append(rel_file_path)
                if is_config:
                    config_files.append(rel_file_path)

                lang = self._detect_language(ext, file_name)
                languages[lang] = languages.get(lang, 0) + 1

                file_metadata[rel_file_path] = FileMeta(
                    path=rel_file_path,
                    full_path=str(full_file_path),
                    size_bytes=size,
                    language=lang,
                    is_source=is_source or is_test,
                    is_test=is_test,
                    is_doc=is_doc,
                    is_config=is_config,
                )

        declared_deps = self._extract_dependencies()

        return RepositoryModel(
            repository_id=self.repo_id,
            name=self.repo_name,
            path=str(self.repo_path),
            files=files_list,
            directories=dirs_list,
            languages=languages,
            source_files=source_files,
            test_files=test_files,
            documentation_files=doc_files,
            configuration_files=config_files,
            declared_dependencies=declared_deps,
            file_metadata=file_metadata,
        )

    def _is_test_file(self, rel_path: str) -> bool:
        lower = rel_path.lower()
        parts = lower.split("/")
        filename = parts[-1]
        
        # Test directory patterns
        in_test_dir = any(p in ["tests", "test", "spec", "specs", "testing"] for p in parts[:-1])
        # Filename patterns
        is_test_name = (
            filename.startswith("test_")
            or filename.endswith(("_test.py", ".test.js", ".spec.js", ".test.ts", ".spec.ts"))
        )
        return in_test_dir or is_test_name

    def _detect_language(self, ext: str, filename: str) -> str:
        lang_map = {
            ".py": "python",
            ".js": "javascript",
            ".ts": "typescript",
            ".jsx": "javascript",
            ".tsx": "typescript",
            ".go": "go",
            ".java": "java",
            ".rs": "rust",
            ".c": "c",
            ".cpp": "cpp",
            ".h": "c_header",
            ".rb": "ruby",
            ".php": "php",
            ".html": "html",
            ".css": "css",
            ".sql": "sql",
            ".md": "markdown",
            ".json": "json",
            ".yaml": "yaml",
            ".yml": "yaml",
            ".toml": "toml",
        }
        if filename in ["Dockerfile", "docker-compose.yml"]:
            return "docker"
        return lang_map.get(ext, "other")

    def _extract_dependencies(self) -> Dict[str, Optional[str]]:
        """
        Extract declared dependencies from requirements.txt, pyproject.toml, or setup.py.
        """
        dependencies: Dict[str, Optional[str]] = {}

        # 1. Check requirements.txt
        req_paths = [
            self.repo_path / "requirements.txt",
            self.repo_path / "requirements-dev.txt",
            self.repo_path / "requirements" / "base.txt",
        ]
        for req_path in req_paths:
            if req_path.exists():
                try:
                    with open(req_path, "r", encoding="utf-8", errors="ignore") as f:
                        for line in f:
                            clean = line.strip()
                            if not clean or clean.startswith("#") or clean.startswith("-"):
                                continue
                            # Parse package name and version: e.g. "requests>=2.28.0", "numpy==1.24.0", "fastapi"
                            match = re.match(r"^([a-zA-Z0-9_\-\.]+)\s*([><!=~^].*)?$", clean)
                            if match:
                                pkg = match.group(1).lower().replace("-", "_")
                                ver = match.group(2).strip() if match.group(2) else None
                                dependencies[pkg] = ver
                except Exception:
                    pass

        # 2. Check pyproject.toml (basic regex parsing without external dependency)
        pyproj_path = self.repo_path / "pyproject.toml"
        if pyproj_path.exists():
            try:
                with open(pyproj_path, "r", encoding="utf-8", errors="ignore") as f:
                    in_deps = False
                    for line in f:
                        clean = line.strip()
                        if clean.startswith("[") and ("dependencies" in clean):
                            in_deps = True
                            continue
                        elif clean.startswith("["):
                            in_deps = False
                        if in_deps and "=" in clean:
                            parts = clean.split("=", 1)
                            pkg = parts[0].strip().strip('"\'').lower().replace("-", "_")
                            ver = parts[1].strip().strip('"\'')
                            if pkg:
                                dependencies[pkg] = ver
            except Exception:
                pass

        return dependencies
