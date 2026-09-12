import json
import re
from pathlib import Path
from typing import Dict, List, Set


class FrameworkDetector:
    """
    Detects frameworks used in the repository from declared dependencies
    and code indicators.
    """

    FRAMEWORK_SIGNATURES = {
        # Python
        "FastAPI": ["fastapi"],
        "Flask": ["flask"],
        "Django": ["django"],
        "Tornado": ["tornado"],
        "Pyramid": ["pyramid"],
        "Celery": ["celery"],
        "SQLAlchemy": ["sqlalchemy"],
        # JavaScript / TypeScript
        "React": ["react", "react-dom"],
        "Next.js": ["next"],
        "Vue": ["vue"],
        "Angular": ["@angular/core"],
        "Express": ["express"],
        "NestJS": ["@nestjs/core"],
        "Fastify": ["fastify"],
        # Java
        "Spring": ["spring-boot", "org.springframework.boot", "spring-core"],
        # Go
        "Gin": ["github.com/gin-gonic/gin"],
        "Echo": ["github.com/labstack/echo"],
        "Fiber": ["github.com/gofiber/fiber"],
    }

    def __init__(self, repo_path: str, declared_dependencies: Dict[str, str]):
        self.repo_path = Path(repo_path).resolve()
        self.declared_deps = declared_dependencies

    def detect(self) -> List[str]:
        detected: Set[str] = set()

        # 1. Check declared dependencies (e.g. from requirements.txt, pyproject.toml)
        normalized_deps = {k.lower().replace("-", "_"): v for k, v in self.declared_deps.items()}
        for framework, signatures in self.FRAMEWORK_SIGNATURES.items():
            for sig in signatures:
                norm_sig = sig.lower().replace("-", "_")
                if norm_sig in normalized_deps or any(norm_sig in d for d in normalized_deps):
                    detected.add(framework)
                    break

        # 2. Check package.json if present
        pkg_json = self.repo_path / "package.json"
        if pkg_json.exists():
            try:
                with open(pkg_json, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    all_js_deps = {}
                    all_js_deps.update(data.get("dependencies", {}))
                    all_js_deps.update(data.get("devDependencies", {}))
                    for framework, signatures in self.FRAMEWORK_SIGNATURES.items():
                        for sig in signatures:
                            if sig in all_js_deps:
                                detected.add(framework)
                                break
            except Exception:
                pass

        # 3. Check pom.xml or build.gradle if present
        pom_xml = self.repo_path / "pom.xml"
        if pom_xml.exists():
            try:
                content = pom_xml.read_text(encoding="utf-8", errors="replace").lower()
                if "spring" in content:
                    detected.add("Spring")
            except Exception:
                pass

        return sorted(list(detected))
