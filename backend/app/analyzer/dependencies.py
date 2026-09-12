from __future__ import annotations

import re
import sys
from pathlib import Path
from typing import Sequence

try:
    import tomllib
except ImportError:
    tomllib = None  # type: ignore

from .models import DependenciesReport, DependencyInfo, ImportInfo, LocalDependencyInfo, ParsedFile


class DependencyAnalyzer:
    """Analyzes declared dependencies and detected imports across a repository."""

    def __init__(self, repo_path: str | Path | None = None) -> None:
        self.repo_path: Path | None = Path(repo_path).resolve() if repo_path else None
        self._stdlib_modules: set[str] = set(sys.stdlib_module_names) if hasattr(sys, "stdlib_module_names") else set()

    def _get_local_module_roots(self, parsed_files: Sequence[ParsedFile]) -> set[str]:
        """Collect top-level names of local modules and packages in the repository."""
        roots: set[str] = set()

        if self.repo_path and self.repo_path.is_dir():
            for item in self.repo_path.iterdir():
                if item.name.startswith("."):
                    continue
                if item.is_dir():
                    roots.add(item.name)
                elif item.suffix == ".py":
                    roots.add(item.stem)

        for pf in parsed_files:
            p = Path(pf.file_path)
            parts = p.parts
            if parts:
                roots.add(parts[0].replace(".py", ""))

        return roots

    def _parse_requirements_txt(self, path: Path) -> dict[str, str | None]:
        """Extract package names and version specs from a requirements.txt file."""
        packages: dict[str, str | None] = {}
        if not path.is_file():
            return packages

        try:
            content = path.read_text(encoding="utf-8", errors="replace")
        except Exception:
            return packages

        for raw_line in content.splitlines():
            line = raw_line.strip()
            if not line or line.startswith("#") or line.startswith("-"):
                continue

            # Remove inline comments
            line = line.split("#")[0].strip()
            # Match package name and optional version specifier
            match = re.match(r"^([A-Za-z0-9_.\-]+)(?:\[[^\]]*\])?\s*(.*)$", line)
            if match:
                pkg_name = match.group(1).strip().lower().replace("-", "_")
                raw_name = match.group(1).strip()
                version_spec = match.group(2).strip() or None
                packages[raw_name] = version_spec
        return packages

    def _parse_pyproject_toml(self, path: Path) -> dict[str, str | None]:
        """Extract declared dependencies from pyproject.toml."""
        packages: dict[str, str | None] = {}
        if not path.is_file() or tomllib is None:
            return packages

        try:
            content = path.read_text(encoding="utf-8", errors="replace")
            data = tomllib.loads(content)
        except Exception:
            return packages

        # PEP 621 dependencies: project.dependencies
        project_deps = data.get("project", {}).get("dependencies", [])
        if isinstance(project_deps, list):
            for dep in project_deps:
                match = re.match(r"^([A-Za-z0-9_.\-]+)(?:\[[^\]]*\])?\s*(.*)$", dep.strip())
                if match:
                    pkg_name = match.group(1).strip()
                    version_spec = match.group(2).strip() or None
                    packages[pkg_name] = version_spec

        # Poetry dependencies: tool.poetry.dependencies
        poetry_deps = data.get("tool", {}).get("poetry", {}).get("dependencies", {})
        if isinstance(poetry_deps, dict):
            for pkg, spec in poetry_deps.items():
                if pkg.lower() == "python":
                    continue
                version_spec = str(spec) if not isinstance(spec, dict) else str(spec.get("version", ""))
                packages[pkg] = version_spec or None

        return packages

    def _parse_pipfile(self, path: Path) -> dict[str, str | None]:
        """Extract dependencies from Pipfile."""
        packages: dict[str, str | None] = {}
        if not path.is_file() or tomllib is None:
            return packages

        try:
            content = path.read_text(encoding="utf-8", errors="replace")
            data = tomllib.loads(content)
        except Exception:
            return packages

        pipfile_pkgs = data.get("packages", {})
        if isinstance(pipfile_pkgs, dict):
            for pkg, spec in pipfile_pkgs.items():
                version_spec = str(spec) if not isinstance(spec, dict) else None
                packages[pkg] = version_spec

        return packages

    def analyze(
        self,
        parsed_files: Sequence[ParsedFile],
        repo_path: str | Path | None = None,
    ) -> DependenciesReport:
        """Analyze declared and imported dependencies across parsed files and repo configuration.

        Args:
            parsed_files: Sequence of ParsedFile objects from SourceParser.
            repo_path: Optional path to repository root. Overrides self.repo_path if provided.

        Returns:
            A DependenciesReport containing external and local dependency facts.
        """
        active_repo_path = Path(repo_path).resolve() if repo_path else self.repo_path
        local_roots = self._get_local_module_roots(parsed_files)

        # 1. Inspect declared dependencies
        declared_map: dict[str, tuple[str | None, str]] = {}  # canonical_name -> (version_spec, source_file)
        declared_files_found: list[str] = []

        if active_repo_path and active_repo_path.is_dir():
            req_path = active_repo_path / "requirements.txt"
            if req_path.is_file():
                declared_files_found.append("requirements.txt")
                for pkg, spec in self._parse_requirements_txt(req_path).items():
                    declared_map[pkg] = (spec, "requirements.txt")

            pyproject_path = active_repo_path / "pyproject.toml"
            if pyproject_path.is_file():
                declared_files_found.append("pyproject.toml")
                for pkg, spec in self._parse_pyproject_toml(pyproject_path).items():
                    if pkg not in declared_map:
                        declared_map[pkg] = (spec, "pyproject.toml")

            pipfile_path = active_repo_path / "Pipfile"
            if pipfile_path.is_file():
                declared_files_found.append("Pipfile")
                for pkg, spec in self._parse_pipfile(pipfile_path).items():
                    if pkg not in declared_map:
                        declared_map[pkg] = (spec, "Pipfile")

        # 2. Extract detected imports and categorize
        external_imported: set[str] = set()
        local_deps: list[LocalDependencyInfo] = []

        for pf in parsed_files:
            for imp in pf.imports:
                mod = imp.module
                if not mod:
                    continue

                is_relative = mod.startswith(".")
                root_pkg = mod.lstrip(".").split(".")[0]

                if is_relative or (root_pkg in local_roots):
                    local_deps.append(
                        LocalDependencyInfo(
                            source_file=pf.file_path,
                            target_module=mod,
                            imported_names=[imp.name] if imp.name else [],
                            line_number=imp.line_number,
                        )
                    )
                elif root_pkg in self._stdlib_modules:
                    # Standard library module
                    continue
                else:
                    external_imported.add(root_pkg)

        # 3. Reconcile declared vs detected external dependencies
        # Normalize keys for accurate matching (e.g. PyYAML vs pyyaml)
        declared_normalized = {
            pkg.lower().replace("-", "_"): (pkg, spec, src)
            for pkg, (spec, src) in declared_map.items()
        }

        all_pkgs: set[str] = set()
        for norm_name, (orig_name, _, _) in declared_normalized.items():
            all_pkgs.add(norm_name)
        for imp in external_imported:
            all_pkgs.add(imp.lower().replace("-", "_"))

        dependencies: list[DependencyInfo] = []

        for norm_pkg in sorted(all_pkgs):
            is_declared = norm_pkg in declared_normalized
            # Check if imported directly or under normalized name
            is_imported = any(
                imp.lower().replace("-", "_") == norm_pkg for imp in external_imported
            )

            if is_declared:
                display_name, version_spec, src_file = declared_normalized[norm_pkg]
            else:
                display_name = next(
                    imp for imp in external_imported if imp.lower().replace("-", "_") == norm_pkg
                )
                version_spec = None
                src_file = None

            dependencies.append(
                DependencyInfo(
                    name=display_name,
                    declared=is_declared,
                    imported=is_imported,
                    version_spec=version_spec,
                    source_file=src_file,
                )
            )

        return DependenciesReport(
            dependencies=dependencies,
            local_dependencies=local_deps,
            declared_files_found=declared_files_found,
        )
