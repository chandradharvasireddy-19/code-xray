import pytest
from app.classification.language_detector import LanguageDetector
from app.classification.framework_detector import FrameworkDetector
from app.classification.project_type import ProjectTypeDetector
from app.classification.repository_profile import RepositoryProfiler


def test_language_detector(tmp_path):
    (tmp_path / "app.py").write_text("import os\n", encoding="utf-8")
    (tmp_path / "script.js").write_text("console.log('hi');\n", encoding="utf-8")

    detector = LanguageDetector(str(tmp_path))
    distribution = detector.detect()

    assert "Python" in distribution
    assert "JavaScript" in distribution
    assert round(sum(distribution.values()), 2) == 1.0


def test_framework_detector(tmp_path):
    deps = {"fastapi": "0.110.0", "uvicorn": "0.28.0"}
    detector = FrameworkDetector(str(tmp_path), deps)
    frameworks = detector.detect()
    assert "FastAPI" in frameworks


def test_project_type_detector(tmp_path):
    detector = ProjectTypeDetector(
        repo_path=str(tmp_path),
        languages={"Python": 1.0},
        frameworks=["FastAPI"],
        files=["main.py", "app/routes.py"],
    )
    p_type = detector.detect()
    assert p_type in ["backend", "service"]


def test_repository_profiler(tmp_path):
    (tmp_path / "service.py").write_text("import fastapi\n", encoding="utf-8")
    profiler = RepositoryProfiler(
        repo_path=str(tmp_path),
        files=["service.py"],
        declared_dependencies={"fastapi": "0.110.0"},
    )
    profile = profiler.profile()
    assert profile.primary_language == "Python"
    assert "FastAPI" in profile.frameworks
    assert profile.total_files == 1
