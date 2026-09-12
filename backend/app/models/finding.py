from dataclasses import dataclass, field, asdict
from enum import Enum
from typing import Any, Dict, List, Optional
from datetime import datetime, timezone
from app.models.evidence import EvidenceItem, ConfidenceLevel


class FindingType(str, Enum):
    DEAD_FEATURE = "dead_feature"
    GHOST_DEPENDENCY = "ghost_dependency"
    ARCHITECTURE_DRIFT = "architecture_drift"
    KNOWLEDGE_CONCENTRATION = "knowledge_concentration"
    DOCUMENTATION_CONTRADICTION = "documentation_contradiction"
    UNTESTED_CRITICAL = "untested_critical"


class Severity(str, Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


@dataclass
class ForensicFinding:
    finding_id: str
    repository_id: str
    finding_type: str                        # from FindingType or custom string
    title: str
    affected_file: str
    affected_symbol: Optional[str] = None
    line_number: Optional[int] = None
    severity: str = "medium"                # 'low', 'medium', 'high', 'critical'
    confidence: float = 0.80                # 0.0 to 1.0
    confidence_level: str = "MEDIUM"        # 'HIGH', 'MEDIUM', 'LOW'
    description: str = ""
    evidence: str = ""                      # Human-readable summary
    evidence_chain: List[EvidenceItem] = field(default_factory=list)  # Structured evidence items
    explanation: str = ""
    created_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())

    def to_dict(self) -> Dict[str, Any]:
        return {
            "finding_id": self.finding_id,
            "repository_id": self.repository_id,
            "finding_type": self.finding_type,
            "title": self.title,
            "affected_file": self.affected_file,
            "affected_symbol": self.affected_symbol,
            "line_number": self.line_number,
            "severity": self.severity,
            "confidence": self.confidence,
            "confidence_level": self.confidence_level,
            "description": self.description,
            "evidence": self.evidence,
            "evidence_chain": [e.to_dict() for e in self.evidence_chain],
            "explanation": self.explanation,
            "created_at": self.created_at,
        }
