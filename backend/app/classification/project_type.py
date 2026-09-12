from pathlib import Path
from typing import Dict, List, Set


class ProjectTypeDetector:
    """
    Heuristically determines the project type:
    - backend
    - frontend
    - library
    - CLI
    - monorepo
    - service
    - application
    """

    def __init__(
        self,
        repo_path: str,
        languages: Dict[str, float],
        frameworks: List[str],
        files: List[str],
    ):
        self.repo_path = Path(repo_path).resolve()
        self.languages = languages
        self.frameworks = set(frameworks)
        self.files = files
        self.file_set = set(files)

    def detect(self) -> str:
        # 1. Check monorepo
        has_packages_dir = any(f.startswith("packages/") or f.startswith("apps/") or f.startswith("services/") for f in self.files)
        has_multiple_projects = sum(1 for f in self.files if f.endswith(("/package.json", "/pyproject.toml", "/pom.xml"))) > 1
        if has_packages_dir and has_multiple_projects:
            return "monorepo"

        # 2. Check frontend
        frontend_frameworks = {"React", "Next.js", "Vue", "Angular"}
        if self.frameworks.intersection(frontend_frameworks):
            # Check if it also has backend frameworks
            backend_frameworks = {"FastAPI", "Flask", "Django", "Express", "NestJS", "Spring", "Gin"}
            if not self.frameworks.intersection(backend_frameworks):
                return "frontend"

        # 3. Check CLI
        cli_markers = {"click", "typer", "argparse", "clap", "cobra", "commander"}
        is_cli = any(
            "cli" in f.lower() or "cmd" in f.lower() or f.endswith("__main__.py")
            for f in self.files
        )
        if is_cli and len(self.frameworks) == 0:
            return "CLI"

        # 4. Check backend / service
        backend_frameworks = {"FastAPI", "Flask", "Django", "Express", "NestJS", "Spring", "Gin", "Echo", "Fiber"}
        if self.frameworks.intersection(backend_frameworks):
            has_microservice_markers = any("dockerfile" in f.lower() or "k8s" in f.lower() or "service" in f.lower() for f in self.files)
            if has_microservice_markers and len(self.files) < 40:
                return "service"
            return "backend"

        # 5. Check library
        library_markers = {"setup.py", "pyproject.toml", "Cargo.toml"}
        has_lib_manifest = any(Path(f).name in library_markers for f in self.files)
        has_src_lib = any("lib/" in f or "src/" in f for f in self.files)
        if has_lib_manifest and has_src_lib and not self.frameworks:
            return "library"

        # Default fallback
        if any(f.endswith(".py") or f.endswith(".java") or f.endswith(".go") for f in self.files):
            return "backend"
        elif any(f.endswith(".js") or f.endswith(".ts") or f.endswith(".html") for f in self.files):
            return "frontend"

        return "application"
