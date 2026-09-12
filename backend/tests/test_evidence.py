import pytest
from app.evidence.evidence_engine import EvidenceEngine
from app.evidence.confidence import ConfidenceEngine
from app.models.evidence import EvidenceItem, EvidenceType, ConfidenceLevel


def test_evidence_engine_creation():
    ast_ev = EvidenceEngine.create_ast_evidence(
        file="src/auth.py",
        line=15,
        detail="Calls validator.validate()",
        confidence=0.92,
    )
    assert isinstance(ast_ev, EvidenceItem)
    assert ast_ev.type == EvidenceType.AST.value
    assert ast_ev.file_or_loc if hasattr(ast_ev, "file_or_loc") else ast_ev.location == "src/auth.py"
    assert ast_ev.line == 15
    assert ast_ev.confidence == 0.92


def test_confidence_engine():
    high_score = ConfidenceEngine.calculate_score(0.85)
    assert 0.80 <= high_score <= 0.95
    assert ConfidenceEngine.get_level(high_score) == ConfidenceLevel.HIGH.value

    med_score = ConfidenceEngine.calculate_score(0.55)
    assert 0.50 <= med_score < 0.80
    assert ConfidenceEngine.get_level(med_score) == ConfidenceLevel.MEDIUM.value

    low_score = ConfidenceEngine.calculate_score(0.20)
    assert ConfidenceEngine.get_level(low_score) == ConfidenceLevel.LOW.value
