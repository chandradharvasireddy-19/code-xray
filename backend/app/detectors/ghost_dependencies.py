"""Detect declared dependencies that are not actually used in source code."""
from typing import Any, Dict, List, Optional, Set
from app.models.repository import RepositoryModel
from app.models.finding import ForensicFinding, FindingType
from app.models.evidence import EvidenceItem, EvidenceType
from app.evidence.confidence import ConfidenceEngine
import uuid


class GhostDependencyDetector:
    """
    Compares declared dependencies (requirements.txt, pyproject.toml) against
    observed imports in source code to find potentially unused packages.
    """

    # Packages that are used as plugins/tools and may not appear in imports
    TOOL_PACKAGES = {
        "pip", "setuptools", "wheel", "pytest", "pytest_cov", "black", "flake8",
        "mypy", "isort", "pylint", "autopep8", "pre_commit", "tox", "nox",
        "coverage", "twine", "build", "flit", "poetry", "hatchling",
        "gunicorn", "uvicorn", "hypercorn", "daphne",
    }

    # Package name -> import name mappings for common mismatches
    PACKAGE_TO_IMPORT = {
        "pillow": "PIL",
        "python_dateutil": "dateutil",
        "pyyaml": "yaml",
        "scikit_learn": "sklearn",
        "beautifulsoup4": "bs4",
        "opencv_python": "cv2",
        "python_dotenv": "dotenv",
    }

    def __init__(self, repo: RepositoryModel, observed_imports: Dict[str, Set[str]]):
        """
        Args:
            repo: RepositoryModel with declared_dependencies
            observed_imports: package_name -> set of files that import it
        """
        self.repo = repo
        self.declared = repo.declared_dependencies
        self.observed = observed_imports

    def detect(self) -> List[ForensicFinding]:
        findings: List[ForensicFinding] = []

        for pkg_name, version in self.declared.items():
            normalized = pkg_name.lower().replace("-", "_")

            # Skip tool/dev packages
            if normalized in self.TOOL_PACKAGES:
                continue

            # Check direct match
            if normalized in self.observed:
                continue

            # Check alternate import name
            alt_name = self.PACKAGE_TO_IMPORT.get(normalized)
            if alt_name and alt_name.lower() in self.observed:
                continue

            # Check if any observed import starts with the package name
            found = False
            for obs_pkg in self.observed:
                if obs_pkg.startswith(normalized) or normalized.startswith(obs_pkg):
                    found = True
                    break
            if found:
                continue

            # This is a ghost dependency
            version_str = f" ({version})" if version else ""
            confidence = ConfidenceEngine.calculate_score(0.80)

            evidence_items = [
                EvidenceItem(
                    type=EvidenceType.DEPENDENCY.value,
                    source="requirements.txt",
                    location="requirements.txt",
                    description=f"Package '{pkg_name}{version_str}' is declared but no matching import found in source files",
                    confidence=0.85,
                    relationship="declared_not_imported",
                    metadata={"package": pkg_name, "version": version},
                )
            ]

            findings.append(ForensicFinding(
                finding_id=f"ghost-{uuid.uuid4().hex[:8]}",
                repository_id=self.repo.repository_id,
                finding_type=FindingType.GHOST_DEPENDENCY.value,
                title=f"Potentially unused dependency: {pkg_name}",
                affected_file="requirements.txt",
                affected_symbol=pkg_name,
                severity="low",
                confidence=confidence,
                confidence_level=ConfidenceEngine.get_level(confidence),
                description=f"Dependency '{pkg_name}{version_str}' is declared in requirements but no import was detected in source files. It may be unused or used as a runtime plugin.",
                evidence=f"Declared in requirements.txt but not found in any import statement",
                evidence_chain=evidence_items,
            ))

        return findings
