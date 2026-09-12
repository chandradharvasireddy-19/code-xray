import pytest
from app.models.repository import RepositoryModel, CodeEntity, Relationship
from app.impact.task_parser import TaskParser
from app.impact.impact_analyzer import ImpactAnalyzer
from app.impact.risk import RiskEngine


def test_task_parser():
    repo = RepositoryModel(
        repository_id="test_repo",
        name="test_repo",
        path=".",
        files=["src/payment_service.py", "src/auth.py"],
        entities={
            "src/payment_service.py:process_payment": CodeEntity(
                id="src/payment_service.py:process_payment",
                type="function",
                name="process_payment",
                file="src/payment_service.py",
            )
        },
    )

    parser = TaskParser(repo)
    result = parser.parse("I want to modify the payment service")

    assert "payment" in result["concepts"]
    assert "src/payment_service.py" in result["matched_files"]


def test_risk_engine():
    from app.models.impact import AffectedEntity

    affected = [
        AffectedEntity(
            entity_id=f"ent_{i}",
            name=f"entity_{i}",
            type="function",
            file=f"file_{i}.py",
            depth=1,
            impact_score=0.8,
        )
        for i in range(5)
    ]
    relationships = [{"type": "CALLS"}] * 6
    tests = []  # No tests = test gap
    findings = [{"type": "architecture_drift"}]
    historical = []

    engine = RiskEngine(
        affected_entities=affected,
        relationships=relationships,
        tests=tests,
        findings=findings,
        historical=historical,
    )
    report = engine.calculate()

    assert report.risk_score >= 50
    assert report.risk_level in ["HIGH", "CRITICAL"]
    factor_names = [f.name for f in report.factors]
    assert "Test Coverage Gap" in factor_names
    assert "Architectural Drift" in factor_names
