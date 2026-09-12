import pytest
from app.models.repository import RepositoryModel, Relationship, CodeEntity
from app.detectors.architecture import ArchitectureDetector
from app.detectors.dead_features import DeadFeatureDetector
from app.detectors.ghost_dependencies import GhostDependencyDetector
from app.detectors.knowledge import KnowledgeConcentrationDetector
from app.analyzer.docs import DocumentedRule


def test_architecture_detector():
    repo = RepositoryModel(
        repository_id="test_repo",
        name="test_repo",
        path=".",
        files=["src/controllers/payment_controller.py", "src/repositories/payment_repository.py"],
        relationships=[
            Relationship(
                source="src/controllers/payment_controller.py",
                target="src/repositories/payment_repository.py",
                type="imports",
                line=3,
            )
        ],
    )
    rules = [
        DocumentedRule(
            rule_text="Controller -> Service -> Repository",
            source_doc="architecture.md",
            allowed_flow=["controller", "service", "repository"],
        )
    ]
    detector = ArchitectureDetector(repo, rules)
    findings = detector.detect()

    assert len(findings) == 1
    assert findings[0].finding_type == "architecture_drift"
    assert "controller -> repository" in findings[0].title.lower()


def test_ghost_dependency_detector():
    repo = RepositoryModel(
        repository_id="test_repo",
        name="test_repo",
        path=".",
        declared_dependencies={"numpy": "1.26.4", "requests": "2.31.0"},
    )
    observed_imports = {"requests": {"src/api.py"}}
    detector = GhostDependencyDetector(repo, observed_imports)
    findings = detector.detect()

    ghost_names = [f.affected_symbol for f in findings]
    assert "numpy" in ghost_names
    assert "requests" not in ghost_names


def test_dead_feature_detector():
    repo = RepositoryModel(
        repository_id="test_repo",
        name="test_repo",
        path=".",
        files=["src/legacy/old_service.py"],
        source_files=["src/legacy/old_service.py"],
        entities={
            "src/legacy/old_service.py": CodeEntity(
                id="src/legacy/old_service.py",
                type="file",
                name="old_service.py",
                file="src/legacy/old_service.py",
            )
        },
        relationships=[],
    )
    detector = DeadFeatureDetector(repo)
    findings = detector.detect()

    assert len(findings) >= 1
    assert any("old_service" in f.title for f in findings)


def test_knowledge_concentration_detector():
    repo = RepositoryModel(
        repository_id="test_repo",
        name="test_repo",
        path=".",
        source_files=["src/core.py"],
    )
    git_stats = {
        "src/core.py": {
            "total_commits": 10,
            "contributor_count": 1,
            "primary_contributor": "Alice Dev",
            "top_contributor_ownership": 1.0,
        }
    }
    detector = KnowledgeConcentrationDetector(repo, git_stats)
    findings = detector.detect()

    assert len(findings) == 1
    assert findings[0].finding_type == "knowledge_concentration"
    assert "Alice Dev" in findings[0].evidence_chain[0].description
