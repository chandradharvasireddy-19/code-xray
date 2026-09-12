from dataclasses import dataclass, field, asdict
from enum import Enum
from typing import Any, Dict, Optional


class EvidenceType(str, Enum):
    AST = "ast"
    DEPENDENCY = "dependency"
    CALL_GRAPH = "call_graph"
    ARCHITECTURE = "architecture"
    GIT = "git"
    DOCUMENTATION = "documentation"
    TEST = "test"


class ConfidenceLevel(str, Enum):
    HIGH = "HIGH"
    MEDIUM = "MEDIUM"
    LOW = "LOW"


@dataclass
class EvidenceItem:
    type: str                                # 'ast', 'dependency', 'call_graph', 'architecture', 'git', 'documentation', 'test'
    source: str                              # Origin file, commit, or rule identifier
    location: Optional[str] = None          # File path or module
    line: Optional[int] = None              # Line number where evidence was observed
    description: str = ""                   # Detailed human-readable explanation of this specific evidence piece
    confidence: float = 0.80                # 0.0 to 1.0
    relationship: Optional[str] = None      # e.g., 'imports', 'calls', 'violates_layer'
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)
