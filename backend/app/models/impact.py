from dataclasses import dataclass, field, asdict
from enum import Enum
from typing import Any, Dict, List, Optional
from datetime import datetime, timezone


class ImpactLevel(str, Enum):
    HIGH = "HIGH"
    MEDIUM = "MEDIUM"
    LOW = "LOW"


class RiskLevel(str, Enum):
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"
    CRITICAL = "CRITICAL"


@dataclass
class AffectedEntity:
    entity_id: str
    name: str
    type: str                                # 'file', 'function', 'class', 'method'
    file: str
    line: Optional[int] = None
    impact_score: float = 0.50               # 0.0 to 1.0
    impact_level: str = "MEDIUM"             # 'HIGH', 'MEDIUM', 'LOW'
    depth: int = 0                           # 0 = direct match, 1 = 1-hop, etc.
    reasons: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class RiskFactor:
    name: str
    score: int                               # Points contributing to total risk
    explanation: str

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class RiskReport:
    risk_score: int                          # 0 to 100
    risk_level: str                          # 'LOW', 'MEDIUM', 'HIGH', 'CRITICAL'
    factors: List[RiskFactor] = field(default_factory=list)
    summary: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return {
            "risk_score": self.risk_score,
            "risk_level": self.risk_level,
            "factors": [f.to_dict() for f in self.factors],
            "summary": self.summary,
        }


@dataclass
class PathStep:
    step: int
    entity: str
    file: str
    reason: str
    role: str                                # 'entry_point', 'business_logic', 'dependency', 'validation', 'test'

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class ImpactAnalysisResponse:
    analysis_id: str
    repository_id: str
    task: str
    matched_concepts: List[str] = field(default_factory=list)
    matched_entities: List[str] = field(default_factory=list)
    affected_entities: List[AffectedEntity] = field(default_factory=list)
    relationships: List[Dict[str, Any]] = field(default_factory=list)
    tests: List[Dict[str, Any]] = field(default_factory=list)
    findings: List[Dict[str, Any]] = field(default_factory=list)
    historical_context: List[Dict[str, Any]] = field(default_factory=list)
    risk: Optional[RiskReport] = None
    recommended_path: List[PathStep] = field(default_factory=list)
    ai_explanation: Optional[str] = None
    created_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())

    def to_dict(self) -> Dict[str, Any]:
        return {
            "analysis_id": self.analysis_id,
            "repository_id": self.repository_id,
            "task": self.task,
            "matched_concepts": self.matched_concepts,
            "matched_entities": self.matched_entities,
            "affected_entities": [e.to_dict() for e in self.affected_entities],
            "relationships": self.relationships,
            "tests": self.tests,
            "findings": self.findings,
            "historical_context": self.historical_context,
            "risk": self.risk.to_dict() if self.risk else None,
            "recommended_path": [p.to_dict() for p in self.recommended_path],
            "ai_explanation": self.ai_explanation,
            "created_at": self.created_at,
        }
