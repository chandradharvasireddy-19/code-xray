from dataclasses import dataclass, field, asdict
from typing import Any, Dict, List, Optional
from app.classification.language_detector import LanguageDetector
from app.classification.framework_detector import FrameworkDetector
from app.classification.project_type import ProjectTypeDetector


@dataclass
class RepositoryProfile:
    languages: Dict[str, float] = field(default_factory=dict)
    frameworks: List[str] = field(default_factory=list)
    project_type: str = "unknown"
    primary_language: str = "unknown"
    total_files: int = 0

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


class RepositoryProfiler:
    """
    Orchestrates language detection, framework detection, and project type classification.
    """

    def __init__(self, repo_path: str, files: List[str], declared_dependencies: Dict[str, str]):
        self.repo_path = repo_path
        self.files = files
        self.declared_deps = declared_dependencies

    def profile(self) -> RepositoryProfile:
        # 1. Detect languages
        lang_detector = LanguageDetector(self.repo_path)
        languages = lang_detector.detect()

        primary_lang = next(iter(languages.keys()), "unknown") if languages else "unknown"

        # 2. Detect frameworks
        framework_detector = FrameworkDetector(self.repo_path, self.declared_deps)
        frameworks = framework_detector.detect()

        # 3. Detect project type
        type_detector = ProjectTypeDetector(self.repo_path, languages, frameworks, self.files)
        p_type = type_detector.detect()

        return RepositoryProfile(
            languages=languages,
            frameworks=frameworks,
            project_type=p_type,
            primary_language=primary_lang,
            total_files=len(self.files),
        )
