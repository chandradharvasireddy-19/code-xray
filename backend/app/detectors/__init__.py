from app.detectors.dead_features import DeadFeatureDetector
from app.detectors.ghost_dependencies import GhostDependencyDetector
from app.detectors.architecture import ArchitectureDetector
from app.detectors.knowledge import KnowledgeConcentrationDetector

__all__ = [
    "DeadFeatureDetector",
    "GhostDependencyDetector",
    "ArchitectureDetector",
    "KnowledgeConcentrationDetector",
]
